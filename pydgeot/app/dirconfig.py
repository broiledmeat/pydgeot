import os
import json


class DirConfig:
    """

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
        """:type: set[str]"""
        self.extra = {}
        """:type: dict[str, object]"""

        self._load(os.path.join(path, '{}pydgeot.conf'.format('' if path == app.root else '.')))

    def _load(self, path):
        from pydgeot.app import AppError

        config = {}
        if os.path.isfile(path):
            try:
                with open(path) as fh:
                    config = json.load(fh)
            except ValueError as e:
                raise AppError('Could not load config \'{}\': \'{}\''.format(path, e))

        directory = os.path.dirname(path)
        parent = None
        if directory != self.app.root:
            parent_path = os.path.dirname(directory)
            parent = self.app.get_config(parent_path)

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

        ignore = config.pop('ignore', None)
        if isinstance(ignore, list):
            self.ignore = ignore
        elif ignore is None and parent is not None:
            self.ignore = parent.ignore

        self.extra = config
        if parent is not None:
            self.extra = DirConfig._merge_dict(parent.extra, self.extra)

    @staticmethod
    def _merge_dict(a, b):
        """
        :type a: dict
        :type b: dict
        """
        import copy
        merged = copy.copy(a)
        for key in b:
            if key in merged and isinstance(merged[key], dict) and isinstance(b[key], dict):
                merged[key] = DirConfig._merge_dict(merged[key], b[key])
                continue
            merged[key] = b[key]
        return merged
