import inspect

available = {}

class Processor:
    priority = 50
    def __init__(self, app):
        self.app = app
    def can_process(self, path):
        return False
    def process(self, path):
        return []
    def get_targets(self, path):
        return []
    def get_dependences(self, path):
        return []

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
