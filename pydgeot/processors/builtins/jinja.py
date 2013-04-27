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
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.app.source_root))
        self.changes = {}

    def can_process(self, path):
        return path.endswith('.html')

    def prepare(self, path):
        target = self.app.target_path(path)
        body = self.env.parse(open(path).read()).body

        self.changes[path] = (target, body)
        self.app.sources.set_targets(path, [target])
        self.app.sources.set_dependencies(path, self._find_deps(body))

    def generate(self, path):
        if path in self.changes:
            target, body = self.changes[path]
            fields = self._get_template_fields(body)
            if 'template_only' not in fields or fields['template_only'] != 'true':
                # TODO: Get template from body
                template = self.env.from_string(path)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                f = open(target, 'w', encoding='utf-8')
                f.write(template.render())
                f.close()
            del self.changes[path]

    def _get_template_fields(self, body):
        fields = dict((name, val[1]) for name, val in self.TEMPLATE_FIELDS.items())
        parts = [(p.target.name.lower(), p.node) for p in body
                 if isinstance(p, jinja2.nodes.Assign) and p.target.name.lower() in fields]
        for name, node in parts:
            fields[name] = self._get_template_field_value(node, self.TEMPLATE_FIELDS[name][0])
        return fields

    def _get_template_field_value(self, node, value_type=str):
        if isinstance(node, jinja2.nodes.List):
            values = dict(node.iter_fields())['items']
            value = [self._get_template_field_value(v, value_type) for v in values]
        elif value_type is bool:
            value = isinstance(node.value, bool) and node.value
        else:
            value = str(node.value)
        return value

    def _find_deps(self, body):
        deps = set()
        for part in body:
            if isinstance(part, (jinja2.nodes.Extends, jinja2.nodes.Include)):
                deps.add(os.path.join(self.app.source_root, part.template.value))
            elif isinstance(part, jinja2.nodes.Block):
                deps |= self._find_deps(part.body)
        return deps
