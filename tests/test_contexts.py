import os


def _context_result(app, path, name, value):
    from pydgeot.app.contexts import ContextResult

    if value is not None:
        value = str(value)

    return ContextResult(name, value, app.source_path(path))


def test_add(temp_app):
    expected = {
        _context_result(temp_app, 'source', 'test', 0),
        _context_result(temp_app, 'source', 'test', 1)
    }

    temp_app.contexts.add_context('source', 'test', 0)
    temp_app.contexts.add_context('source', 'test', 1)

    results = temp_app.contexts.get_contexts(name='test')

    assert results == expected


def test_set(temp_app):
    expected = {
        _context_result(temp_app, 'source', 'test', 1)
    }

    temp_app.contexts.add_context('source', 'test', 0)
    temp_app.contexts.set_context('source', 'test', 1)

    results = temp_app.contexts.get_contexts(name='test')

    assert results == expected


def test_get_value(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 1),
        _context_result(temp_app, 'source02', 'test', 1)
    }

    temp_app.contexts.add_context('source01', 'test', 1)
    temp_app.contexts.add_context('source02', 'test', 1)
    temp_app.contexts.add_context('source03', 'test', 0)

    results = temp_app.contexts.get_contexts(value=1)

    assert results == expected


def test_get_name(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0),
        _context_result(temp_app, 'source02', 'test', 1),
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'test', 1)
    temp_app.contexts.add_context('source03', 'other', 2)

    results = temp_app.contexts.get_contexts('test')

    assert results == expected


def test_get_value_globbed(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 'test_01'),
        _context_result(temp_app, 'source02', 'other', 'test_02')
    }

    temp_app.contexts.add_context('source01', 'test', 'test_01')
    temp_app.contexts.add_context('source02', 'other', 'test_02')
    temp_app.contexts.add_context('source03', 'test', 'test')
    temp_app.contexts.add_context('source04', 'test', 'other')

    results = temp_app.contexts.get_contexts(value='test_*')

    assert results == expected


def test_get_name_and_value(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 1),
        _context_result(temp_app, 'source03', 'test', 1)
    }

    temp_app.contexts.add_context('source01', 'test', 1)
    temp_app.contexts.add_context('source02', 'other', 0)
    temp_app.contexts.add_context('source03', 'test', 1)
    temp_app.contexts.add_context('source04', 'test', 0)

    results = temp_app.contexts.get_contexts(name='test', value=1)

    assert results == expected


