import os
import inspect

available = {}


class Processor:
    """
    Base class for file processors.
    """
    priority = 50  # Processors can_process methods are checked in order of priority. Higher priority processors
                   # are checked earlier.

    def __init__(self, app):
        """
        Args:
            app: Parent App instance.
        """
        self.app = app

    def can_process(self, path):
        """
        Check if the Processor is able to process the given file path.

        Args:
            path: File path to check.

        Returns:
            True if the file path is processable, False otherwise.
        """
        return False

    def process_create(self, path):
        """
        Process a new source file.

        Args:
            path: File path to process.

        Returns:
            A list of file paths that were built.
        """
        return self.process_update(path)

    def process_update(self, path):
        """
        Process an updated source file.

        Args:
            path: File path to process.

        Returns:
            A list of file paths that were built.
        """
        return []

    def process_delete(self, path):
        """
        Process a deleted file.

        Args:
            path: File path to process.
        """
        for target in self.app.filemap.get_targets(path):
            if os.path.isfile(target):
                try:
                    os.remove(target)
                    root = os.path.dirname(target)
                    if not os.listdir(root):
                        os.rmdir(root)
                except PermissionError:
                    pass

    def get_dependencies(self, path):
        """
        Get other files the given file depends on.

        Args:
            Path: File path to get dependencies for.

        Returns:
            A list of file dependencies.
        """
        return []

    def process_changes_complete(self):
        """
        Called after a Generator instance finishes processing a group of changes.
        """
        pass

    def reset(self):
        """
        Called when an App instance is reset.
        """
        pass


class register:
    """
    Decorator to add Processor class definitions to the list of available processors.
    """
    def __init__(self):
        mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
        if '.' in mod_name:
            mod_name = mod_name[mod_name.rindex('.') + 1:]
        self.module_name = mod_name

    def __call__(self, cls):
        global available
        if self.module_name not in available:
            available[self.module_name] = []
        available[self.module_name].append(cls)
