import os
import inspect

available = {}


class Processor:
    """
    Base class for file processors.
    """
    priority = 50  # Processors can_process methods are checked in order of priority. Processors with higher priority
                   # values are checked earlier.

    def __init__(self, app):
        """
        :param app: Parnet App instance.
        :type app: pydgeot.app.App
        """
        self.app = app

    def can_process(self, path):
        """
        Check if the Processor is able to process the given file path.

        :param path: File path to check.
        :type path: str
        :return: If the file path is processable.
        :rtype: bool
        """
        return False

    def prepare(self, path):
        """
        Preprocess a source file. Sets targets and dependencies, without generating content.

        :param path: File path to preproess.
        :type path: str
        """
        pass

    def generate(self, path):
        """
        Generate content for a prepared source file.

        :param path: File path to process.
        :type path: str
        """
        pass

    def delete(self, path):
        """
        Process a deleted file. Deletes the container target directory if it is empty.

        :param path: File path to delete.
        :type path: str
        """
        for target in [t.path for t in self.app.sources.get_targets(path)]:
            if os.path.isfile(target) or os.path.islink(target):
                try:
                    os.unlink(target)
                    root = os.path.dirname(target)
                    if not os.listdir(root):
                        os.rmdir(root)
                except PermissionError:
                    pass
        self.app.contexts.remove_context(source=path)
        self.app.sources.remove_source(path)

    def generation_complete(self):
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
        self.module_name = inspect.getmodule(inspect.stack()[1][0]).__name__

    def __call__(self, cls):
        global available
        if self.module_name not in available:
            available[self.module_name] = []
        available[self.module_name].append(cls)
