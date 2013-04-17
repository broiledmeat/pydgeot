import os
from pydgeot.processors import register, Processor
from pydgeot.utils.filesystem import create_symlink


@register()
class SymlinkFallbackProcessor(Processor):
    priority = 0

    def can_process(self, path):
        return True

    def process_update(self, path):
        rel = os.path.relpath(path, self.app.source_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        create_symlink(path, target)
        return [target]
