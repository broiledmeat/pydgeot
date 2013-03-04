import os

class ChangeSet:
    """
    Contains a set of file changes.
    """
    def __init__(self):
        self.create = set()
        self.update = set()
        self.delete = set()
    def merge(self, other):
        """
        Merge from another ChangeSet.

        Args:
            other: ChangeSet to merge changes from.
        """
        self.create |= other.create
        self.update |= other.update
        self.delete |= other.delete

class Generator:
    """
    Source content builder for App instances.
    """
    def __init__(self, app):
        """
        Args:
            app: Parent App instance.
        """
        self.app = app

    def generate(self):
        """
        Build content for the App's root content directory.
        """
        if not os.path.isdir(self.app.build_root):
            os.makedirs(self.app.build_root)
        changes = self.collect_changes()
        self.process_changes(changes)

    def process_changes(self, changes):
        """
        Build content for a given ChangeSet.

        Args:
            changes: ChangeSet to build content for.
        """
        for path in changes.delete:
            self.app.process_delete(path)
            self.app.filemap.remove_source(path)
            self.app.filemap.commit()

        # Update dependencies for new or updated files
        for path in list(changes.create | changes.update):
            dependencies = self.app.get_dependencies(path)
            self.app.filemap.set_dependencies(path, dependencies)
            changes.update |= self.app.filemap.get_dependencies(path, reverse=True, recursive=True)

        for path in changes.create | changes.update:
            proc_func = self.app.process_create if path in changes.create else self.app.process_update
            targets = proc_func(path)
            if targets is not None:
                self.app.filemap.set_targets(path, targets)
                self.app.filemap.commit()

        for processor in self.app._processors:
            processor.process_changes_complete()

    def collect_changes(self, root=None):
        """
        Find new, updated, or deleted files in a directory.

        Args:
            root: Directory path to look for changes in.

        Returns:
            A ChangeSet instance, representing any changed files.
        """
        if root is None:
            root = self.app.source_root
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

        for path in dirs:
            changes.merge(self.collect_changes(path))

        return changes
