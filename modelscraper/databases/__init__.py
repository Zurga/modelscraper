from .mongo_db import MongoDB
from .shell_command import ShellCommand
from .dummy import DummyDatabase

_threads = {'mongo_db': MongoDB,
            'shell_command': ShellCommand,
            'dummy': DummyDatabase,
            }
