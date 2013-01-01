def create(app, path):
    import os
    from .. import CommandError

    root = os.path.abspath(os.path.expanduser(os.path.join(os.getcwd(), path)))
    parent = os.path.split(root)[0]

    if not os.path.isdir(parent):
        raise CommandError('Parent directory \'{0}\' does not exist'.format(parent))
    if os.path.exists(root):
        raise CommandError('Target directory \'{0}\' already exists'.format(root))

    os.makedirs(os.path.join(root, 'content'))
    os.makedirs(os.path.join(root, 'store', 'logs'))
    os.makedirs(os.path.join(root, 'plugins'))
    os.makedirs(os.path.join(root, 'build'))

    conf_file = open(os.path.join(root, 'pydgeot.json'), 'w')
    conf_file.write('{}')
    conf_file.close()

