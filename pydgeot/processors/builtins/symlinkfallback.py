import sys
import os
import shutil
from pydgeot.processors import register, Processor

if sys.platform == 'win32':
    try:
        import win32file
        def create_symlink(source, target):
            if os.path.isfile(target):
                os.remove(target)
            win32file.CreateSymbolicLink(target, source)
    except ImportError:
        pass

if 'create_symlink' not in globals():
    def create_symlink(source, target):
        if os.path.isfile(target):
            os.remove(target)
        os.symlink(source, target)

@register()
class SymlinkFallbackProcessor(Processor):
    priority = 0

    def can_process(self, path):
        return True

    def process_update(self, path):
        rel = os.path.relpath(path, self.app.source_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        create_symlink(path, target)
        return [target]
