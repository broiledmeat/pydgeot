"""
File Handlers
File handler manager and file handlers.

An appropriate handler should be retrieved with get_handler(file_uri). E.g.; get_handler("ok.html") would return a
JinjaHandler instance, or None if the jinja2 module could not be found. 

File handler classes should have the following attributes:
 - desc (str) Optional. Class attribute. Short description of what the handler handles.
 - uris (str): Class attribute. A regex to match against URIs. What paths or file extensions the handler will handle.
 - render (func(root, path)): Function that returns rendered content for the file path given to it.
 - dependencies (func(root, path)): Optional. Function that returns any other files that the file path given to it
                                    depends on in order to render.
"""
_handlers = []

def handler(cls):
    """
    Decorator for adding a file handler class to the available handlers.
    """
    if hasattr(cls, 'uris') and hasattr(cls, 'render'):
        import re
        cls.uris = re.compile(cls.uris)
        _handlers.append(cls())
    return cls

def get_handler(uri):
    """
    Get a handler that can handle the given URI.

    Args:
        uri (str): URI to get an appropriate handler for.
    Returns:
        handler or None if no handler was found.
    """
    for handler in _handlers:
        if handler.uris.match(uri):
            return handler
    return None

def get_handlers():
    """
    Get all handlers as a list.

    Args:
        None
    Returns:
        list(handler)
    """
    return _handlers

try:
    import jinja2

    @handler
    class JinjaHandler:
        """
        Jinja2 template handler.
        """
        desc = 'Jinja2 Templates (*.html, *.htm)'
        uris = '.*\.html$'
        def __init__(self):
            self.envs = {}
        def render(self, source_root, source_path):
            return self._env(source_root).from_string(open(source_path).read()).render()
        def dependencies(self, source_root, source_path):
            body = self._env(source_root).parse(open(source_path).read()).body
            return self._find_deps(source_root, body)
        def _env(self, source_root):
            """
            Return a Jinja environment handler for the source root.

            Args:
                source_root (str): The file paths root, passed from self.dependencies.
            Returns:
            jinja2.Environment
            """
            if source_root not in self.envs:
                self.envs[source_root] = jinja2.Environment(loader=jinja2.FileSystemLoader(source_root))
            return self.envs[source_root]
        def _find_deps(self, source_root, body):
            """
            Recursively iterates through a Jinja template body, looking for any Extends or Include nodes.

            Args:
                source_root (str): The file paths root, passed from self.dependencies.
                body (jinja2.nodes.*.body): The body to iterate through.
            Returns:
                list(str): Files the Jinja template body depends on to render.
            """
            import os
            deps = set()
            for part in body:
                if isinstance(part, (jinja2.nodes.Extends, jinja2.nodes.Include)):
                    deps.add(os.path.join(source_root, part.template.value))
                elif isinstance(part, jinja2.nodes.Block):
                    deps |= self._find_deps(source_root, part.body)
            return deps
except ImportError:
    pass

try:
    from lesscpy.lessc import parser, formatter

    @handler
    class LesscpyHandler:
        """
        Lesscpy CSS handler.
        """
        desc = 'Lesscpy CSS (*.css)'
        uris = '.*\.css$'
        def __init__(self):
            self.parser = parser.LessParser()
            self.formatter = formatter.Formatter(self.lessopts())
        def render(self, source_root, source_path):
            self.parser.parse(filename=source_path)
            return self.formatter.format(self.parser)
        class lessopts:
            """
            Formatting options for Lesscpy formatter.
            """
            def __init__(self):
                self.minify = False
                self.xminify = False
                self.tabs = False
                self.spaces = True
except ImportError:
    pass