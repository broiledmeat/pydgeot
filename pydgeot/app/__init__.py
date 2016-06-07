import os
import logging
import logging.handlers
import json
import importlib
import sqlite3
from pydgeot import processors, commands
from pydgeot.app.sources import Sources
from pydgeot.app.contexts import Contexts


class InvalidAppRoot(Exception):
    pass


class AppError(Exception):
    pass


def _db_regex_func(expr, item):
    """
    REGEXP search function for SQLite.

    :param expr:
    :type expr: str
    :param item:
    :type item:
    :return: True if a match is found.
    :rtype: bool
    """
    import re
    reg = re.compile(expr, re.I)
    return reg.search(item) is not None


class App:
    def __init__(self, root=None):
        """
        Initialize a new App instance for the given app directory.

        :param root: App directory path root to initialize at. If None the current working directory will be used.
        :type root: str | None
        """
        # If root is None, then try to use the current directory. If it doesn't work then just set is_valid to false.
        # If it is set, and the directory is invalid, then raise InvalidAppRoot
        raise_invalid = root is not None
        root = root if root is not None else './'

        # Set app path directories
        self.root = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
        self.source_root = os.path.realpath(os.path.join(self.root, 'source'))
        self.store_root = os.path.realpath(os.path.join(self.root, 'store'))
        self.log_root = os.path.realpath(os.path.join(self.store_root, 'log'))
        self.build_root = os.path.realpath(os.path.join(self.root, 'build'))
        self.config_path = os.path.realpath(os.path.join(self.root, 'pydgeot.json'))
        self.is_valid = os.path.isdir(self.root) and os.path.isfile(self.config_path)

        if not self.is_valid and raise_invalid:
            raise InvalidAppRoot('App root \'{0}\' does not exist or is not a valid app directory.'.format(self.root))

        # Initialize the commands dict and processor list
        self.commands = {}
        self.processors = []

        # Import builtin commands
        importlib.import_module('pydgeot.commands.builtins')
        for builtin_commands in commands.available.values():
            self.commands.update(builtin_commands)

        # Configure logging
        self.log = logging.getLogger('app')
        self.log.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        self.log.addHandler(console_handler)

        if self.is_valid:
            # Make source root if necessary
            os.makedirs(self.source_root, exist_ok=True)

            # Config logging
            os.makedirs(self.log_root, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(os.path.join(self.log_root, 'app.log'),
                                                                encoding='utf-8',
                                                                maxBytes=2 * 1024 * 1024,
                                                                backupCount=2)
            file_handler.setFormatter(formatter)
            self.log.addHandler(file_handler)

            # Get settings
            try:
                self.settings = json.load(open(self.config_path))
            except ValueError as e:
                raise AppError('Could not load config: \'{0}\''.format(e))

            # Init database
            self.db_path = os.path.join(self.store_root, 'pydgeot.db')
            self.db_connection = None
            self.db_cursor = None
            self.sources = None
            self.contexts = None
            self._init_database()

            # Load plugins
            if 'plugins' in self.settings:
                for plugin in self.settings['plugins']:
                    if plugin.startswith('builtins.'):
                        plugin = 'pydgeot.processors.' + plugin
                    try:
                        importlib.import_module(plugin)
                    except Exception as e:
                        raise AppError('Unable to load plugin \'{0}\': {1}'.format(plugin, e))
                    if plugin in processors.available:
                        for processor in processors.available[plugin]:
                            self.processors.append(processor(self))
                    if plugin in commands.available:
                        self.commands.update(commands.available[plugin])

            # Sort processors by priority
            self.processors = sorted(self.processors, key=lambda p: p.priority, reverse=True)

    def _init_database(self):
        """
        Connect to the SQLite database.
        """
        self.db_path = os.path.join(self.store_root, 'pydgeot.db')
        self.db_connection = sqlite3.connect(self.db_path)
        self.db_cursor = self.db_connection.cursor()
        self.db_connection.create_function('REGEXP', 2, _db_regex_func)
        self.sources = Sources(self)
        self.contexts = Contexts(self)

    @classmethod
    def create(cls, path):
        """
        Create a new app directory.

        :param path: Directory path to create as a new app directory.
        :type path: str
        :return: App instance for the new app directory.
        :rtype: pydgeot.app.App()
        """
        root = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.join(root, 'source'))
        os.makedirs(os.path.join(root, 'store'))
        os.makedirs(os.path.join(root, 'store', 'log'))
        os.makedirs(os.path.join(root, 'build'))
        conf = open(os.path.join(root, 'pydgeot.json'), 'w')
        conf.write('{}')
        conf.close()
        return App(root)

    def reset(self):
        """
        Delete all built content.
        """
        for processor in self.processors:
            processor.reset()
        if os.path.isdir(self.build_root):
            for root, dirs, files in os.walk(self.build_root, topdown=False, followlinks=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        os.unlink(self.db_path)
        self._init_database()

    def clean(self, paths):
        """
        Process delete events for all files under the given paths. Simulates the paths as having been deleted, without
        actually deleting the source files, allowing the source files to be rebuilt completely.

        :param paths: List of directory paths to clean.
        :type paths: list[str]
        """
        for path in paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path, topdown=False, followlinks=False):
                    for source in [os.path.join(root, file) for file in files]:
                        self.processor_delete(source)
        for processor in self.processors:
            processor.generation_complete()
        self.contexts.clean(paths)
        self.sources.clean(paths)
        self.db_connection.commit()

    def get_processor(self, path):
        """
        Get a processor able to handle the given path.

        :param path: File path to get a capable processor for.
        :type path: str
        :return: File processor, or None if a processor capable of handling the file cannot be found.
        :rtype: pydgeot.app.processors.Processor | None
        """
        for processor in self.processors:
            if processor.can_process(path):
                return processor
        return None

    def _processor_call(self, name, path, default=None, log_call=False):
        """
        Helper method to call a function on a paths appropriate file processor.

        :param name: Name of the function to call.
        :type name: str
        :param path: File path to process.
        :type path: str
        :param default: Value to return if no processor could be found.
        :type default: object
        :param log_call: Log this call.
        :type log_call: bool
        :return: Tuple containing the processor used (if any,) and its return value of the method called.
        :rtype: tuple[pydgeot.app.processors.Processor | None, object]
        """
        processor = self.get_processor(path)
        if processor is not None and hasattr(processor, name):
            try:
                value = getattr(processor, name)(path)

                if log_call:
                    rel = self.relative_path(path)
                    proc_name = processor.__class__.__name__
                    self.log.info('Processed \'%s\' %s with %s', rel, name, proc_name)

                return processor, value
            except Exception as e:
                rel = os.path.relpath(path, self.source_root)
                proc_name = processor.__class__.__name__
                self.log.exception('Exception occurred processing \'%s\' %s with %s: %s', rel, name, proc_name, str(e))
        return None, default

    def processor_prepare(self, path):
        """
        Process a prepare event for the given path.

        :param path: File path to process.
        :type path: str
        """
        self._processor_call('prepare', path)

    def processor_generate(self, path):
        """
        Process a generate event for the given path.

        :param path: File path to process.
        :type path: str
        """
        self._processor_call('generate', path, log_call=True)

    def processor_delete(self, path):
        """
        Process a delete event for the given path.

        :param path: File path to process.
        :type path: str
        """
        return self._processor_call('delete', path, log_call=True)

    def processor_generation_complete(self):
        """
        Process the changes complete event for all processors.
        """
        for processor in self.processors:
            processor.generation_complete()

    def run_command(self, name, *args):
        """
        Run a command.

        :param name: Name of the command to run.
        :type name: str
        :param args: Arguments to pass to the command.
        :type args: list(object)
        :return: Return value of the command being run.
        :rtype: object
        :raises pydgeot.app.CommandError: If a command with the given name does not exist.
        :raises pydgeot.app.CommandError: If the number of arguments passed to the command is not correct.
        """
        if name in self.commands:
            command = self.commands[name]
            args_len = len(args) + 1
            arg_count = command.func.__code__.co_argcount
            has_varg = command.func.__code__.co_flags & 0x04 > 0

            if (has_varg and args_len >= arg_count) or (not has_varg and args_len == arg_count):
                self.log.debug('Running command \'%s\'', ' '.join([name] + list(args)))
                return command.func(self, *args)
            else:
                raise commands.CommandError('Incorrect number of arguments passed to command \'{0}\''.format(name))
        raise commands.CommandError('Command \'{0}\' does not exist'.format(name))

    def source_path(self, path):
        """
        Get a source path from a relative or target path.

        :param path: Relative or target path.
        :type path: str
        :return: Source path.
        :rtype: str
        """
        if path.startswith(self.source_root):
            return path
        elif path.startswith(self.build_root):
            path = os.path.relpath(path, self.build_root)
        return os.path.join(self.source_root, path)

    def target_path(self, path):
        """
        Get a target path from a relative or source path.

        :param path: Relative or source path.
        :type path: str
        :return: Target path.
        :rtype: str
        """
        if path.startswith(self.source_root):
            path = os.path.relpath(path, self.source_root)
        elif path.startswith(self.build_root):
            return path
        return os.path.join(self.build_root, path)

    def relative_path(self, path):
        """
        Get a relative path from a source or target path.

        :param path: Source or target path.
        :type path: str
        :return: Relative path.
        :rtype: str
        """
        if path.startswith(self.source_root):
            path = os.path.relpath(path, self.source_root)
        elif path.startswith(self.build_root):
            path = os.path.relpath(path, self.build_root)
        path = '' if path == '.' else path
        return path

    def path_regex(self, path, recursive=False):
        """
        Get a regex for the given directory path. Used for retrieving file paths in or under the given directory.

        :param path: Directory path.
        :type path: str
        :param recursive: Regex should retrieve files in all subdirectories.
        :type recursive: bool
        :return: Regex path for the given directory.
        :rtype: str
        """
        rel = self.relative_path(path)
        if recursive:
            match = '.*'
        else:
            match = '[^{0}]*'.format(os.sep)
        if rel == '':
            regex = '^({0})$'.format(match)
        else:
            regex = '^{0}{1}({2})$'.format(rel, os.sep, match)
        return regex.replace('\\', '\\\\')
