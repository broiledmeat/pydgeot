import os
import shutil
from pydgeot.processors import register, Processor

@register()
class CopyFallbackProcessor(Processor):
    priority = 0

    def can_process(self, path):
        return True

    def process(self, path):
        rel = os.path.relpath(path, self.app.content_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(path, target)
        return [target]