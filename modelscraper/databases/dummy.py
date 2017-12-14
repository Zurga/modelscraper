from ..workers import StoreWorker


class DummyDatabase(StoreWorker):
    """
    A dummy database class which can be used to print the results to the screen.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _handle(self, template):
        return str(template)
