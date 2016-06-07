import inspect

available = {}


class Command:
    """
    Container for command functions and help texts.
    """
    def __init__(self, func, name, help_args, help_msg):
        """
        :param func: Command function to be called.
        :type func: types.FunctionType
        :param name: Name of the command, if None, the name of the function is used.
        :type name: str | None
        :param help_args: Usage text describing arguments.
        :type help_args: str
        :param help_msg: Usage text describing the commands purpose.
        :type help_msg: str
        """
        self.func = func
        self.name = name if name is not None else func.__name__
        self.help_args = help_args
        self.help_msg = help_msg


# noinspection PyPep8Naming
class register:
    """
    Decorator to add command functions to the list of available commands.
    """
    def __init__(self, name=None, help_args='', help_msg=''):
        """
        Decorator to add a function to the list of available Commands.

        :param name: Name of the command, if None, the name of the function is used.
        :type name: str | None
        :param help_args: Usage text describing arguments.
        :type help_args: str
        :param help_msg: Usage text describing the commands purpose.
        :type help_msg: str
        """
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
