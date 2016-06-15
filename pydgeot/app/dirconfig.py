import os
import json


class DirConfig:
    """
    App configuration for a directory.
    """

    def __init__(self, app, path):
        """
        Initialize a new DirConfig instance for the given App.

        :param app: App to associated with the directory.
        :type app: pydgeot.app.App
        :param path:
        :type path: str
        """
        self.app = app
        self.path = path
        self.processors = []
        """:type: list[pydgeot.processors.Processor]"""
        self.ignore = set()
        """:type: set[pydgeot.filesystem.Glob]"""
        self.extra = {}
        """:type: dict[str, object]"""

        self._load(os.path.join(path, '{}pydgeot.conf'.format('' if path == app.root else '.')))

    def _load(self, path):
        """
        Load in configuration data from a file path.

        :param path: Config file to load.
        :type path: str
        """
        from pydgeot.app import AppError
        from pydgeot.filesystem import Glob

        config = {}
        if os.path.isfile(path):
            try:
                with open(path) as fh:
                    config = json.load(fh)
            except ValueError as e:
                raise AppError('Could not load config \'{}\': \'{}\''.format(path, e))

        # Find the parent config, so it can be inherited from.
        directory = os.path.dirname(path)
        parent = None
        if directory != self.app.root:
            parent_path = os.path.dirname(directory)
            parent = self.app.get_config(parent_path)

        # Convert a 'processors' key to a list of processor instances.
        processors = config.pop('processors', None)
        if isinstance(processors, list):
            for processor in processors:
                processor_inst = self.app.processors.get(processor, None)
                if processor_inst is not None:
                    self.processors.append(processor_inst)
                else:
                    raise AppError('Could not load config \'{}\', unable to find procssor: \'{}\''.format(path,
                                                                                                          processor))
            self.processors = sorted(self.processors, key=lambda p: p.priority, reverse=True)
        elif processors is None and parent is not None:
            self.processors = parent.processors

        # Convert an 'ignore' key to a list of matchable globs.
        ignore = config.pop('ignore', None)
        if isinstance(ignore, list):
            for glob in ignore:
                if directory not in (self.app.root, self.app.source_root):
                    glob = self.app.relative_path(directory).replace('\\', '/') + '/' + glob
                try:
                    self.ignore.add(Glob(glob))
                except ValueError:
                    raise AppError('Malformed glob in \'{}\': \'{}\''.format(path, glob))
        elif ignore is None and parent is not None:
            self.ignore = parent.ignore

        # Any extra keys remain as a dictionary, being merged in with the parent configs extra data.
        self.extra = config
        if parent is not None:
            self.extra = DirConfig._merge_dict(parent.extra, self.extra)

    @staticmethod
    def _merge_dict(target, source):
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
                merged[key] = DirConfig._merge_dict(merged[key], source[key])
                continue
            merged[key] = source[key]
        return merged
