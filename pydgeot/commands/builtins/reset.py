from pydgeot.commands import register


@register(help_msg='Quickly clean all built content')
def reset(app):
    """
    Clean content and wipe databases for an App instance.

    :param app: App instance to reset.
    :type app: pydgeot.app.App
    """
    from pydgeot.commands import CommandError

    if app.is_valid:
        app.reset()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
