import os
from pydgeot.processors.builtins import register_builtins


available = {}
""":type: dict[str, callable[pydgeot.app.App]"""


class Processor:
    """
    Base class for file processors. When generating content, an App will call can_process on each registered processor,
    in sequential order (sorted by the processors priority.) The first processor to return True will then be used for
    content preparation, generation, and deletion. Generally, preparation will determine what files a source file should
    generate, what other source files it depends on, and sets any context variables the source file creates. After all
    modified files have been prepared, generation will be run, creating and updating targets files in the build
    directory.
    """
    # Display name for config/logging/etc, None will use __class__.name. May be overridden by the register decorator.
    name = None
    """:type: str | None"""

    # Help message. May be overridden by the register decorator.
    help_msg = ''
    """:type: str"""

    # Processors can_process methods are checked in order of priority. Processors with higher priority values are
    # checked earlier. May be overridden by the register decorator.
    priority = 50
    """:type: int"""

    def __init__(self, app):
        """
        :param app: Parent App instance.
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
        raise NotImplementedError

    def prepare(self, path):
        """
        Preprocess a source file. Sets targets and dependencies, without generating content.

        :param path: File path to preproess.
        :type path: str
        """
        pass

    def generate(self, path):
        """
        Generate content for a prepared source file. Called after all preparation is complete.

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

    # noinspection PyMethodMayBeStatic
    def generation_complete(self):
        """
        Called after a Generator instance finishes processing a group of changes.
        """
        pass

    # noinspection PyMethodMayBeStatic
    def reset(self):
        """
        Called when an App instance is reset.
        """
        pass


# noinspection PyPep8Naming
class register:
    """
    Decorator to add Processor class definitions to the list of available processors.
    """

    def __init__(self, name=None, priority=None, help_msg=None):
        """
        Decorator to add Processor class definitions to the list of available processors.

        :param name: Name of the processor, if None, the name of the processor class is used.
        :type name: str | None
        :param priority: Processor checking priority. Higher values are checked earlier.
        :type priority: int | None
        :param help_msg: Usage text describing the processors purpose.
        :type help_msg: str | None
        """
        self.name = name
        self.priority = priority
        self.help_msg = help_msg

    def __call__(self, cls):
        name = self.name or cls.name or cls.__name__
        cls.name = name
        cls.priority = self.priority or cls.priority
        cls.help_msg = self.help_msg or cls.help_msg
        available[name] = cls
        return cls
