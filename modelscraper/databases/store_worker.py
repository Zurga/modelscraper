from multiprocessing import Process, JoinableQueue


unsupported = 'The "{}" function is not supported by the {} adapter'


class StoreWorker(Process):
    def __init__(self, cache=10):
        super(StoreWorker, self).__init__()
        self.store_q = JoinableQueue()
        self.cache = cache

    def run(self):
        while True:
            template = self.store_q.get()

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
        raise NotImplementedError

    def read(self, *args, **kwargs):
        '''
        Read an entry from the database.
        '''
        raise NotImplementedError

    def update(self, *args, **kwargs):
        '''
        Performs an update to the database based on the key specified.
        If no key is specified, the url of object is used.
        By default creates an object in the database, if none exists.
        '''
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        '''
        Deletes an entry from the database.
        Not implemented yet in any of the DatabaseAdapters.
        '''
        raise NotImplementedError
