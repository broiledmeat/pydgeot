def clean(app, *args):
    import os
    from pydgeot.commands import CommandError

    if app.is_valid:
        paths = [os.path.join(app.content_root, path) for path in args]
        app.clean(paths)
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
