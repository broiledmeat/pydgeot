import os
import shutil
from pydgeot.processors import register, Processor


@register()
class CopyFallbackProcessor(Processor):
    priority = 0

    def can_process(self, path):
        return True

    def generate(self, path):
        rel = os.path.relpath(path, self.app.source_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(path, target)
        self.app.sources.set_targets(path, [target])
