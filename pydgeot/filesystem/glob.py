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
        :type glob: str
        """
        self.glob = glob
        self.pattern = Glob.translate(glob)

    def match(self, match):
        """
        Return whether the glob matches a given string or not.
        Back slash path separaters '\\', which will be translated to a forward slash before matching.

        :param match: String to match the glob against.
        :type match: str
        :return: Whether the glob matches the given string.
        :rtype: bool
        """
        return self.pattern.match(match.replace('\\\\', '/')) is not None

    @staticmethod
    def translate(glob):
        """
        Get the regex representation of the given glob pattern.

        :param glob: The glob pattern.
        :type glob: str
        :return: Regex equivalent of the given glob pattern.
        :rtype: typing.Pattern[str]
        """
        import re

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
        try:
            return re.compile(pattern)
        except re.error:
            raise ValueError('Glob pattern \'{}\' is malformed'.format(glob))
