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
        def on_changed(self, path):
            root = os.path.dirname(path)
            changes = gen.collect_changes(root)
            gen.process_changes(changes)
        setattr(Observer, on_changed.__name__, types.MethodType(on_changed, Observer))
        obs.start()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
