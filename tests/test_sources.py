def _source_result(app, path, build_root=False):
    from datetime import datetime
    from pydgeot.app.sources import SourceResult

    if build_root:
        return SourceResult(app.target_path(path), None, None)

    return SourceResult(app.source_path(path), 0, datetime.fromtimestamp(0))


def test_get(temp_app):
    expected = _source_result(temp_app, 'source')

    temp_app.sources.add_source('source')

    result = temp_app.sources.get_source('source')

    assert result == expected


def test_gets(temp_app):
    expected = {
        _source_result(temp_app, 'test/source02'),
        _source_result(temp_app, 'test/source03')
    }

    temp_app.sources.add_source('source01')
    temp_app.sources.add_source('test/source02')
    temp_app.sources.add_source('test/source03')
    temp_app.sources.add_source('test/other/source04')

    results = temp_app.sources.get_sources('test', recursive=False)

    assert results == expected


def test_gets_recursive(temp_app):
    expected = {
        _source_result(temp_app, 'test/source02'),
        _source_result(temp_app, 'test/source03'),
        _source_result(temp_app, 'test/other/source04')
    }

    temp_app.sources.add_source('source01')
    temp_app.sources.add_source('test/source02')
    temp_app.sources.add_source('test/source03')
    temp_app.sources.add_source('test/other/source04')

    results = temp_app.sources.get_sources('test', recursive=True)

    assert results == expected


def test_remove(temp_app):
    temp_app.sources.add_source('source')
    temp_app.sources.remove_source('source')

    result = temp_app.sources.get_source('source')

    assert result is None


def test_target(temp_app):
    expected = {
        _source_result(temp_app, 'source01', build_root=True),
        _source_result(temp_app, 'source02', build_root=True)
    }

    temp_app.sources.set_targets('source01', ['source01', 'source02'])

    results = temp_app.sources.get_targets('source01')

    assert results == expected


def test_dependencies(temp_app):
    expected = {
        _source_result(temp_app, 'source02'),
        _source_result(temp_app, 'source03')
    }

    temp_app.sources.set_dependencies('source01', ['source02', 'source03'])

    results = temp_app.sources.get_dependencies('source01')

    assert results == expected
