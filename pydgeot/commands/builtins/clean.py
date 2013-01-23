def clean(app, *args):
    import os
    from pydgeot.commands import CommandError
    from pydgeot.generator import Generator

    if app.is_valid:
        gen = Generator(app)
        paths = [os.path.join(app.content_root, path) for path in args]
        gen.clean(paths)
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
