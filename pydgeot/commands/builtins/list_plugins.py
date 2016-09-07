from pydgeot.commands import register


@register(name='plugins', help_msg='List available plugins')
def list_plugins(app):
    """
    Print available plugin information.

    :param app: App instance to get plugins for.
    :type app: pydgeot.app.App | None
    """
    import os
    import ast
    import pkgutil
    import pydgeot

    plugins = {}

    plugin_paths = [os.path.join(path, 'plugins') for path in pydgeot.__path__]
    for finder, name, _ in pkgutil.iter_modules(plugin_paths):
        plugin_path = finder.find_module(name).get_filename()
        tree = ast.parse(open(plugin_path).read())

        plugins[name] = (_get_node_value(tree.body, '__version__'),
                         _get_node_value(tree.body, '__help_msg__'))

    if len(plugins) == 0:
        return

    name_align = max(14, max([len(key) + 1 for key in plugins.keys()]))
    version_align = max([len(version) for version, _ in plugins.values()])

    for name in sorted(plugins):
        version, help_msg = plugins[name]
        print('{} {}    {}'.format(name.rjust(name_align), version.rjust(version_align), help_msg).rstrip())


def _get_node_value(body, name):
    """
    :param body: list[ast.AST]
    :param name: str
    :rtype: str
    """
    import ast

    nodes = [node for node in body
             if (isinstance(node, ast.Assign) and
                 len(node.targets) > 0 and
                 node.targets[0].id == name)]

    if len(nodes) > 0:
        if isinstance(nodes[0].value, ast.Num):
            return str(nodes[0].value.n)
        elif isinstance(nodes[0].value, ast.Str):
            return nodes[0].value.s

    return ''
