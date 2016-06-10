from pydgeot.commands import register


@register(help_args='[event delay[, timeout]]', help_msg='Continuously build static content')
def watch(app, *args):
    """
    Build content for an App instance, and then monitor changes, building content as needed.

    :param app: App instance to watch and build content for.
    :type app: pydgeot.app.App
    :param args: List of optional parameters for the content generator. The first element will be used for the event
                 timeout. The second will be used for the file changed timeout.
    :type args: list[str]
    """
    import os
    from pydgeot.commands import CommandError
    from pydgeot.generator import Generator
    from pydgeot.observer import Observer

    if app.is_valid:
        gen = Generator(app)
        gen.generate()

        obs = Observer(app.source_root)

        if len(args) >= 1:
            obs.event_timeout = max(int(args[0]), 1)
        if len(args) >= 2:
            obs.changed_timeout = max(int(args[1]), 1)

        print('Starting {0} observer ({1}s event delay, {2}s file changed timeout)'.format(obs.observer,
                                                                                           obs.event_timeout,
                                                                                           obs.changed_timeout))

        def on_changed(path):
            root = os.path.dirname(path)
            changes = gen.collect_changes(root)
            gen.process_changes(changes)

        obs.on_changed_handlers.add(on_changed)
        obs.start()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
