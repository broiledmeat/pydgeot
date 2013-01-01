import os
import sys
import json
import importlib
import pkgutil
from pydgeot import processors, commands

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
        self.root = os.path.abspath(os.path.expanduser(root))
        self.is_valid = os.path.isdir(self.root) and os.path.isfile(os.path.join(self.root, 'pydgeot.json'))

        if not self.is_valid and raise_invalid:
            raise InvalidAppRoot('App root \'{0}\' does not exist or not a valid app directory.'.format(self.root))

        self._commands = {}
        self._processors = []

        # Import builtin commands
        importlib.import_module('pydgeot.commands.builtins')
        self._commands.update(commands.available['builtins'])

        if self.is_valid:
            # Get settings
            self.settings = json.load(open(os.path.join(self.root, 'pydgeot.json')))

            # Add processor builtins to syspath
            pkg = pkgutil.get_loader('pydgeot.processors.builtins')
            sys.path.insert(0, pkg._path._path[0])

            # Load plugins
            plugins_path = os.path.join(self.root, 'plugins')
            if os.path.isdir(plugins_path) and 'plugins' in self.settings:
                sys.path.insert(0, plugins_path)
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
            self._processors = sorted(self._processors, lambda p: p.priority, reverse=True)

    def command(self, name, *args):
        if name in self._commands:
            command = self._commands[name]
            args_len = len(args) + 1
            arg_count = command.func.__code__.co_argcount
            has_varg = command.func.__code__.co_flags & 0x04 > 0

            if (has_varg and args_len >= arg_count) or (not has_varg and args_len == arg_count):
                return command.func(self, *args)
            else:
                raise commands.CommandError('Incorrect number of arguments passed to commands \'{0}\''.format(name))
        raise commands.CommandError('Command \'{0}\' does not exist'.format(name))