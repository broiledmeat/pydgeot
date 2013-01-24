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
        # If root is None, then try to use the current directory. If it doesn't work then just set is_valid to false.
        # If it is set, and the directory is invalid, then raise InvalidAppRoot
        raise_invalid = root is not None
        root = root if root is not None else './'
        self.root = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
        self.content_root = os.path.realpath(os.path.join(self.root, 'content'))
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

        if self.is_valid:
            # Config logging
            os.makedirs(self.log_root, exist_ok=True)
            self.log = logging.getLogger('app')
            self.log.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
            file_handler = logging.FileHandler(os.path.join(self.log_root, 'app.log'))
            file_handler.setFormatter(formatter)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)
            self.log.addHandler(file_handler)
            self.log.addHandler(console_handler)

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
        root = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.join(root, 'content'))
        os.makedirs(os.path.join(root, 'store'))
        os.makedirs(os.path.join(root, 'store', 'log'))
        os.makedirs(os.path.join(root, 'build'))
        os.makedirs(os.path.join(root, 'plugins'))
        conf = open(os.path.join(root, 'pydgeot.json'), 'w')
        conf.write('{}')
        conf.close()
        return App(root)

    def reset(self):
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
        if paths is None:
            paths = [self.content_root]
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
        for processor in self._processors:
            if processor.can_process(path):
                return processor
        return None

    def _process_func(self, path, name):
        processor = self.get_processor(path)
        if processor is not None and hasattr(processor, 'process_' + name):
            rel = os.path.relpath(path, self.content_root)
            proc_name = processor.__class__.__name__
            try:
                value = getattr(processor, 'process_' + name)(path)
                self.log.info('Processed \'%s\' %s with %s', rel, name, proc_name)
                return value
            except Exception as e:
                self.log.exception('Exception occurred processing \'%s\' %s with %s',
                                   rel, name, proc_name)
        return None

    def process_create(self, path):
        return self._process_func(path, 'create')

    def process_update(self, path):
        return self._process_func(path, 'update')

    def process_delete(self, path):
        return self._process_func(path, 'delete')

    def run_command(self, name, *args):
        if name in self._commands:
            command = self._commands[name]
            args_len = len(args) + 1
            arg_count = command.func.__code__.co_argcount
            has_varg = command.func.__code__.co_flags & 0x04 > 0

            if (has_varg and args_len >= arg_count) or (not has_varg and args_len == arg_count):
                self.log.debug('Running command \'%s %s\'', name, ' '.join(args))
                return command.func(self, *args)
            else:
                raise commands.CommandError('Incorrect number of arguments passed to command \'{0}\''.format(name))
        raise commands.CommandError('Command \'{0}\' does not exist'.format(name))
