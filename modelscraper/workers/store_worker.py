from multiprocessing import Process
from threading import Thread


unsupported = 'The "{}" function is not supported by the {} adapter'


class StoreWorker(Process):
    def __init__(self, in_q=None, cache=10):
        super(StoreWorker, self).__init__()
        self.in_q = in_q
        self.cache = cache

    def run(self):
        while True:
            template = self.in_q.get()

            if template is None:
                break

            # Set up the environment before storing the objects.
            self.res = self._handle(template)
            '''
            if template.objects:
                # Call to the functions in this class
                func = getattr(self, template.func, None)
                if func:
                    result = func(template.objects, **template.kws)

                    if not result:
                        print('Failed with template', template.name)
                        print(template)
            '''
        print('stopping store')

    def create(self, objects, *args, **kwargs):
        '''
        Writes a list of objects to the database specified in the template.
        This wraps around functions of the database wrappers.
        '''
        assert getattr(self, '_create', None), \
            unsupported.format("create", self.__name__)
        return self._create(objects, *args, **kwargs)

    def read(self, *args, **kwargs):
        '''
        Read an entry from the database.
        '''
        assert getattr(self, '_read', None), \
            unsupported.format("read", self.__name__)
        return self._read(*args, **kwargs)

    def update(self, *args, **kwargs):
        '''
        Performs an update to the database based on the key specified.
        If no key is specified, the url of object is used.
        By default creates an object in the database, if none exists.
        '''
        assert getattr(self, '_update', None), \
            unsupported.format("update", self.__name__)
        return self._update(*args, **kwargs)

    def delete(self, *args, **kwargs):
        '''
        Deletes an entry from the database.
        Not implemented yet in any of the DatabaseAdapters.
        '''
        assert getattr(self, '_delete', None), \
            unsupported.format("delete", self.__name__)
        return self._delete(*args, **kwargs)
