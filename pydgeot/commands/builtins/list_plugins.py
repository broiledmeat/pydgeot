from pydgeot.commands import register


@register(name='plugins', help_msg='List available plugins')
def list_plugins(app):
    """
    Print available plugin information.

    :param app: App instance to get plugins for.
    :type app: pydgeot.app.App | None
    """
    import sys
    import os
    import ast
    import pkgutil
    import pydgeot

    plugins = {}

    plugin_paths = [os.path.join(path, 'plugins') for path in pydgeot.__path__]
    for finder, name, _ in pkgutil.iter_modules(plugin_paths):
        plugin_path = finder.find_module(name).get_filename()
        tree = ast.parse(open(plugin_path).read())
        help_nodes = [node
                      for node in tree.body
                      if (isinstance(node, ast.Assign) and
                          len(node.targets) > 0 and
                          node.targets[0].id == '__help_msg__')]

        plugins[name] = help_nodes[0].value.s if len(help_nodes) > 0 else ''

    if len(plugins) == 0:
        return

    left_align = max(14, max([len(key) + 1 for key in plugins.keys()]))

    for name in sorted(plugins):
        disp = ('*' if '{}.{}'.format(app.plugins_package_name, name) in sys.modules else ' ') + name
        print('{}    {}'.format(disp.rjust(left_align), plugins[name]))
