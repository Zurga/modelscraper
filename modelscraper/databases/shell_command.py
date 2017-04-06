import subprocess
from ..workers import StoreWorker


class ShellCommand(StoreWorker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _store(self, item):
        for objct in item.objects:
            arguments = item.kws['command'].format(**objct).split()

            print(arguments)
            subprocess.Popen(arguments)
