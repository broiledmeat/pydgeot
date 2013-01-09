def create(app, path):
    import os
    from pydgeot.commands import CommandError
    from pydgeot.app import App

    root = os.path.abspath(os.path.expanduser(os.path.join(os.getcwd(), path)))
    parent = os.path.split(root)[0]

    if not os.path.isdir(parent):
        raise CommandError('Parent directory \'{0}\' does not exist'.format(parent))
    if os.path.exists(root):
        raise CommandError('Target directory \'{0}\' already exists'.format(root))

    app = App(root)
    os.makedirs(app.content_root)
    os.makedirs(app.store_root)
    os.makedirs(app.log_root)
    os.makedirs(app.plugins_root)
    os.makedirs(app.build_root)

    conf_file = open(app.config_path, 'w')
    conf_file.write('{}')
    conf_file.close()

