import os
import shutil
from pydgeot.processors import register, Processor
from pydgeot.app.dirconfig import BaseDirConfig
from pydgeot.filesystem import Glob, create_symlink


@register(name='fallback')
class FallbackProcessor(Processor):
    """
    Copy or create a symlink for any target file over to the build directory. Only does so if no other Processor will
    process the file.
    """
    def can_process(self, path):
        return self._is_copy_path(path) or self._is_symlink_path(path)

    def negotiate_process(self, path, processors):
        # Always bow out if another processor can process the path.
        return False

    def generate(self, path):
        rel = os.path.relpath(path, self.app.source_root)
        target = os.path.join(self.app.build_root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if self._is_copy_path(path):
            shutil.copy2(path, target)
        elif self._is_symlink_path(path):
            create_symlink(path, target)
        self.app.sources.set_targets(path, [target])

    def _is_copy_path(self, path):
        config = DirConfig.get(self.app, path)
        rel = os.path.relpath(path, self.app.source_root)
        return any([glob.match_path(rel) for glob in config.copy_paths])

    def _is_symlink_path(self, path):
        config = DirConfig.get(self.app, path)
        rel = os.path.relpath(path, self.app.source_root)
        return any([glob.match_path(rel) for glob in config.symlink_paths])


class DirConfig(BaseDirConfig):
    _config_key = 'fallback'
    _default_config = {
        'copy_paths': ['**'],
        'symlink_paths': []
    }

    def __init__(self, app, path):
        """
        :type app: pydgeot.app.App
        :type path: str
        """
        self.copy_paths = None
        """:type: list[Glob] | None"""
        self.symlink_paths = None
        """:type: list[Glob] | None"""

        super().__init__(app, path)

    def _parse(self, config_path, config, parent):
        """
        :type config_path: str
        :type config: dict[str, Any]
        :type parent: DirConfig | None
        """
        config = config.get(DirConfig._config_key, {})

        for name in ('copy_paths', 'symlink_paths'):
            value = config.pop(name, None)
            if value is None:
                value = self._default_config.get(name) if parent is None else getattr(parent, name)
            elif isinstance(value, str):
                value = [value]
            value = [Glob(glob) for glob in value]
            setattr(self, name, value)
