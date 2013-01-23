def reset(app, *args):
    from pydgeot.commands import CommandError
    from pydgeot.generator import Generator

    if app.is_valid:
        gen = Generator(app)
        gen.reset()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
