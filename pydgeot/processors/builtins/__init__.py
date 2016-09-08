def register_builtins():
    from .copyfallback import CopyFallbackProcessor
    from .symlinkfallback import SymlinkFallbackProcessor
    from .jinja import JinjaProcessor
    from .lesscss import LessCSSProcessor
