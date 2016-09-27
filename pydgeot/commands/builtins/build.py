from pydgeot.commands import register


@register(help_msg='Build static content')
def build(app):
    """
    Generate content for an App instance.

    :param app: App instance to generate content for.
    :type app: pydgeot.app.App
    """
    from pydgeot.commands import CommandError
    from pydgeot.generator import Generator

    if app.is_valid:
        gen = Generator(app)
        gen.generate()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
