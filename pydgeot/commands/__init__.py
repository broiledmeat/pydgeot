import inspect

available = {}


class Command:
    """
    Container for command functions and help texts.
    """
    def __init__(self, func, name, help_args, help_msg):
        """
        Args:
            func: Command function to be called.
            name: Name of the command, if None, the name of the function is used.
            help_args: Usage text describing arguments.
            help: Usage text describing the commands purpose.
        """
        self.func = func
        self.name = name if name is not None else func.__name__
        self.help_args = help_args
        self.help_msg = help_msg


class register:
    """
    Decorator to add command functions to the list of available commands.
    """
    def __init__(self, name=None, help_args='', help_msg=''):
        self.name = name
        self.help_args = help_args
        self.help_msg = help_msg
        mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
        if '.' in mod_name:
            mod_name = mod_name[mod_name.rindex('.') + 1:]
        self.module_name = mod_name

    def __call__(self, func):
        global available
        command = Command(func, self.name, self.help_args, self.help_msg)
        if self.module_name not in available:
            available[self.module_name] = {}
        available[self.module_name][command.name] = command


class CommandError(Exception):
    pass
