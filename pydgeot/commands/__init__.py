from pydgeot.commands.builtins import register_builtins


available = {}
""":type: dict[str, Command]"""


class CommandError(Exception):
    pass


class Command:
    """
    Container for command functions and help texts.
    """
    def __init__(self, func, name, help_args, help_msg, allow_appless):
        """
        :param func: Command function to be called.
        :type func: callable[pydgeot.app.App, *object]
        :param name: Name of the command, if None, the name of the function is used.
        :type name: str | None
        :param help_args: Usage text describing arguments.
        :type help_args: str
        :param help_msg: Usage text describing the commands purpose.
        :type help_msg: str
        :param allow_appless: Whether the function will require an App instance passed as the first argument or not.
        :type allow_appless: bool
        """
        self.func = func
        self.name = name
        self.help_args = help_args
        self.help_msg = help_msg
        self.allow_appless = allow_appless

    def run(self, app, *args):
        """
        Run the command function with the given app and arguments.

        :param app: App instance to pass to the command.
        :type app: pydgeot.app.App | None
        :param args: Arguments to pass to the command.
        :type args: list[Any]
        :return: Return value of the command being run.
        :rtype: Any
        :raises pydgeot.app.CommandError: If the number of arguments passed to the command is not correct.
        """
        arg_len = len(args) + 1
        arg_count = self.func.__code__.co_argcount
        has_varg = self.func.__code__.co_flags & 0x04 > 0

        if (has_varg and arg_len >= arg_count) or (not has_varg and arg_len == arg_count):
            return self.func(app, *args)

        raise CommandError('Incorrect number of arguments passed to command \'{0}\''.format(self.name))


# noinspection PyPep8Naming
class register:
    """
    Decorator to add command functions to the list of available commands.
    """
    def __init__(self, name=None, help_args='', help_msg='', allow_appless=False):
        """
        Decorator to add a function to the list of available Commands. The current App instance will be passed as the
        first argument, unless appless is True.

        :param name: Name of the command, if None, the name of the function is used.
        :type name: str | None
        :param help_args: Usage text describing arguments.
        :type help_args: str
        :param help_msg: Usage text describing the commands purpose.
        :type help_msg: str
        :param allow_appless: Whether the function will require an App instance passed as the first argument or not.
        :type allow_appless: bool
        """
        self.name = name
        self.help_args = help_args
        self.help_msg = help_msg
        self.allow_appless = allow_appless

    def __call__(self, func):
        name = self.name or func.__name__
        command = Command(func, name, self.help_args, self.help_msg, self.allow_appless)
        available[command.name] = command
        return func
