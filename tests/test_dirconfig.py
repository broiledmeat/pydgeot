import os


def test_base(temp_app, resources):
    from pydgeot.app.dirconfig import DirConfig
    from pydgeot.filesystem.glob import Glob
    from pydgeot.processors.builtins.copyfallback import CopyFallbackProcessor
    from pydgeot.processors.builtins.symlinkfallback import SymlinkFallbackProcessor

    resources.copy('test_dirconfig', temp_app.root)

    config = DirConfig.get(temp_app, temp_app.root)

    assert config is not None
    assert len(config.processors) == 2
    assert any([isinstance(proc, CopyFallbackProcessor) for proc in config.processors])
    assert any([isinstance(proc, SymlinkFallbackProcessor) for proc in config.processors])
    assert config.ignore == {Glob('**/.ignore')}


def test_overriding(temp_app, resources):
    from pydgeot.app.dirconfig import DirConfig
    from pydgeot.processors.builtins.symlinkfallback import SymlinkFallbackProcessor

    resources.copy('test_dirconfig', temp_app.root)

    config = DirConfig.get(temp_app, os.path.join(temp_app.source_root, 'sub'))

    assert config is not None
    assert len(config.processors) == 1
    assert isinstance(config.processors[0], SymlinkFallbackProcessor)
    assert config.extra == {'testing01': 0, 'testing02': 2, 'extra': {'test': True, 'ok': 'alright'}}
