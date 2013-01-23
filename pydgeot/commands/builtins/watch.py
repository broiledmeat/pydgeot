def watch(app, *args):
    import os
    import types
    from pydgeot.commands import CommandError
    from pydgeot.generator import Generator
    from pydgeot.fsobserver import FSObserver

    if app.is_valid:
        gen = Generator(app)
        gen.generate()

        obs = FSObserver(app.content_root)
        def on_changed(self, path):
            root = os.path.dirname(path)
            changes = gen.collect_changes(root)
            gen.process_changes(changes)
        setattr(FSObserver, on_changed.__name__, types.MethodType(on_changed, FSObserver))
        obs.start()
    else:
        raise CommandError('Need a valid Pydgeot app directory.')
