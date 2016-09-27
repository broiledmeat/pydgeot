def test_is_glob():
    from pydgeot.filesystem import Glob

    glob_match_single = Glob('tes?')
    glob_match_all = Glob('test*')
    glob_match_path = Glob('test**')
    non_glob = Glob('test')
    assert glob_match_single.is_glob
    assert glob_match_all.is_glob
    assert glob_match_path.is_glob
    assert not non_glob.is_glob


def test_match_path():
    from pydgeot.filesystem import Glob

    glob = Glob('test/**/subtest??/*.html')
    assert glob.match_path('test/dir/subdir/subtest01/test.html')
    assert not glob.match_path('test/subtest01/test.html')
    assert not glob.match_path('test/dir/subtest0/test.html')
