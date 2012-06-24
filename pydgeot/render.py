"""
Renderer
Method for getting a files rendered contents.
"""

from collections import namedtuple
RenderResult = namedtuple('RenderResult', ['content', 'handler'])

def render(source_root, source_path):
    """
    Render a file, using a handler if available.

    Args:
        source_root (str): Sources files root directory.
        source_path (str): Source file to render.
    Raises:
        IOError: If source_root is not a directory, or source_path is not a file.
    Returns:
        str: Rendered content.
    """
    import os
    from .handlers import get_handler

    if not os.path.isdir(source_root):
        raise IOError('Source root is not a directory', source_root)
    if not os.path.isfile(source_path):
        raise IOError('Source path is not a file', source_path)

    handler = get_handler(os.path.relpath(source_path, source_root))
    if handler is not None:
        content = handler.render(source_root, source_path)
    else:
        content = open(source_path, 'rb').read()

    return RenderResult(content, handler)
