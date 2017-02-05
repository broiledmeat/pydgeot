import os
import pytest


class _DummyProcessor:
    name = 'dummy'
    help_msg = None

    def __init__(self, _):
        pass

    def generation_complete(self):
        pass


# noinspection PyShadowingNames
@pytest.fixture
def temp_config_app(resources, temp_dir):
    from pydgeot.app import App
    from pydgeot import processors

    processors.available.clear()
    processors.register_builtins()
    processors.register()(_DummyProcessor)

    dest_path = os.path.join(temp_dir, 'test_app')
    resources.copy('app_new', dest_path)

    return App(dest_path)


def test_base(temp_config_app, resources):
    from pydgeot.app.dirconfig import DirConfig
    from pydgeot.filesystem.glob import Glob
    from pydgeot.processors.builtins.fallback import FallbackProcessor

    resources.copy('test_dirconfig', temp_config_app.root)

    config = DirConfig.get(temp_config_app, temp_config_app.root)

    assert config is not None
    assert len(config.processors) == 2
    assert any([isinstance(proc, FallbackProcessor) for proc in config.processors])
    assert any([isinstance(proc, _DummyProcessor) for proc in config.processors])
    assert config.ignore == {Glob('**/.ignore')}


def test_overriding(temp_config_app, resources):
    from pydgeot.app.dirconfig import DirConfig

    resources.copy('test_dirconfig', temp_config_app.root)

    config = DirConfig.get(temp_config_app, os.path.join(temp_config_app.source_root, 'sub'))

    assert config is not None
    assert len(config.processors) == 1
    assert isinstance(list(config.processors)[0], _DummyProcessor)
    assert config.extra == {'testing01': 0, 'testing02': 2, 'extra': {'test': True, 'ok': 'alright'}}

