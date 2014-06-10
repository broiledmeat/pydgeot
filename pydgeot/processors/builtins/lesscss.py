import os
from lesscpy.lessc import parser, formatter
from pydgeot.processors import register, Processor


@register()
class LessCSSProcessor(Processor):
    """
    Compile a Less (http://lesscss.org/) source file in to the build directory.
    """
    def __init__(self, app):
        super().__init__(app)
        self.parser = parser.LessParser()
        self.formatter = formatter.Formatter(self._LessOpts())

    def can_process(self, path):
        return path.endswith('.css')

    def generate(self, path):
        self.parser.parse(filename=path)
        rel = os.path.relpath(path, self.app.source_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        f = open(target, 'w')
        f.write(self.formatter.format(self.parser))
        f.close()
        self.app.sources.set_targets(path, [target])

    class _LessOpts:
        def __init__(self):
            self.minify = False
            self.xminify = False
            self.tabs = False
            self.spaces = True
