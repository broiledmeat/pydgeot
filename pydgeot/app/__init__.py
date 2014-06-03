import os
import sys
import logging
import json
import importlib
import pkgutil
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
    REGEXP function for SQLite. Return true if a match is found.
    """
    import re
    reg = re.compile(expr, re.I)
    return reg.search(item) is not None


class App:
    def __init__(self, root=None):
        """
        Initialize a new App instance for the given app directory.

        Args:
            root: The app directory path root to initialize at.
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
            file_handler = logging.FileHandler(os.path.join(self.log_root, 'app.log'), encoding='utf-8')
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
        Create a new app directory structure.

        Args:
            path: Directory path to create new app directory at.

        Returns:
            An app instance for the new app directory.
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

    def clean(self, paths=None):
        """
        Process delete events for all files under the given paths. Simulates the paths as having been deleted, without
        actually deleting the source files, allowing the source files to be rebuilt completely.

        Args:
            paths: List of directory paths to clean.
        """
        if paths is None:
            paths = [self.source_root]
        for path in paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path, topdown=False, followlinks=False):
                    sources = [os.path.join(root, file) for file in files]
                    for source in sources:
                        self.processor_delete(source)
        for processor in self.processors:
            processor.generation_complete()
        self.contexts.clean(paths)
        self.sources.clean(paths)
        self.db_connection.commit()

    def get_processor(self, path):
        """
        Get a processor able to handle the given path.

        Args:
            path: File path to get a processor for.

        Returns:
            A file processor, or None if one can not be found.
        """
        for processor in self.processors:
            if processor.can_process(path):
                return processor
        return None

    def _processor_call(self, name, path, default=None, log_call=None):
        """
        Helper method to call a function on a paths appropriate file processor.

        Args:
            name: Name of the function to call.
            path: File path to process.
            args: List of extra arguments to pass.
            kwargs: Dictionary of extra keyword arguments to pass.
            default: Default value to return if no processor can be found.

        Returns:
            A tuple containing the processor used, and its return value of the method called.
        """
        processor = self.get_processor(path)
        if processor is not None and hasattr(processor, name):
            try:
                value = getattr(processor, name)(path)

                if log_call is not None:
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

        Args:
            path: File path to process.
        """
        self._processor_call('prepare', path)

    def processor_generate(self, path):
        """
        Process a generate event for the given path.

        Args:
            path: File path to process.
        """
        self._processor_call('generate', path, log_call='generate')

    def processor_delete(self, path):
        """
        Process a delete event for the given path.

        Args:
            path: File path to process.
        """
        return self._processor_call('delete', path, log_call='delete')

    def processor_generation_complete(self):
        """
        Process the changes complete event for all processors.
        """
        for processor in self.processors:
            processor.generation_complete()

    def run_command(self, name, *args):
        """
        Run a command.

        Args:
            name: Name of the command to run.
            args: Arguments to pass to the command.

        Raises:
            CommandError: If a command with the name does not exist, or if the command does not take the number of
                          arguments given.

        Returns:
            The return value of the command being run.
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
        Get a source path from a build or relative path.

        Args:
            relative: Relative path.

        Returns:
            A source path.
        """
        if path.startswith(self.source_root):
            return path
        elif path.startswith(self.build_root):
            path = os.path.relpath(path, self.build_root)
        return os.path.join(self.source_root, path)

    def target_path(self, path):
        """
        Get a target path from a source or relative path.

        Args:
            relative: Relative path.

        Returns:
            A target path.
        """
        if path.startswith(self.source_root):
            path = os.path.relpath(path, self.source_root)
        elif path.startswith(self.build_root):
            return path
        return os.path.join(self.build_root, path)

    def relative_path(self, path):
        """
        Get a relative path from a source or target path.

        Args:
            path: Source or target path.

        Returns:
            A relative path.
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

        Args:
            path: Directory path.
            recursive: Retrieve files in all subdirectories.

        Returns:
            A regex string.
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
