from pydgeot.commands import register


@register(help_args='PATH [PATH]...', help_msg='Clean built content for specific directories')
def clean(app, *args):
    import os
    from pydgeot.commands import CommandError

    if app.is_valid:
        paths = [os.path.join(app.source_root, path) for path in args]
        app.clean(paths)
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
