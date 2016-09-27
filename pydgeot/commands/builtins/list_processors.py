from pydgeot.commands import register


@register(name='processors', help_msg='List available processors')
def list_processors(app):
    """
    Print available processor information.

    :param app: App instance to get processors for.
    :type app: pydgeot.app.App | None
    """
    processors = sorted(app.processors.values(), key=lambda p: p.name)

    if len(processors) == 0:
        return

    left_align = max(14, max([len(p.name) for p in processors]))

    for processor in processors:
        print('{0}    {1}'.format(processor.name.rjust(left_align), processor.help_msg))
