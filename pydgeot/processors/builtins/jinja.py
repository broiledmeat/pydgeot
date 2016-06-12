import os
from pydgeot.processors import register, Processor


try:
    # noinspection PyUnresolvedReferences
    import jinja2
    # noinspection PyUnresolvedReferences
    import jinja2.meta
    # noinspection PyUnresolvedReferences
    import jinja2.nodes
    # noinspection PyUnresolvedReferences
    from jinja2.ext import Extension
except ImportError:
    pass
else:
    class SetContextExtension(Extension):
        tags = {'setcontext'}

        def __init__(self, environment):
            super().__init__(environment)
            self.processor = None
            """:type: JinjaProcessor"""

        def parse(self, parser):
            lineno = next(parser.stream).lineno
            name = parser.stream.expect('name')

            if parser.stream.current.type == 'assign':
                next(parser.stream)
                value = parser.parse_expression()
                self.processor.add_set_context(name.value, value.value)
                name_node = jinja2.nodes.Name(name.value, 'store', lineno=lineno)
                value_node = jinja2.nodes.Const(value.value, lineno=lineno)
                return jinja2.nodes.Assign(name_node, value_node, lineno=lineno)

            return []


    @register()
    class JinjaProcessor(Processor):
        """
        Compile a Jinja (http://jinja.pocoo.org/) template source file in to the build directory.

        Context variables can be set using the 'setcontext' tag. This also works as Jinja's built in 'set' tag.
        File paths that have set context variables can be retrieved with 'getcontexts("name", "value")'.
        To mark a file as only being used as a template (no file will be generated for it,) use Jinja's built in 'set'
        to set the 'template_only' variable to True.
        """
        name = 'Jinja'

        def __init__(self, app):
            super().__init__(app)

            self._env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self.app.source_root),
                extensions=[SetContextExtension])

            # Prepare template extensions
            for extension in self._env.extensions.values():
                extension.processor = self

            # Add template functions
            def get_contexts(name, value):
                context_dicts = []
                results = self.app.contexts.get_contexts(name, value)
                for result in results:
                    context_dict = {}
                    source = self.app.sources.get_source(result.source)
                    if source is not None:
                        targets = self.app.sources.get_targets(result.source)
                        if len(targets) == 1:
                            context_dict['url'] = '/' + self.app.relative_path(list(targets)[0].path)
                        context_dict['urls'] = ['/' + self.app.relative_path(target.path) for target in targets]
                        context_dict['size'] = source.size
                        context_dict['modified'] = source.modified
                    for context_var in self.app.contexts.get_contexts(source=result.source):
                        context_dict[context_var.name] = context_var.value
                    context_dicts.append(context_dict)
                return context_dicts
            self._env.globals['getcontexts'] = get_contexts

            self._generate = {}
            self._set_contexts = {}
            self.current_path = None

        def can_process(self, path):
            return path.endswith('.html')

        def prepare(self, path):
            # TODO: Allow extension changing
            if path not in self._generate:
                self.current_path = path
                self._set_contexts = {}

                target = self.target_path(path)
                with open(path) as fh:
                    ast = self._env.parse(fh.read())

                self.app.sources.set_targets(path, [target])
                self.app.sources.set_dependencies(path,
                                                  [self.app.source_path(t)
                                                   for t in jinja2.meta.find_referenced_templates(ast)])

                consts = self._get_const_vars(ast)
                template_only = consts.get('template_only', False)

                # Clear old context dependencies and add new ones (populated from get_contexts)
                self.app.contexts.clear_dependencies(path)
                for name, value in self._get_context_requests(ast):
                    self.app.contexts.add_dependency(path, name, value)

                # Clear old contexts and add new ones (populated from SetContextExtension when the template is parsed)
                self.app.contexts.remove_context(path)
                for name, value in self._set_contexts.items():
                    self.app.contexts.set_context(path, name, value)

                # Add this to the list of paths to be generated if it's not template only
                if not template_only:
                    self._generate[path] = (target, ast)

        def generate(self, path):
            if path in self._generate:
                target, ast = self._generate[path]
                # TODO: Get template from ast returned above
                with open(path) as fh:
                    template = self._env.from_string(fh.read())

                context_dict = {}
                source = self.app.sources.get_source(path)
                if source is not None:
                    targets = self.app.sources.get_targets(path)
                    if len(targets) == 1:
                        context_dict['url'] = '/' + self.app.relative_path(list(targets)[0].path)
                    context_dict['urls'] = ['/' + self.app.relative_path(target.path) for target in targets]
                    context_dict['size'] = source.size
                    context_dict['modified'] = source.modified

                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, 'w', encoding='utf-8') as fh:
                    fh.write(template.render(**context_dict))
                del self._generate[path]

        def target_path(self, path):
            return self.app.target_path(path)

        def add_set_context(self, name, value):
            self._set_contexts[name] = value

        @staticmethod
        def _get_const_vars(ast):
            const_vars = {}
            for node in ast.find_all((jinja2.nodes.Assign, )):
                if isinstance(node.target, jinja2.nodes.Name) and isinstance(node.node, jinja2.nodes.Const):
                    # noinspection PyUnresolvedReferences
                    const_vars[node.target.name] = node.node.value
            return const_vars

        @staticmethod
        def _get_context_requests(ast):
            context_requests = []
            for node in ast.find_all(jinja2.nodes.Call, ):
                if isinstance(node.node, jinja2.nodes.Name) and len(node.args) == 2 and \
                        isinstance(node.args[0], jinja2.nodes.Const) and isinstance(node.args[1], jinja2.nodes.Const):
                    context_requests.append((node.args[0].value, node.args[1].value))
            return context_requests
