import os
import inspect

available = {}

class Processor:
    priority = 50
    def __init__(self, app):
        self.app = app
    def can_process(self, path):
        return False
    def process_create(self, path):
        return self.process_update(path)
    def process_update(self, path):
        return []
    def process_delete(self, path):
        for target in self.app.filemap.get_targets(path):
            if os.path.isfile(target):
                try:
                    os.remove(target)
                except PermissionError:
                    pass
    def get_dependencies(self, path):
        return []
    def process_changes_complete(self):
        pass
    def wipe(self):
        pass

class register:
    def __init__(self):
        mod_name = inspect.getmodule(inspect.stack()[1][0]).__name__
        if '.' in mod_name:
            mod_name = mod_name[mod_name.rindex('.') + 1:]
        self.module_name = mod_name

    def __call__(self, cls):
        global available
        if self.module_name not in available:
            available[self.module_name] = []
        available[self.module_name].append(cls)
