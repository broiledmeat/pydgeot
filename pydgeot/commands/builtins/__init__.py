from pydgeot.commands import register
from pydgeot.commands.builtins.create import create
from pydgeot.commands.builtins.build import build
from pydgeot.commands.builtins.watch import watch
from pydgeot.commands.builtins.list_commands import list_commands

register(name='commands', help='List available commands')(list_commands)
register(help_args='PATH', help='Generate a new Pydgeot app directory')(create)
register(help_args='[wipe]', help='Build static content')(build)
register(help_args='[wipe]', help='Continously build static content')(watch)
