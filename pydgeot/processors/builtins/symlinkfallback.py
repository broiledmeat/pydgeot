import os
from pydgeot.processors import register, Processor
from pydgeot.utils.filesystem import create_symlink


@register()
class SymlinkFallbackProcessor(Processor):
    """
    Creates a symlink for any target file in to the build directory. Run with lowest priority.
    """
    name = 'Symlink'
    priority = 0

    def can_process(self, path):
        return True

    def generate(self, path):
        rel = os.path.relpath(path, self.app.source_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        create_symlink(path, target)
        self.app.sources.set_targets(path, [target])
