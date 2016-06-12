import pkgutil


# Import all modules in this package at runtime so processors are registered.
__all__ = []
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    __all__.append(module_name)
    loader.find_module(module_name).load_module(module_name)
