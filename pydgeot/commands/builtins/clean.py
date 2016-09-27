from pydgeot.commands import register


@register(help_args='PATH [PATH]...', help_msg='Clean built content for specific directories')
def clean(app, *args):
    """
    Clean content for specific directories in an App instance.

    :param app: App instance to clean content for.
    :type app: pydgeot.app.App
    :param args: List of directories (relative to the source directory) to clean.
    :type args: list[str]
    """
    import os
    from pydgeot.commands import CommandError

    if app.is_valid:
        paths = [os.path.join(app.source_root, path) for path in args]
        app.clean(paths)
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
