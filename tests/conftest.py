import os
import pytest


class _ResourcesManager:
    root = os.path.join(os.path.dirname(__file__), 'resources')

    @classmethod
    def copy(cls, source, dest):
        import shutil

        source = os.path.join(cls.root, source)

        if os.path.isdir(source):
            if not os.path.isdir(dest):
                shutil.copytree(source, dest)
            else:
                for entry in os.scandir(source):
                    dest_path = os.path.join(dest, entry.name)
                    if os.path.isdir(entry.path):
                        cls.copy(entry.path, dest_path)
                    else:
                        shutil.copy2(entry.path, dest_path)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)

    @classmethod
    def equal(cls, source, dest):
        import filecmp

        if not os.path.exists(dest):
            return False

        source = os.path.join(cls.root, source)

        if os.path.isdir(source):
            return len(filecmp.dircmp(source, dest).diff_files) == 0

        return filecmp.cmp(source, dest)


@pytest.fixture
def resources():
    """
    :rtype: pathlib.Path
    """
    return _ResourcesManager



@pytest.fixture
def temp_dir(request, tmpdir_factory):
    """
    Similar to the pytest built-in tmpdir fixture, but returns a string, and with a less horrible name.
    """
    import re
    name = re.sub('[\W]', '_', request.node.name)[:30]
    return str(tmpdir_factory.mktemp(name, numbered=True))


# noinspection PyShadowingNames
@pytest.fixture
def temp_app(resources, temp_dir):
    from pydgeot.app import App

    dest_path = os.path.join(temp_dir, 'test_app')
    resources.copy('app_new', dest_path)
    return App(dest_path)

    # import shutil
    # from pydgeot.app import App
    #
    # name = getattr(request, 'param', 'app_new')
    # source_path = os.path.join(resources_root, name)
    # dest_path = os.path.join(temp_dir, 'test_app')
    # shutil.copytree(source_path, dest_path)
    # return App(dest_path)
