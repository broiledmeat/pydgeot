import os
import re
import json
from collections import namedtuple

CONFIG_DEFAULTS = {
    "ignore": {
        "dot_files": False,
        "paths": []
    }
}

def abspath(path):
    return os.path.abspath(os.path.expanduser(path))

RenderResult = namedtuple('RenderResult', ['content', 'handler'])

class PydgeotCore:
    """
    Base class providing access to configuration information and content rendering.
    """
    DEFAULT_CONFIG_FILE = './.pydgeotconf.json'

    def __init__(self, source_root, config_file=DEFAULT_CONFIG_FILE):
        self.source_root = abspath(source_root)
        self.config_file = abspath(os.path.join(source_root, config_file))

        if os.path.isfile(self.config_file):
            self.append_config(json.loads(open(self.config_file).read()))

    def append_config(self, config):
        if not hasattr(self, 'config'):
            self.config = {}
        self._append_config_dict(self.config, config)

    def _append_config_dict(self, target, source):
        for key, value in source.items():
            override = key.endswith('!')
            key = key.rstrip('!')
            in_target = isinstance(target, dict) and key in target

            if isinstance(value, dict):
                if override or not in_target or not isinstance(target[key], dict):
                    target[key] = {}
                self._append_config_dict(target[key], value)
                continue
            elif not override and in_target and isinstance(value, list):
                target[key] += value
                print('APPEND ' + key)
                continue
            target[key] = value

    def is_ignored(self, *paths):
        for path in paths:
            if path == self.config_file:
                return True
            if self.config['ignore']['dot_files'] and any(part.startswith('.') for part in path.split(os.path.sep)):
                return True
            if any([re.match(regex, path) for regex in self.config['ignore']['paths']]):
                return True
        return False

    def render(self, source_path):
        """
        Return file contents, after having rendered the file with a handler if available.

        Args:
            source_path (str): Source file to render.
        Raises:
            IOError: If source_path is not a file.
        Returns:
            RenderResult: Named tuple containing the files contents, and handler (or None if not used.)
        """
        from .handlers import get_handler

        if not os.path.isfile(source_path):
            raise IOError('Source path is not a file', source_path)

        handler = get_handler(os.path.relpath(source_path, self.source_root))
        if handler is not None:
            content = handler.render(self.source_root, source_path)
        else:
            content = open(source_path, 'rb').read()

        return RenderResult(content, handler)
