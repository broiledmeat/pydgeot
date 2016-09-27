import os
import sys


def test_is_dotfile(temp_dir):
    from pydgeot.filesystem import is_dotfile

    with open(os.path.join(temp_dir, '.dotfile'), 'w') as fh:
        assert is_dotfile(fh.name)

    with open(os.path.join(temp_dir, 'file'), 'w') as fh:
        assert not is_dotfile(fh.name)

    os.makedirs(os.path.join(temp_dir, '.subdir'))
    with open(os.path.join(temp_dir, '.subdir', 'file'), 'w') as fh:
        assert is_dotfile(fh.name)


def test_is_hidden(temp_dir):
    from pydgeot.filesystem import is_hidden

    with open(os.path.join(temp_dir, 'visible'), 'w') as fh:
        assert not is_hidden(fh.name)

    if sys.platform != 'win32':
        with open(os.path.join(temp_dir, '.dotfile'), 'w') as fh:
            assert is_hidden(fh.name)

    if sys.platform == 'win32':
        import ctypes

        with open(os.path.join(temp_dir, 'hidden'), 'w') as fh:
            ctypes.windll.kernel32.SetFileAttributesW(fh.name, 2)
            assert is_hidden(fh.name)
    elif sys.platform == 'darwin':
        import stat

        with open(os.path.join(temp_dir, 'hidden'), 'w') as fh:
            os.chflags(fh.name, os.stat(fh.name).st_flags ^ stat.UF_HIDDEN)
            assert is_hidden(fh.name)


def test_create_symlink(temp_dir):
    from pydgeot.filesystem import create_symlink

    with open(os.path.join(temp_dir, 'test'), 'w') as fh:
        sym_path = os.path.join(temp_dir, 'test_sym')
        create_symlink(fh.name, sym_path)
        assert os.path.isfile(sym_path)

        if sys.platform != 'win32':
            assert os.path.islink(sym_path)
