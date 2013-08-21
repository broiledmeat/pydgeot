from pydgeot.commands import register


@register(help_msg='Quickly clean all built content')
def reset(app):
    from pydgeot.commands import CommandError

    if app.is_valid:
        app.reset()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
