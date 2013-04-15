import os
import jinja2
from pydgeot.processors import register, Processor

@register()
class JinjaProcessor(Processor):
    TEMPLATE_FIELDS = {
        'name': (str, None),
        'template_only': (bool, False)
    }

    def __init__(self, app):
        super().__init__(app)
        self.envs = {}

    def can_process(self, path):
        return path.endswith('.html')

    def process_update(self, path):
        fields = self._get_template_fields(path)
        if 'template_only' in fields and fields['template_only'] != 'true':
            env = self._get_env(self.app.source_root)
            content = open(path).read()
            template = env.from_string(content)
            rel = os.path.relpath(path, self.app.source_root)
            target = os.path.join(self.app.build_root, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            f = open(target, 'w', encoding='utf-8')
            f.write(template.render())
            f.close()
            return [target]
        return []

    def get_dependencies(self, path):
        body = self._get_env(self.app.source_root).parse(open(path).read()).body
        return self._find_deps(self.app.source_root, body)

    def _get_env(self, root):
        if root not in self.envs:
            self.envs[root] = jinja2.Environment(loader=jinja2.FileSystemLoader(root))
        return self.envs[root]

    def _get_template_fields(self, path):
        fields = dict((name, val[1]) for name, val in self.TEMPLATE_FIELDS.items())
        body = self._get_env(self.app.source_root).parse(open(path).read()).body
        parts = [(p.target.name.lower(), p.node) for p in body
                 if isinstance(p, jinja2.nodes.Assign) and p.target.name.lower() in fields]
        for name, node in parts:
            fields[name] = self._get_template_field_value(node, self.TEMPLATE_FIELDS[name][0])
        return fields

    def _get_template_field_value(self, node, type=str):
        if isinstance(node, jinja2.nodes.List):
            values = dict(node.iter_fields())['items']
            value = [self._get_template_field_value(v, type) for v in values]
        elif type is bool:
            value = isinstance(node.value, bool) and node.value
        else:
            value = str(node.value)
        return value

    def _find_deps(self, root, body):
        deps = set()
        for part in body:
            if isinstance(part, (jinja2.nodes.Extends, jinja2.nodes.Include)):
                deps.add(os.path.join(root, part.template.value))
            elif isinstance(part, jinja2.nodes.Block):
                deps |= self._find_deps(root, part.body)
        return deps
