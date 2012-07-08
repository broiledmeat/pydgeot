import os
import configparser
from collections import namedtuple

def abspath(path):
    return os.path.abspath(os.path.expanduser(path))

RenderResult = namedtuple('RenderResult', ['content', 'handler'])

class PydgeotCore:
    """
    Base class providing access to configuration information and content rendering.
    """
    DEFAULT_CONFIG_FILE = './.pydgeot.conf'

    def __init__(self, source_root, config_file=DEFAULT_CONFIG_FILE):
        self.source_root = abspath(source_root)
        self.config_file = abspath(os.path.join(source_root, config_file))

        self.config_parser = configparser.ConfigParser(allow_no_value=True)

        if os.path.isfile(self.config_file):
            self.config_parser.read(self.config_file)

    def has_conf(self, section, key=None):
        """
        Check a section or a section key for existance.

        Args:
            section (str): Section name to check.
            key (str): Optional. Key name to check.
        Returns:
            bool: True if the section or section key exists.
        """
        if key is None:
            return section in self.config_parser
        return section in self.config_parser and key in self.config_parser[section]

    def get_conf(self, section, key=None, type=None):
        """
        Get the value for a section key. If no key is provided, a list of key/value tuples for the section will be
        returned.

        Args:
            section (str): Section name.
            key (str): Optional. Section key name.
            type (type): Optional. Return a section keys value as a specific type. Defaults to str.
        Returns:
            object or list(tuple(str, str)): The section keys value if key is specified, otherwise a list of tuples
                                             containing key names and values in the section.
        """
        if key is None:
            return list(self.config_parser[section].items())
        else:
            if type in (None, str):
                return self.config_parser[section][key]
            elif type is int:
                return self.config_parser[section].getint(key)
            elif type is float:
                return self.config_parser[section].getfloat(key)
            elif type is bool:
                return self.config_parser[section].getboolean(key)

    def get_conf_list(self, section, key=None, delimiter=','):
        """
        Get the value for a section key as a list. If only a section name is provided, the sections key names will be
        returned.

        Args:
            section (str): Section name.
            key (str): Optional. Section key name.
            delimiter (str): Optional. String to split the section keys value with.
        Returns:
            list(str): A section keys values after being split by the delimiter, or a sections key names.
        """
        if key is None:
            return list(self.config_parser[section].keys())
        else:
            return self.config_parser[section][key].split(delimiter)

    def get_conf_sections(self):
        """
        Get a list of section names.

        Args:
            None
        Return:
            list(str)
        """
        return list(self.config_parser.sections())

    def set_conf(self, section, key, value):
        """
        Set a section keys value, creating the section if needed.

        Args:
            section (str): Section name.
            key (str): Key name.
            value (str): Section keys value.
        Returns:
            None
        """
        if not self.config_parser.has_section(section):
            self.config_parser.add_section(section)
        self.config_parser[section][key] = str(value)

    def set_conf_list(self, section, values):
        """
        Set a sections key names.

        Args:
            section (str): Section name.
            values (list(str)): List of key names.
        Returns:
            None
        """
        if not self.config_parser.has_section(section):
            self.config_parser.add_section(section)
        for value in values:
            self.config_parser[section][value] = None

    def load_conf_dict(self, conf):
        """
        Load config values from a dictionary.

        The keys are used as section names, and must be strings.
        The values can either be dict(str, str) or list(str).
        If the values are dictionaries, the keys and values will be added to the section. If the values are lists,
        then the items will be used as key names, with no values.

        Args:
            conf (dict): Dictionary to load.
        Returns:
            None
        """
        for section, section_value in conf.items():
            if isinstance(section_value, dict):
                for key, value in section_value.items():
                    self.set_conf(section, key, value)
            elif isinstance(section_value, list):
                self.set_conf_list(section, section_value)

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
