def register_builtins():
    from .. import register
    from .fallback import FallbackProcessor

    register()(FallbackProcessor)
