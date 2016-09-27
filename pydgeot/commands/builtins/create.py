from pydgeot.commands import register


# noinspection PyUnusedLocal
@register(help_args='PATH', help_msg='Generate a new Pydgeot app directory', allow_appless=True)
def create(app, path):
    """
    Create a new App directory.

    :param app: App instance. Unused.
    :type app: pydgeot.app.App | None
    :param path: Directory path to create as an App directory.
    :type path: str
    """
    import os
    from pydgeot.commands import CommandError
    from pydgeot.app import App

    root = os.path.abspath(os.path.expanduser(os.path.join(os.getcwd(), path)))
    parent = os.path.split(root)[0]

    if not os.path.isdir(parent):
        raise CommandError('Parent directory \'{0}\' does not exist'.format(parent))
    if os.path.exists(root):
        raise CommandError('Target directory \'{0}\' already exists'.format(root))

    App.create(root)
