def reset(app, *args):
    from pydgeot.commands import CommandError

    if app.is_valid:
        app.reset()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
