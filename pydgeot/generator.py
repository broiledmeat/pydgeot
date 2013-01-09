import os
import shutil
from pydgeot.filemap import FileMap

class ChangeSet:
    def __init__(self):
        self.create = set()
        self.update = set()
        self.delete = set()
    def merge(self, other):
        self.create |= other.create
        self.update |= other.update
        self.delete |= other.delete

class Generator:
    def __init__(self, app):
        self.app = app
        self.filemap = FileMap(app, os.path.join(app.store_root, 'filemap.db'))

    def wipe(self):
        print('WIPE')
        if os.path.isdir(self.app.build_root):
            shutil.rmtree(self.app.build_root)
        self.filemap.wipe()

    def generate(self):
        if not os.path.isdir(self.app.build_root):
            os.makedirs(self.app.build_root)
        changes = self.collect_changes()
        self.process_changes(changes)

    def process_changes(self,  changes):
        print('CREATE', changes.create)
        print('UPDATE', changes.update)
        print('DELETE', changes.delete)

        for path in changes.delete:
            for target in self.filemap.targets(path):
                os.remove(target)
            os.remove(path)
            self.filemap.remove(path)

        for path in changes.create | changes.update:
            processor = self.app.processor(path)
            if processor is not None:
                print('Processing {0} with {1}'.format(os.path.relpath(path, self.app.content_root), processor.__class__.__name__))
                self.filemap.dependencies(path, processor.get_dependencies(path))
                self.filemap.targets(path, processor.process(path))
        self.filemap.commit()

    def collect_changes(self, root=None):
        if root is None:
            root = self.app.content_root
        changes = ChangeSet()

        dirs = set()

        old_sources = self.filemap.sources(root, mtimes=True)
        current_sources = []
        for filename in os.listdir(root):
            path = os.path.join(root, filename)
            stat = os.stat(path)
            if os.path.isdir(path):
                dirs.add(path)
            else:
                current_sources.append((path, stat.st_mtime))

        for path, mtime in current_sources:
            found_old = False
            for old_path, old_mtime in old_sources:
                if path == old_path:
                    if abs(mtime - old_mtime) > 0.001:
                        changes.update.add(path)
                    found_old = True
                    break
            if not found_old:
                changes.create.add(path)

        for old_path, old_mtime in old_sources:
            if not any((old_path == path for path, mtime in current_sources)):
                changes.delete.add(old_path)

        for dir in dirs:
            changes.merge(self.collect_changes(dir))

        return changes