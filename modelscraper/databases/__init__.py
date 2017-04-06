from .mongo_db import MongoDB
from .shell_command import ShellCommand

_threads = {'mongo_db': MongoDB,
            'shell_command': ShellCommand,
            }
