import os

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

    def generate(self):
        if not os.path.isdir(self.app.build_root):
            os.makedirs(self.app.build_root)
        changes = self.collect_changes()
        self.process_changes(changes)

    def process_changes(self,  changes):
        for path in changes.delete:
            self.app.process_delete(path)
            self.app.filemap.remove_source(path)
            self.app.filemap.commit()

        dependencies = set()
        for path in changes.update:
            dependencies |= set(self.app.filemap.get_dependencies(path, reverse=True))
        changes.update |= dependencies

        for path in changes.create | changes.update:
            proc_func = self.app.process_create if path in changes.create else self.app.process_update
            targets = proc_func(path)
            if targets is not None:
                self.app.filemap.set_dependencies(path, dependencies)
                self.app.filemap.set_targets(path, targets)
                self.app.filemap.commit()

        for processor in self.app._processors:
            processor.process_changes_complete()

    def collect_changes(self, root=None):
        if root is None:
            root = self.app.content_root
        changes = ChangeSet()

        dirs = set()

        old_sources = self.app.filemap.get_sources(root, mtimes=True)
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
