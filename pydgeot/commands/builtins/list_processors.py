from pydgeot.commands import register


@register(name='processors', help_msg='List available processors')
def list_processors(app):
    """
    Print available processor information.

    :param app: App instance to get processors for.
    :type app: pydgeot.app.App | None
    """
    processors = sorted(app.processors.values(), key=lambda x: x.name if x.name else x.__class__.__name)

    if len(processors) == 0:
        return

    left_align = max(14, max([len(p.name if p.name else p.__class__.__name__) for p in processors])) + 4

    for processor in processors:
        disp = processor.name if processor.name else processor.__class__.__name__
        print('{0}    {1}'.format(disp.rjust(left_align), processor.help_msg))
