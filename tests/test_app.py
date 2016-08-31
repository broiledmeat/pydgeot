import os


def test_create(temp_dir):
    from pydgeot.app import App
    App.create(os.path.join(temp_dir, 'app'))


def test_is_valid(temp_app):
    assert temp_app.is_valid


def test_source_path(temp_app):
    expected = os.path.join(temp_app.source_root, 'test')
    source = temp_app.source_path('test')
    target = temp_app.target_path(source)
    assert source == expected
    assert temp_app.source_path(target) == expected


def test_target_path(temp_app):
    expected = os.path.join(temp_app.build_root, 'test')
    target = temp_app.target_path('test')
    source = temp_app.source_path(target)
    assert target == expected
    assert temp_app.target_path(source) == expected


def test_relative_path(temp_app):
    expected = 'test/other'
    source = temp_app.source_path(expected)
    target = temp_app.target_path(expected)
    assert temp_app.relative_path(source) == expected
    assert temp_app.relative_path(target) == expected

