import sys
import os

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
        pass

elif sys.platform == 'darwin':
    try:
        import Foundation

        def is_hidden(path):
            url = Foundation.NSURL.fileURLWithPath_(path)
            return url.getResourceValue_forKey_error_(None, Foundation.NSURLIsHiddenKey, None)[0]
    except ImportError:
        pass

if 'create_symlink' not in globals():
    def create_symlink(source, target):
        if os.path.isfile(target):
            os.remove(target)
        os.symlink(source, target)

if 'is_hidden' not in globals():
    def is_hidden(path):
        parts = path.split(os.sep)
        return any([part != '..' and part.startswith('.') for part in parts])
