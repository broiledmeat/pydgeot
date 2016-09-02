available = {}
""":type: dict[str, Command]"""


class Command:
    """
    Container for command functions and help texts.
    """
    def __init__(self, func, name, help_args, help_msg):
        """
        :param func: Command function to be called.
        :type func: callable[pydgeot.app.App, *object]
        :param name: Name of the command, if None, the name of the function is used.
        :type name: str | None
        :param help_args: Usage text describing arguments.
        :type help_args: str
        :param help_msg: Usage text describing the commands purpose.
        :type help_msg: str
        """
        self.func = func
        self.name = name
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

    def __call__(self, func):
        global available
        name = self.name or func.__name__
        command = Command(func, name, self.help_args, self.help_msg)
        available[command.name] = command
        return func


class CommandError(Exception):
    pass
