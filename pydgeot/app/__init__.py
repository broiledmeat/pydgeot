import json
import os
import logging
import logging.handlers
import importlib
import sqlite3
from pydgeot.app.dirconfig import DirConfig
from pydgeot.app.sources import Sources
from pydgeot.app.contexts import Contexts


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
    plugins_package_name = 'pydgeot.plugins'

    def __init__(self, root):
        """
        Initialize a new App instance for the given app directory.

        :param root: App directory path root to initialize at. If None the current working directory will be used.
        :type root: str
        """
        # Set app path directories
        self.root = os.path.abspath(os.path.expanduser(root))
        self.source_root = os.path.join(self.root, 'source')
        self.store_root = os.path.join(self.root, 'store')
        self.log_root = os.path.join(self.store_root, 'log')
        self.build_root = os.path.join(self.root, 'build')
        self.config_path = os.path.join(self.root, 'pydgeot.conf')
        self.is_valid = os.path.isdir(self.root) and os.path.isfile(self.config_path)

        # Processor name and instance
        self.processors = {}
        """:type: dict[str, pydgeot.processors.Processor]"""

        self.db_path = os.path.join(self.store_root, 'pydgeot.db')
        self.db_connection = None
        self.db_cursor = None
        self.sources = None
        """:type: Sources | None"""
        self.contexts = None
        """:type: Contexts | None"""

        # Configure logging
        self.log = logging.getLogger('app')
        self.log.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        self.log.addHandler(console_handler)

        # Import builtin processors and commands
        from pydgeot import commands, processors
        commands.register_builtins()
        processors.register_builtins()

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
            config = {}
            config_path = os.path.join(self.root, 'pydgeot.conf')
            if os.path.isfile(config_path):
                try:
                    with open(config_path) as fh:
                        config = json.load(fh)
                except ValueError as e:
                    raise AppError('Could not load config \'{}\': \'{}\''.format(config_path, e))

            # Init database
            self._init_database()

            # Load plugins
            # noinspection PyTypeChecker
            for plugin in config.get('plugins', []):
                try:
                    importlib.import_module('{}.{}'.format(self.plugins_package_name, plugin))
                except Exception as e:
                    raise AppError('Unable to load plugin \'{0}\': {1}'.format(plugin, e))

        for name, processor in processors.available.items():
            self.processors[name] = processor(self)

    def _init_database(self):
        self.db_connection = sqlite3.connect(self.db_path)
        self.db_connection.create_function('REGEXP', 2, _db_regex_func)
        self.db_cursor = self.db_connection.cursor()
        self.sources = Sources(self)
        self.contexts = Contexts(self)

    @classmethod
    def create(cls, path):
        """
        Create a new app directory.

        :param path: Directory path to create as a new app directory.
        :type path: str
        :return: App instance for the new app directory.
        :rtype: pydgeot.app.App
        """
        root = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.join(root, 'source'))
        os.makedirs(os.path.join(root, 'store'))
        os.makedirs(os.path.join(root, 'store', 'log'))
        os.makedirs(os.path.join(root, 'build'))
        with open(os.path.join(root, 'pydgeot.conf'), 'w') as fh:
            fh.write('{}')
        return App(root)

    def reset(self):
        """
        Delete all built content.
        """
        for processor in self.processors.values():
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
        for processor in self.processors.values():
            processor.generation_complete()
        self.contexts.clean(paths)
        self.sources.clean(paths)
        self.db_connection.commit()

    def get_config(self, path):
        """
        Get the configuration for the given path.

        :param path: File path to get the configuration for.
        :type path: str
        :return: Configuration dictionary for the given path.
        :rtype: pydgeot.app.dirconfig.DirConfig
        """
        return DirConfig.get(self, path)

    def get_processor(self, path):
        """
        Get a processor able to handle the given path.

        :param path: File path to get a capable processor for.
        :type path: str
        :return: File processor, or None if a processor capable of handling the file cannot be found.
        :rtype: pydgeot.app.processors.Processor | None
        """
        config = self.get_config(path)

        for processor in config.processors:
            if processor.can_process(path):
                return processor
        return None

    def _processor_call(self, name, path, default=None):
        """
        Helper method to call a function on a paths appropriate file processor.

        :param name: Name of the function to call.
        :type name: str
        :param path: File path to process.
        :type path: str
        :param default: Value to return if no processor could be found.
        :type default: Any
        :return: Tuple containing the processor used (if any,) and its return value of the method called.
        :rtype: tuple[pydgeot.app.processors.Processor | None, Any]
        """
        processor = self.get_processor(path)
        if processor is not None and hasattr(processor, name):
            rel_path = self.relative_path(path)
            proc_name = processor.name if processor.name else processor.__class__.__name__

            try:
                value = getattr(processor, name)(path)

                if name != 'prepare':
                    self.log.info('[%s] %s "%s"', proc_name, name, rel_path)

                return processor, value
            except Exception as e:
                self.log.exception('[%s] exception.%s "%s" %s', proc_name, name, rel_path, str(e))
        return None, default

    def processor_prepare(self, path):
        """
        Process a prepare event for the given path.

        :param path: File path to process.
        :type path: str
        """
        return self._processor_call('prepare', path)

    def processor_generate(self, path):
        """
        Process a generate event for the given path.

        :param path: File path to process.
        :type path: str
        """
        return self._processor_call('generate', path)

    def processor_delete(self, path):
        """
        Process a delete event for the given path.

        :param path: File path to process.
        :type path: str
        """
        return self._processor_call('delete', path)

    def processor_generation_complete(self):
        """
        Process the changes complete event for all processors.
        """
        for processor in self.processors.values():
            processor.generation_complete()

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
