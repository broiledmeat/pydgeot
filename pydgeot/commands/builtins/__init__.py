from pydgeot.commands import register
from pydgeot.commands.builtins.create import create
from pydgeot.commands.builtins.build import build
from pydgeot.commands.builtins.watch import watch
from pydgeot.commands.builtins.reset import reset
from pydgeot.commands.builtins.clean import clean
from pydgeot.commands.builtins.list_commands import list_commands

register(help_args='PATH', help_msg='Generate a new Pydgeot app directory')(create)
register(help_msg='Build static content')(build)
register(help_msg='Continuously build static content')(watch)
register(help_msg='Quickly clean all built content')(reset)
register(help_args='PATH [PATH]...', help_msg='Clean built content for specific directories')(clean)
register(name='commands', help_msg='List available commands')(list_commands)
