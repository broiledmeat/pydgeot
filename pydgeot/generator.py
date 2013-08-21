import os
import datetime


class ChangeSet:
    """
    Contains a set of file changes.
    """
    def __init__(self):
        self.generate = set()
        self.delete = set()

    def merge(self, other):
        """
        Merge from another ChangeSet.

        Args:
            other: ChangeSet to merge changes from.
        """
        self.generate |= other.generate
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
        Build content for the Apps root content directory.
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
            self.app.processor_delete(path)

        # Prepare new or updated files to set targets and dependencies. Add those dependencies to another ChangeSet to
        # be prepared.
        dep_changes = ChangeSet()
        for path in list(changes.generate):
            # Grab dependencies before preparing, in case any context vars had been removed.
            source_deps = set([s.path for s in self.app.sources.get_dependencies(path, reverse=True, recursive=True)])
            context_deps = set([c.source for c in
                                self.app.contexts.get_dependencies(path, reverse=True, recursive=True)])

            # Prepare the source to refresh any new dependencies
            self.app.processor_prepare(path)

            # Add any files the source is dependent on or depends on it
            source_deps |= set([s.path for s in self.app.sources.get_dependencies(path, reverse=True, recursive=True)])
            context_deps |= set([c.source for c in
                                 self.app.contexts.get_dependencies(path, reverse=True, recursive=True)])

            # Get source dependencies for context dependency sources.
            source_deps |= set([s.path
                                for c in context_deps
                                for s in self.app.sources.get_dependencies(c, reverse=True, recursive=True)])

            # Add source and context dependencies to the changeset.
            dep_changes.generate |= source_deps | context_deps

        # Prepare dependent changes that weren't in the original changes list
        for path in (dep_changes.generate - changes.generate):
            self.app.processor_prepare(path)

        # Generate everything
        for path in (changes.generate | dep_changes.generate):
            self.app.processor_generate(path)

        # Finish generation
        self.app.processor_generation_complete()

        # Commit database changes
        self.app.db_connection.commit()

    def collect_changes(self, root=None):
        """
        Find updated or deleted files in a directory.

        Args:
            root: Directory path to look for changes in.

        Returns:
            A ChangeSet instance, representing any changed files.
        """
        if root is None:
            root = self.app.source_root
        changes = ChangeSet()

        dirs = set()

        old_sources = dict([(s.path, s.modified) for s in self.app.sources.get_sources(root, recursive=False)])
        current_sources = {}
        if os.path.isdir(root):
            for filename in os.listdir(root):
                path = os.path.join(root, filename)
                stat = os.stat(path)
                if os.path.isdir(path):
                    dirs.add(path)
                else:
                    current_sources[path] = datetime.datetime.fromtimestamp(stat.st_mtime)

        for path, mtime in current_sources.items():
            if path not in old_sources or (mtime - old_sources[path]).total_seconds() > 1:
                changes.generate.add(path)

        for old_path, old_mtime in old_sources.items():
            if old_path not in current_sources:
                changes.delete.add(old_path)

        for path in dirs:
            changes.merge(self.collect_changes(path))

        return changes
