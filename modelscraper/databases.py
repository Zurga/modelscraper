from multiprocessing import Process, JoinableQueue
import subprocess
from datetime import datetime
import time

from pymongo import MongoClient, UpdateMany
from pymongo.collection import Collection

from .helpers import add_other_doc

unsupported = 'The "{}" function is not supported by the {} adapter'


class BaseDatabase(Process):
    def __init__(self, cache=10):
        super().__init__()
        self.store_q = JoinableQueue()
        self.cache = cache

    def run(self):
        while True:
            template = self.store_q.get()

            if template is None:
                break

            # Set up the environment before storing the objects.
            self.res = self._handle(template)
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


class MongoDB(BaseDatabase):
    '''
    A thread thread that will communicate with a single MongoDB instance.
    Look in the pymongo docs for possible functions to storing.
    '''
    name = 'mongo_db'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # TODO add connection details
        self.client = MongoClient(connect=False)

    def _handle(self, template):
        self.db = self.client[template.db]
        self.coll = self.db[template.table]

        if template.objects:
            # Call to the functions in this class
            func = getattr(self, template.func, None)
            if func:
                return func(template.objects, **template.kws)
        else:
            print('No objects in', template.name)
        return False

    #!@add_other_doc(Collection.insert_many)
    def create(self, objects, *args, **kwargs):
        return self.coll.insert_many([obj.to_dict() for obj in objects],
                                     *args, **kwargs)

    #!@add_other_doc(Collection.bulk_write)
    def update(self, objects, key='', method='$set', upsert=True,
                date=False):
        if objects:
            queries = self._create_queries(key, objects)
            if date:
                date = datetime.datetime.fromtimestamp(time.time())
                objects = ({date.isoformat(): obj.to_dict()}
                           for obj in objects)

            # insert all the objects in the database
            db_requests = [UpdateMany(query, {method: obj.to_dict()},
                                      upsert=upsert) for obj, query in
                           zip(objects, queries)]
            print(db_requests)
            return self.coll.bulk_write(db_requests)
        return False

    #!@add_other_doc(Collection.find)
    def read(self, template=None, url='', **kwargs):
        self.db = self.client[template.db]
        self.coll = self.db[template.table]
        if url:
            db_objects = self.coll.find({'url': url}, **kwargs)
        else:
            db_objects = self.coll.find(**kwargs)

        for db_object in db_objects:
            objct = template()
            objct.attrs_from_dict(db_object)
            yield objct

    def _create_queries(self, key, objects):
        if not key:
            return ({'url': obj.url} for obj in objects)
        else:
            return ({key: obj.attrs[key].value[0]} for obj in objects)


class Dummy(BaseDatabase):
    """
    A dummy database class which can be used to print the results to the screen.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _handle(self, template):
        for ob in template.objects:
            print(ob.name, end='')
            for attr in ob.attrs:
                print('\n\t', attr.name, attr.value)


class ShellCommand(BaseDatabase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _handle(self, item):
        for objct in item.objects:
            arguments = item.kws['command'].format(**objct).split()
            subprocess.Popen(arguments)
