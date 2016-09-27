import os
import json


class BaseDirConfig:
    """
    Base app configuration for a directory.
    """
    _cached = {}
    """:type: dict[type, dict[str, DirConfig]]"""

    def __init__(self, app, path):
        """
        Initialize a new DirConfig instance for the given App. The `get` class method should be used instead of
        initializing this directly.

        :param app: App associated with the directory.
        :type app: pydgeot.app.App
        :param path: Directory to get configuration for.
        :type path: str
        """
        self.app = app
        self.path = path

        self._load()

    @classmethod
    def get(cls, app, path):
        """
        Get a DirConfig instance for the given file or directory path.

        :param app: App associated with the directory.
        :type app: pydgeot.app.App
        :param path:
        :type path: str
        """
        if os.path.isfile(path):
            path = os.path.dirname(path)

        if cls not in cls._cached:
            cls._cached[cls] = {}

        if path in cls._cached[cls]:
            return cls._cached[cls][path]

        config = cls(app, path)
        cls._cached[cls][path] = config
        return config

    def _load(self):
        """
        Load in the current path and parent configuration data.
        """
        from pydgeot.app import AppError

        config = {}
        config_path = os.path.join(self.path, '{}pydgeot.conf'.format('' if self.path == self.app.root else '.'))

        # Find the parent config, so it can be inherited from.
        parent = None
        if self.path != self.app.root:
            parent_path = os.path.dirname(self.path)
            parent = self.__class__.get(self.app, parent_path)

        if os.path.isfile(config_path):
            try:
                with open(config_path) as fh:
                    config = json.load(fh)
            except ValueError as e:
                raise AppError('Could not load config \'{}\': \'{}\''.format(config_path, e))

        self._parse(config_path, config, parent)

    def _parse(self, config_path, config, parent):
        """
        Parse current path and parent configuration data retrieved from _load.

        :type config_path: str
        :type config: dict[str, Any]
        :type parent: DirConfig | None
        """
        raise NotImplementedError

    @classmethod
    def _merge_dict(cls, target, source):
        """
        Return a merged copy of two dictionaries. Overwriting any matching keys from the second over the first, but
        merging any dictionary values.

        :param target: Original dictionary to copy and update.
        :type target: dict
        :param source: Dictionary to update items from.
        :type source: dict
        :return: Copied and updated target dictionary.
        :rtype: dict
        """
        import copy
        merged = copy.copy(target)
        for key in source:
            if key in merged and isinstance(merged[key], dict) and isinstance(source[key], dict):
                merged[key] = cls._merge_dict(merged[key], source[key])
                continue
            merged[key] = source[key]
        return merged


class DirConfig(BaseDirConfig):
    """
    App configuration for a directory.
    """
    def __init__(self, app, path):
        """
        Initialize a new DirConfig instance for the given App. The `get` class method should be used instead of
        initializing this directly.

        :param app: App to associated with the directory.
        :type app: pydgeot.app.App
        :param path:
        :type path: str
        """
        self.processors = []
        """:type: list[pydgeot.processors.Processor]"""
        self.ignore = set()
        """:type: set[pydgeot.filesystem.Glob]"""
        self.extra = {}
        """:type: dict[str, object]"""

        super().__init__(app, path)

    def _parse(self, config_path, config, parent):
        """
        Parse current path and parent configuration data retrieved from _load.

        :type config_path: str
        :type config: dict[str, Any]
        :type parent: DirConfig | None
        """
        from pydgeot.app import AppError
        from pydgeot.filesystem import Glob

        # Convert a 'processors' key to a list of processor instances.
        processors = config.pop('processors', None)
        if isinstance(processors, list):
            for processor in processors:
                processor_inst = self.app.processors.get(processor, None)
                if processor_inst is not None:
                    self.processors.append(processor_inst)
                else:
                    raise AppError('Could not load config \'{}\', unable to find processor: \'{}\''.format(config_path,
                                                                                                           processor))
            self.processors = sorted(self.processors, key=lambda p: p.priority, reverse=True)
        elif processors is None and parent is not None:
            self.processors = parent.processors

        # Convert an 'ignore' key to a list of matchable globs.
        ignore = config.pop('ignore', None)
        if isinstance(ignore, list):
            for glob in ignore:
                if self.path not in (self.app.root, self.app.source_root):
                    glob = self.app.relative_path(self.path).replace('\\', '/') + '/' + glob
                try:
                    self.ignore.add(Glob(glob))
                except ValueError:
                    raise AppError('Malformed glob in \'{}\': \'{}\''.format(config_path, glob))
        elif ignore is None and parent is not None:
            self.ignore = parent.ignore

        # Any extra keys remain as a dictionary, being merged in with the parent configs extra data.
        self.extra = config
        if parent is not None:
            self.extra = self.__class__._merge_dict(parent.extra, self.extra)
