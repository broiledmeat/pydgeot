"""
Development Server
An extremely simple file server that renders files with available handlers (HTML templates, CSS helpers, etc.)
"""
import os
import re
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from . import PydgeotCore, abspath

CONFIG_DEFAULTS = {
    "devserver": {
        "address": "localhost",
        "port": 8000,
        "index_files":[
            "index.html"
        ],
        "redirects": {}
    }
}

class Server(PydgeotCore, HTTPServer):
    """
    HTTPServer containing configuration data.
    """
    def __init__(self,
                 source_root=None,
                 config_file=PydgeotCore.DEFAULT_CONFIG_FILE,
                 config={}):
        """
        Initialises the server and properties needed for RequestHandlers.

        Args:
            source_root (str): Root directory to serve files from.
            config_file (str): Filepath to load configuration from.
            config (dict): Additional configuration to load.
        """
        self.append_config(CONFIG_DEFAULTS)
        PydgeotCore.__init__(self, source_root, config_file)
        self.append_config(config)

        self.address = self.config['devserver']['address']
        self.port = self.config['devserver']['port']
        self.index_files = self.config['devserver']['index_files']
        self.url_redirects = [(re.compile('^/{0}(/.*)?$'.format(url.strip('/'))), abspath(path))
                              for url, path in self.config['devserver']['redirects'].items()]

        HTTPServer.__init__(self, (self.address, self.port), RequestHandler)

    def start(self):
        self.serve_forever()

    def stop(self):
        self.socket.close()

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
                    print(self.path)
                    print(source_path)
                    break

        # If source_path is a directory, try to find an index file
        if os.path.isdir(source_path):
            # Redirect to 'path/' if path doesn't end with a '/'' already.
            if not self.path.endswith('/'):
                self.send_response(301)
                self.send_header('Location', self.path + '/')
                self.end_headers()
                return

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

        # If the file should be ignored, or doesn't exist, 404
        if self.server.is_ignored(self.path, source_path) or not os.path.isfile(source_path):
            self.send_error(404, 'File Not Found: ' + source_path)
            return
        # If source_path is a directory (and thus no index file was found,) serve a generated index
        elif os.path.isdir(source_path):
            return self.serve_index(source_path)

        # Guess the mimetype and set headers
        mimetype = mimetypes.guess_type(source_path)[0]
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.end_headers()

        # Render
        result = self.server.render(source_path)
        self.wfile.write(result.content)

    def serve_index(self, source_path):
        """
        Constructs and serves a simple HTML document listing file contents for the requested path.

        Args:
            None
        Returns:
            None
        """
        content = '<!DOCTYPE html>\n<html><head><title>{0}</title></head><body>\n'.format(self.path)

        for filename in sorted(os.listdir(source_path)):
            if os.path.isdir(os.path.join(source_path, filename)):
               filename += '/'
            content += '<a href="{0}">{0}</a><br>\n'.format(filename)

        content += '</body></html>'

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(content + '\n', 'utf-8'))
