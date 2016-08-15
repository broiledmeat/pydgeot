import sys
import os
import stat
from pydgeot.filesystem.glob import Glob


def is_dotfile(path):
    """
    Check if any part of a file path is a dot file.

    :param path: File path to check.
    :type path: str
    :return: If any part of the file path is a dot file.
    :rtype: bool
    """
    return any([part != '..' and part.startswith('.') for part in path.split(os.sep)])

if sys.platform == 'win32':
    try:
        import win32file

        def create_symlink(source, target):
            """
            Create a symlink from target to source.

            :param source: Source path for the symlink.
            :type source: str
            :param target: New path to create as the symlink.
            :type target: str
            """
            if os.path.isfile(target):
                os.remove(target)
            win32file.CreateSymbolicLink(target, source)

        def is_hidden(path):
            """
            Check if the file path is hidden.

            :param path: File path to check.
            :type path: str
            :return: If the file path is hidden.
            :rtype: bool
            """
            try:
                return bool(win32file.GetFileAttributes(path) & 2)
            except (AttributeError, AssertionError):
                return False
    except ImportError:
        # noinspection PyUnusedLocal
        def is_hidden(path):
            return False

elif sys.platform == 'darwin':
    def is_hidden(path):
        """
        Check if the file path is hidden.

        :param path: File path to check.
        :type path: str
        :return: If the file path is hidden.
        :rtype: bool
        """
        return is_dotfile(path) or os.stat(path).st_flags & stat.UF_HIDDEN > 0

if 'create_symlink' not in globals():
    def create_symlink(source, target):
        """
        Create a symlink from target to source.

        :param source: Source path for the symlink.
        :type source: str
        :param target: New path to create as the symlink.
        :type target: str
        """
        if os.path.isfile(target):
            os.remove(target)
        os.symlink(source, target)

if 'is_hidden' not in globals():
    is_hidden = is_dotfile
