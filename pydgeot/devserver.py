"""
Development Server
An extremely simple file server that renders files with available handlers (HTML templates, CSS helpers, etc.)
"""
import os
import re
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from .handlers import get_handler, get_handlers

class Server(HTTPServer):
    """
    HTTPServer containing configuration data.
    """
    # These regexes apply to paths relative to the source root path
    DEFAULT_INDEX_FILES = ['index.html']
    DEFAULT_URL_REDIRECTS = []

    def __init__(self,
                 address,
                 port,
                 source_root=None,
                 index_files=DEFAULT_INDEX_FILES,
                 url_redirects=DEFAULT_URL_REDIRECTS):
        """
        Initialises the server and properties needed for RequestHandlers.

        Args:
            address (str): Network address to serve on.
            port (int): Network port to serve on.
            source_root (str): Root directory to serve files from.
            index_files (list(str)): List of possible index file names.
            url_redirects: (list(str,str)): (uri,target) list of URI's to remap to a target path.
        """
        super(Server, self).__init__((address, port), RequestHandler)
        self.source_root = os.path.abspath(os.path.expanduser(source_root))
        self.index_files = index_files
        self.url_redirects = [(re.compile('^/%s(/.*)?$' % (url.strip('/'))), os.path.abspath(os.path.expanduser(path)))
                              for url, path in url_redirects]

class RequestHandler(BaseHTTPRequestHandler):
    """
    Custom BaseHTTPRequestHandler capable of server directory indexes and passing files to appropriate file handlers.
    """
    def do_GET(self):
        """
        Passes a requested file to Jinja2 and serves its rendered contents if the file path matches any of the regexes
        specified in Server.render_paths, serves a directory index, or otherwise serves a file directly.

        Args:
            None
        Returns:
            None
        """
        self.path = urllib.parse.unquote(self.path)
        source_root = self.server.source_root
        source_path = os.path.join(source_root, self.path.lstrip('/'))
        
        # Find matching url redirects and alter self.path and source_path accordingly
        if len(self.server.url_redirects) > 0:
            for url, target in self.server.url_redirects:
                match = url.match(self.path)
                if match is not None:
                    source_root = target
                    if match.group(1) is None:
                        self.path = '/'
                    else:
                        self.path = match.group(1)
                    source_path = os.path.join(source_root, self.path.lstrip('/'))
                    break

        # If source_path is a directory, try to find an index file
        if os.path.isdir(source_path):
            index_path = None
            o_path = self.path.lstrip('/')
            if len(o_path) > 0 and o_path[-1] != '/':
                o_path += '/'
            for index in self.server.index_files:
                path = o_path + index
                filepath = os.path.join(source_root, path.lstrip('/'))
                if os.path.isfile(filepath):
                    self.path = path.lstrip('/')
                    index_path = filepath
                    break
            if index_path is not None:
                source_path = index_path

        # If source_path is a directory (and thus no index file was found,) serve a generated index
        if os.path.isdir(source_path):
            return self.serve_index(source_path)
        elif not os.path.isfile(source_path):
            self.send_error(404,'File Not Found: %s' % source_path)

        # Guess the mimetype and set headers
        mimetype = mimetypes.guess_type(source_path)[0]
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.end_headers()

        # Pass off to a renderer if available
        handler = get_handler(self.path)
        if handler is not None:
            content = handler.render(source_root, source_path)
            self.wfile.write(bytes(content + '\n', 'utf-8'))
        else:
            self.wfile.write(open(source_path, 'rb').read())

    def serve_index(self, source_path):
        """
        Constructs and serves a simple HTML document listing file contents for the requested path.

        Args:
            None
        Returns:
            None
        """
        content = '<!DOCTYPE html>\n<html><head><title>%s</title></head><body>\n' % (self.path,)

        for filename in sorted(os.listdir(source_path)):
            rel_path = self.path + filename
            file_path = os.path.join(source_path, filename)
            name = filename

            if os.path.isdir(file_path):
                rel_path += '/'
                name += '/'

            content += '<a href="%s">%s</a><br>\n' % (rel_path, name)

        content += '</body></html>'

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(content + '\n', 'utf-8'))