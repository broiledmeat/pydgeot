def list_commands(app):
    commands = sorted(app._commands.values(), key=lambda x: x.name)
    left_align = max(14, max([len(c.name) + len(c.help_args) for c in commands])) + 4

    for command in commands:
        disp = command.name
        if command.help_args != '':
            disp += ' ' + command.help_args
        print('{0}\t{1}'.format(disp.rjust(left_align), command.help))