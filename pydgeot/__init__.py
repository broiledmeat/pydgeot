import os
import configparser
from collections import namedtuple

def abspath(path):
    return os.path.abspath(os.path.expanduser(path))

RenderResult = namedtuple('RenderResult', ['content', 'handler'])

class PydgeotCore:
    DEFAULT_CONFIG_FILE = './.pydgeot.conf'

    def __init__(self, source_root, config_file=DEFAULT_CONFIG_FILE):
        self.source_root = abspath(source_root)
        self.config_file = abspath(os.path.join(source_root, config_file))

        self.config_parser = configparser.ConfigParser(allow_no_value=True)

        if os.path.isfile(self.config_file):
            self.config_parser.read(self.config_file)

    def has_conf(self, section, key=None):
        if key is None:
            return section in self.config_parser
        return section in self.config_parser and key in self.config_parser[section]

    def get_conf(self, section, key=None):
        if key is None:
            return list(self.config_parser[section].items())
        else:
            return self.config_parser[section][key]

    def get_conf_list(self, section, key=None, delimiter=','):
        if key is None:
            return list(self.config_parser[section].keys())
        else:
            return self.config_parser[section][key].split(delimiter)

    def get_conf_sections(self):
        return list(self.config_parser.sections())

    def set_conf(self, section, key, value):
        if not self.config_parser.has_section(section):
            self.config_parser.add_section(section)
        self.config_parser[section][key] = value

    def set_conf_list(self, section, values):
        if not self.config_parser.has_section(section):
            self.config_parser.add_section(section)
        for value in values:
            self.config_parser[section][value] = None

    def load_conf_dict(self, conf):
        for section, section_value in conf.items():
            if isinstance(section_value, dict):
                for key, value in section_value.items():
                    self.set_conf(section, key, value)
            elif isinstance(section_value, list):
                self.set_conf_list(section, section_value)

    def render(self, source_path):
        """
        Render a file, using a handler if available.

        Args:
            source_path (str): Source file to render.
        Raises:
            IOError: If source_path is not a file.
        Returns:
            str: Rendered content.
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
