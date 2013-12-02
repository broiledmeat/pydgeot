from pydgeot.commands import register


@register(help_args='[forward|backward|both]', help_msg='Output DOT file showing source dependencies')
def depdot(app, *dirs):
    """
    Generates a DOT file showing file depedencies.
    """
    import os
    from pydgeot.commands import CommandError

    render_forward = 'forward' in dirs
    render_backward = 'backward' in dirs
    if not render_forward and not render_backward:
        render_forward = render_backward = True

    path = os.path.join(app.store_root, 'deps.dot')
    f = open(path, 'w')

    indent_level = 0

    def write(line):
        line = '{0}{1}'.format(' ' * indent_level * 2, str(line))
        f.write(line + '\n')

    if app.is_valid:
        write('graph Dependencies {')

        sources = app.sources.get_sources()
        indent_level += 1

        for source in sources:
            rel = app.relative_path(source.path)
            write('"{0}";'.format(rel))
            if render_forward:
                for dep in app.sources.get_dependencies(source.path):
                    dep_rel = app.relative_path(dep.path)
                    write('"{0}" -- "{1}" [dir=back, color="#880000"];'.format(rel, dep_rel))
                for dep in app.contexts.get_dependencies(source.path):
                    dep_rel = app.relative_path(dep.source)
                    write('"{0}" -- "{1}" [dir=back, color="#000088", label="{2}={3}"];'.format(rel,
                                                                                                dep_rel,
                                                                                                dep.name,
                                                                                                dep.value))
            if render_backward:
                for dep in app.sources.get_dependencies(source.path, reverse=True):
                    dep_rel = app.relative_path(dep.path)
                    write('"{0}" -- "{1}" [dir=back, color="#BB6666"];'.format(rel, dep_rel))
                for dep in app.contexts.get_dependencies(source.path, reverse=True):
                    dep_rel = app.relative_path(dep.source)
                    write('"{0}" -- "{1}" [dir=back, color="#6666BB", label="{2}={3}"];'.format(rel,
                                                                                                dep_rel,
                                                                                                dep.name,
                                                                                                dep.value))
        indent_level -= 1
        write('}')

        print('Wrote {0}'.format(path))
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
