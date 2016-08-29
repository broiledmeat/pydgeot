class Glob:
    """
    Glob file matching.

    Supports the following special characters:
        '?'     Match any single character (excluding path separator)
        '*'     Match 0 or more characters (excluding path separators)
        '**'    Match 0 or more characters
    Escaped characters will not be specially processed, and will be placed directly in to the resulting regex. The
    exception being the back slash path separater '\\', which will be translated to a forward slash.

    '*.txt'     will match 'example.txt', but not 'childdir/example.txt' or 'otherchild/grandchild/sample.txt'
    '**.txt'    will match 'example.txt', 'childdir/example.txt', and 'otherchild/grandchild/sample.txt'
    '**/*.txt'  will not match 'example.txt', but will match 'childdir/example.txt' and
                'otherchild/grandchild/sample.txt'
    'ex??.txt'  will match 'exam.txt', but not 'example.txt'
    'ex??*.txt' will match 'exam.txt', and 'example.txt', but not 'exam/sample.txt'
    """
    def __init__(self, glob):
        """
        :type glob: str | Any
        """
        self.value = glob
        self.is_glob = Glob.is_glob(glob)
        if self.is_glob:
            import re
            self.regex = Glob.as_regex(glob)
            self._regex = re.compile(self.regex)
        else:
            self.regex = None
            self._regex = None

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.value == self.value

    def match_path(self, path):
        """
        Return whether the glob matches a given path or not.
        Back slash path separaters '\\', which will be translated to a forward slash before matching.

        :param path: Path to match the glob against.
        :type path: str
        :return: Whether the glob matches the given string.
        :rtype: bool
        """
        path = path.replace('\\\\', '/')
        if self._regex is None:
            return self.value == path
        return self._regex.match(path) is not None

    @staticmethod
    def is_glob(glob):
        """
        Determine if the given string is a glob or not.

        :param glob: The potential glob pattern.
        :type glob: str | Any
        :return: Whether the given string is a glob or not.
        :rtype: bool
        """
        if glob is None or not isinstance(glob, str):
            return False

        i = 0
        length = len(glob)
        while i < length:
            c = glob[i]
            if c == '\\':
                i += 1
            elif c in ('?', '*'):
                return True
            i += 1
        return False

    @staticmethod
    def as_regex(glob):
        """
        Get the regex representation of the given glob pattern.

        :param glob: The glob pattern.
        :type glob: str
        :return: Regex equivalent of the given glob pattern.
        :rtype: typing.Pattern[str]
        """
        pattern = '^'
        i = 0
        length = len(glob)
        while i < length:
            c = glob[i]
            if c == '\\':
                i += 1
                if i == length:
                    break
                c += glob[i]
                if c == '\\\\':
                    c = '/'
            elif c == '.':
                c = '\\.'
            elif c == '?':
                c = '[^/]'
            elif c == '*':
                if i < length - 1 and glob[i + 1] == '*':
                    i += 1
                    c = '.*'
                else:
                    c = '[^/]*'
            pattern += c
            i += 1
        pattern += '$'
        return pattern
