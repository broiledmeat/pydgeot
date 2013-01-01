import inspect

available = {}

class Command:
    def __init__(self, func, name, help_args, help):
        self.func = func
        self.name = name if name is not None else func.__name__
        self.help_args = help_args
        self.help = help

class register:
    def __init__(self, name=None, help_args='', help=''):
        self.name = name
        self.help_args = help_args
        self.help = help
        mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
        if '.' in mod_name:
            mod_name = mod_name[mod_name.rindex('.') + 1:]
        self.module_name = mod_name

    def __call__(self, func):
        global available
        command = Command(func, self.name, self.help_args, self.help)
        if self.module_name not in available:
            available[self.module_name] = {}
        available[self.module_name][command.name] = command

class CommandError(Exception):
    pass