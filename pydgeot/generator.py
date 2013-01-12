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
            processor = self.app.get_processor(path)
            if processor is not None:
                processor.process_delete(path)
            for target in self.filemap.get_targets(path):
                sources = self.filemap.get_targets(target, reverse=True)
                if len(sources) <= 1 and os.path.isfile(target):
                    os.remove(target)
            self.filemap.remove_source(path)

        dependencies = set()
        for path in changes.update:
            dependencies |= set(self.filemap.get_dependencies(path, reverse=True))
        changes.update |= dependencies

        for path in changes.create | changes.update:
            processor = self.app.get_processor(path)
            if processor is not None:
                print('Processing {0} with {1}'.format(os.path.relpath(path, self.app.content_root), processor.__class__.__name__))
                try:
                    dependencies = processor.get_dependencies(path)
                except Exception as e:
                    print('Exception occurred getting dependencies:', e)
                    continue
                try:
                    proc_func = processor.process_create if path in changes.create else processor.process_update
                    targets = proc_func(path)
                except Exception as e:
                    print('Exception occurred while processing:', e)
                    continue
                self.filemap.set_dependencies(path, dependencies)
                self.filemap.set_targets(path, targets)
        self.filemap.commit()

    def collect_changes(self, root=None):
        if root is None:
            root = self.app.content_root
        changes = ChangeSet()

        dirs = set()

        old_sources = self.filemap.get_sources(root, mtimes=True)
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
