from pydgeot.commands import register


@register(help_args='[file event delay[, file changed timeout]]', help_msg='Continuously build static content')
def watch(app, *args):
    import os
    import types
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

        def on_changed(self, path):
            root = os.path.dirname(path)
            changes = gen.collect_changes(root)
            gen.process_changes(changes)

        setattr(Observer, on_changed.__name__, types.MethodType(on_changed, Observer))
        obs.start()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
