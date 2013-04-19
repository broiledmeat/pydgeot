import sys
import os
import stat

def is_dotfile(path):
    parts = path.split(os.sep)
    return any([part != '..' and part.startswith('.') for part in parts])

if sys.platform == 'win32':
    try:
        import win32file

        def create_symlink(source, target):
            if os.path.isfile(target):
                os.remove(target)
            win32file.CreateSymbolicLink(target, source)

        def is_hidden(path):
            try:
                return bool(win32file.GetFileAttributes(path) & 2)
            except (AttributeError, AssertionError):
                return False
    except ImportError:
        def is_hidden(path):
            return False

elif sys.platform == 'darwin':
    def is_hidden(path):
        return is_dotfile(path) or os.stat(path).st_flags & stat.UF_HIDDEN > 0

if 'create_symlink' not in globals():
    def create_symlink(source, target):
        if os.path.isfile(target):
            os.remove(target)
        os.symlink(source, target)

if 'is_hidden' not in globals():
    is_hidden = is_dotfile

