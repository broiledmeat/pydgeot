from pydgeot.processors import register, Processor

@register()
class CopyFallbackProcessor(Processor):
    priority = 0