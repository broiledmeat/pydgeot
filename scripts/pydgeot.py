"""Pydgeot

Usage:
  pydgeot commands [-a PATH]
  pydgeot <command> [-a PATH] [<args>...]
  pydgeot -h | --help
  pydgeot --version

Options:
  -h, --help            Show this screen.
  --version             Show version.
  -a PATH, --app PATH   App directory.
"""

if __name__ == '__main__':
    import sys
    from docopt import docopt

    sys.path = sys.path[1:]
    from pydgeot.app import App

    args = docopt(__doc__, version='Pydgeot 0.2')
    app = App(args['--app'])

    if args['commands']:
        args['<command>'] = 'commands'

    app.command(args['<command>'], *args['<args>'])