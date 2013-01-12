import os
from pydgeot.processors import register, Processor
from lesscpy.lessc import parser, formatter

@register()
class LessCSSProcessor(Processor):
    def __init__(self, app):
        super().__init__(app)
        self.parser = parser.LessParser()
        self.formatter = formatter.Formatter(self._LessOpts())

    def can_process(self, path):
        return path.endswith('.css')

    def process_update(self, path):
        self.parser.parse(filename=path)
        rel = os.path.relpath(path, self.app.content_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        f = open(target, 'w')
        f.write(self.formatter.format(self.parser))
        f.close()
        return [target]

    class _LessOpts:
        def __init__(self):
            self.minify = False
            self.xminify = False
            self.tabs = False
            self.spaces = True