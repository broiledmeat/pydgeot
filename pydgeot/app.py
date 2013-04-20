import os
import sys
import logging
import json
import importlib
import pkgutil
from pydgeot import processors, commands
from pydgeot.filemap import FileMap


class InvalidAppRoot(Exception):
    pass


class AppError(Exception):
    pass


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
        self.root = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
        self.source_root = os.path.realpath(os.path.join(self.root, 'source'))
        self.store_root = os.path.realpath(os.path.join(self.root, 'store'))
        self.log_root = os.path.realpath(os.path.join(self.store_root, 'log'))
        self.build_root = os.path.realpath(os.path.join(self.root, 'build'))
        self.plugins_root = os.path.realpath(os.path.join(self.root, 'plugins'))
        self.config_path = os.path.realpath(os.path.join(self.root, 'pydgeot.json'))
        self.is_valid = os.path.isdir(self.root) and os.path.isfile(self.config_path)

        if not self.is_valid and raise_invalid:
            raise InvalidAppRoot('App root \'{0}\' does not exist or is not a valid app directory.'.format(self.root))

        self._commands = {}
        self._processors = []

        # Import builtin commands
        importlib.import_module('pydgeot.commands.builtins')
        self._commands.update(commands.available['builtins'])

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

            # Load filemap
            self.filemap = FileMap(self, os.path.join(self.store_root, 'filemap.db'))

            # Get settings
            try:
                self.settings = json.load(open(self.config_path))
            except ValueError as e:
                raise AppError('Could not load config: \'{0}\''.format(e))

            # Add processor builtins to syspath
            pkg = pkgutil.get_loader('pydgeot.processors.builtins')
            sys.path.insert(0, os.path.dirname(pkg.path))

            # Load plugins
            if 'plugins' in self.settings:
                if os.path.isdir(self.plugins_root):
                    sys.path.insert(0, self.plugins_root)
                for plugin in self.settings['plugins']:
                    try:
                        importlib.import_module(plugin)
                    except Exception as e:
                        raise AppError('Unable to load plugin \'{0}\': {1}'.format(plugin, e))
                    if plugin in processors.available:
                        for processor in processors.available[plugin]:
                            self._processors.append(processor(self))
                    if plugin in commands.available:
                        self._commands.update(commands.available[plugin])

            # Sort processors by priority
            self._processors = sorted(self._processors, key=lambda p: p.priority, reverse=True)

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
        os.makedirs(os.path.join(root, 'plugins'))
        conf = open(os.path.join(root, 'pydgeot.json'), 'w')
        conf.write('{}')
        conf.close()
        return App(root)

    def reset(self):
        """
        Delete all built content.
        """
        for processor in self._processors:
            processor.reset()
        if os.path.isdir(self.build_root):
            for root, dirs, files in os.walk(self.build_root, topdown=False, followlinks=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        self.filemap.reset()

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
                        self.process_delete(source)
        for processor in self._processors:
            processor.process_changes_complete()
        self.filemap.clean(paths)

    def get_processor(self, path):
        """
        Get a processor able to handle the given path.

        Args:
            path: File path to get a processor for.

        Returns:
            A file processor, or None if one can not be found.
        """
        for processor in self._processors:
            if processor.can_process(path):
                return processor
        return None

    def _processor_call(self, name, path, default=None):
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
                return processor, value
            except Exception:
                rel = os.path.relpath(path, self.source_root)
                proc_name = processor.__class__.__name__
                self.log.exception('Exception occurred processing \'%s\' %s with %s', rel, name, proc_name)
        return None, default

    def _processor_process_call(self, name, path):
        """
        Helper method to call and log a process function on a paths appropriate file processor.

        Args:
            path: File path to process.
            name: Name of the function to call.

        Returns:
            The return value of the processor method to be called.
        """
        rel = os.path.relpath(path, self.source_root)
        processor, value = self._processor_call('process_' + name, path)
        if processor is not None:
            proc_name = processor.__class__.__name__
            self.log.info('Processed \'%s\' %s with %s', rel, name, proc_name)
            return value
        return None

    def process_create(self, path):
        """
        Process a create event for the given path.

        Args:
            path: File path to process.

        Returns:
            A list of files generated for the path, or None if no processor could be found.
        """
        return self._processor_process_call('create', path)

    def process_update(self, path):
        """
        Process an update event for the given path.

        Args:
            path: File path to process.

        Returns:
            A list of files generated for the path, or None if no processor could be found.
        """
        return self._processor_process_call('update', path)

    def process_delete(self, path):
        """
        Process a delete event for the given path.

        Args:
            path: File path to process.

        Returns:
            None
        """
        return self._processor_process_call('delete', path)

    def get_dependencies(self, path):
        """
        Get a list of files the given path depends on.

        Args:
            source: Path to get dependency paths for.

        Returns:
            A list of paths.
        """
        processor, value = self._processor_call('get_dependencies', path, default=[])
        return value

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
        if name in self._commands:
            command = self._commands[name]
            args_len = len(args) + 1
            arg_count = command.func.__code__.co_argcount
            has_varg = command.func.__code__.co_flags & 0x04 > 0

            if (has_varg and args_len >= arg_count) or (not has_varg and args_len == arg_count):
                self.log.debug('Running command \'%s\'', ' '.join([name] + list(args)))
                return command.func(self, *args)
            else:
                raise commands.CommandError('Incorrect number of arguments passed to command \'{0}\''.format(name))
        raise commands.CommandError('Command \'{0}\' does not exist'.format(name))