def test_get_source(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0),
        _context_result(temp_app, 'source01', 'other', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source01', 'other', 0)
    temp_app.contexts.add_context('source02', 'test', 0)

    results = temp_app.contexts.get_contexts(source='source01')

    assert results == expected


def test_get_single(temp_app):
    expected = _context_result(temp_app, 'source', 'test', 0)

    temp_app.contexts.add_context('source', 'test', 0)

    result = temp_app.contexts.get_context('test')

    assert result == expected


def test_remove_name(temp_app):
    expected = {
        _context_result(temp_app, 'source', 'test', 0),
        _context_result(temp_app, 'source', 'other', 0)
    }

    temp_app.contexts.add_context('source', 'test', 0)
    temp_app.contexts.add_context('source', 'other', 0)

    results = temp_app.contexts.get_contexts(source='source')\

    assert results == expected

    expected = {
        _context_result(temp_app, 'source', 'other', 0)
    }

    temp_app.contexts.remove_context(name='test')

    results = temp_app.contexts.get_contexts(source='source')

    assert results == expected


def test_remove_source(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0),
        _context_result(temp_app, 'source02', 'test', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'test', 0)

    results = temp_app.contexts.get_contexts(source='source01') | temp_app.contexts.get_contexts(source='source02')

    assert results == expected

    expected = {
        _context_result(temp_app, 'source02', 'test', 0)
    }

    temp_app.contexts.remove_context(source='source01')

    results = temp_app.contexts.get_contexts(source='source01') | temp_app.contexts.get_contexts(source='source02')

    assert results == expected


def test_remove_name_and_source(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0),
        _context_result(temp_app, 'source01', 'other', 0),
        _context_result(temp_app, 'source02', 'test', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source01', 'other', 0)
    temp_app.contexts.add_context('source02', 'test', 0)

    results = temp_app.contexts.get_contexts(source='source01') | temp_app.contexts.get_contexts(source='source02')

    assert results == expected

    expected = {
        _context_result(temp_app, 'source01', 'other', 0),
        _context_result(temp_app, 'source02', 'test', 0)
    }

    temp_app.contexts.remove_context(source='source01', name='test')

    results = temp_app.contexts.get_contexts(source='source01') | temp_app.contexts.get_contexts(source='source02')

    assert results == expected


def test_clean(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0),
        _context_result(temp_app, 'source02', 'test', 0),
        _context_result(temp_app, 'sub01/source03', 'test', 0),
        _context_result(temp_app, 'sub02/source04', 'test', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'test', 0)
    temp_app.contexts.add_context('sub01/source03', 'test', 0)
    temp_app.contexts.add_context('sub02/source04', 'test', 0)

    results = temp_app.contexts.get_contexts(name='test')

    assert results == expected

    expected = {
        _context_result(temp_app, 'source01', 'test', 0),
        _context_result(temp_app, 'source02', 'test', 0),
        _context_result(temp_app, 'sub01/source03', 'test', 0)
    }

    temp_app.contexts.clean([os.path.join(temp_app.source_root, 'sub02')])

    results = temp_app.contexts.get_contexts(name='test')

    assert results == expected

    expected = set()

    temp_app.contexts.clean([temp_app.source_root])

    results = temp_app.contexts.get_contexts(name='test')

    assert results == expected


def test_dependency_add(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_dependency('source02', 'test')

    results = temp_app.contexts.get_dependencies('source02')

    assert results == expected


def test_dependency_get(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'other', 0)
    temp_app.contexts.add_dependency('source03', 'test')

    results = temp_app.contexts.get_dependencies('source03')

    assert results == expected


def test_dependency_get_value(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'test', 1)
    temp_app.contexts.add_dependency('source03', 'test', value=0)

    results = temp_app.contexts.get_dependencies('source03')

    assert results == expected


def test_dependency_get_source(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test', 0)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'test', 0)
    temp_app.contexts.add_dependency('source03', 'test', source='source01')

    results = temp_app.contexts.get_dependencies('source03')

    assert results == expected


def test_dependency_get_recursive(temp_app):
    expected = {
        _context_result(temp_app, 'source01', 'test01', 0),
        _context_result(temp_app, 'source02', 'test02', 0)
    }

    temp_app.contexts.add_context('source01', 'test01', 0)
    temp_app.contexts.add_context('source02', 'test02', 0)
    temp_app.contexts.add_dependency('source02', 'test01')
    temp_app.contexts.add_dependency('source03', 'test02')

    results = temp_app.contexts.get_dependencies('source03', recursive=True)

    assert results == expected


def test_dependency_get_reverse(temp_app):
    expected = {
        _context_result(temp_app, 'source03', 'test', None)
    }

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'other', 0)
    temp_app.contexts.add_dependency('source03', 'test')

    results = temp_app.contexts.get_dependencies('source01', reverse=True)

    assert results == expected


def test_dependency_get_reverse_value(temp_app):
    expected = set()

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'test', 1)
    temp_app.contexts.add_dependency('source03', 'test', value=1)

    results = temp_app.contexts.get_dependencies('source01', reverse=True)

    assert results == expected

    expected = {
        _context_result(temp_app, 'source03', 'test', 1)
    }

    results = temp_app.contexts.get_dependencies('source02', reverse=True)

    assert results == expected


def test_dependency_get_reverse_source(temp_app):
    expected = set()

    temp_app.contexts.add_context('source01', 'test', 0)
    temp_app.contexts.add_context('source02', 'test', 0)
    temp_app.contexts.add_dependency('source03', 'test', source='source02')

    results = temp_app.contexts.get_dependencies('source01', reverse=True)

    assert results == expected

    expected = {
        _context_result(temp_app, 'source03', 'test', None)
    }

    results = temp_app.contexts.get_dependencies('source02', reverse=True)

    assert results == expected


def test_dependency_get_reverse_recursive(temp_app):
    expected = {
        _context_result(temp_app, 'source02', 'test01', None),
        _context_result(temp_app, 'source03', 'test02', None)
    }

    temp_app.contexts.add_context('source01', 'test01', 0)
    temp_app.contexts.add_context('source02', 'test02', 0)
    temp_app.contexts.add_dependency('source02', 'test01')
    temp_app.contexts.add_dependency('source03', 'test02')

    results = temp_app.contexts.get_dependencies('source01', reverse=True, recursive=True)

    assert results == expected
