from pydgeot.commands import register


@register(help_msg='Build static content')
def build(app):
    from pydgeot.commands import CommandError
    from pydgeot.generator import Generator

    if app.is_valid:
        gen = Generator(app)
        gen.generate()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
