from pydgeot.commands import register


@register(name='commands', help_msg='List available commands', allow_appless=True)
def list_commands(app):
    """
    Print available commands information.

    :param app: App instance to get commands for.
    :type app: pydgeot.app.App | None
    """
    from pydgeot import commands

    commands = sorted(commands.available.values(), key=lambda x: x.name)

    if len(commands) == 0:
        return

    name_align = max(14, max([len(command.name) for command in commands]))
    args_align = max([len(command.help_args) for command in commands])

    for command in commands:
        if app is None and not command.allow_appless:
            continue

        print('{} {}    {}'.format(command.name.rjust(name_align), command.help_args.ljust(args_align),
                                   command.help_msg))
