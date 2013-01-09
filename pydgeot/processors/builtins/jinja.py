import os
import jinja2
from pydgeot.processors import register, Processor

@register()
class JinjaProcessor(Processor):
    def __init__(self, app):
        super().__init__(app)
        self.envs = {}

    def can_process(self, path):
        return path.endswith('.html')

    def process(self, path):
        if not self._has_template_flag(path):
            env = self._get_env(self.app.content_root)
            content = open(path).read()
            template = env.from_string(content)
            rel = os.path.relpath(path, self.app.content_root)
            target = os.path.join(self.app.build_root, rel)
            f = open(target, 'w')
            f.write(template.render())
            f.close()
            return [target]
        return []

    def get_dependencies(self, path):
        body = self._get_env(self.app.content_root).parse(open(path).read()).body
        return self._find_deps(self.app.content_root, body)

    def _get_env(self, root):
        if root not in self.envs:
            self.envs[root] = jinja2.Environment(loader=jinja2.FileSystemLoader(root))
        return self.envs[root]

    def _has_template_flag(self, path):
        body = self._get_env(self.app.content_root).parse(open(path).read()).body
        for part in body:
            if isinstance(part, jinja2.nodes.Assign) and \
               part.target.name == 'template_only' and \
               part.node.value:
                return True
        return False

    def _find_deps(self, root, body):
        deps = set()
        for part in body:
            if isinstance(part, (jinja2.nodes.Extends, jinja2.nodes.Include)):
                deps.add(os.path.join(root, part.template.value))
            elif isinstance(part, jinja2.nodes.Block):
                deps |= self._find_deps(root, part.body)
        return deps