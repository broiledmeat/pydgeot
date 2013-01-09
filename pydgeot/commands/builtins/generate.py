def generate(app, *args):
    from pydgeot.commands import CommandError
    from pydgeot.generator import Generator

    if app.is_valid:
        gen = Generator(app)
        if len(args) > 0 and args[0] == 'wipe':
            gen.wipe()
        gen.generate()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')