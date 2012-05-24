"""
Command line renderer
Method and command line access for getting a files rendered contents.
"""
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
        return handler.render(source_root, source_path)
    return open(source_path).read()

    return template.render()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('source_root', metavar='SOURCE_ROOT')
    parser.add_argument('source_file', metavar='SOURCE_FILE')
    args = vars(parser.parse_args())

    print(render(args['source_root'], args['source_file']))
