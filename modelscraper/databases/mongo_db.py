from ..workers import StoreWorker
from pymongo import MongoClient, UpdateMany
from datetime import datetime
import time


class MongoDB(StoreWorker):
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

    def _create(self, objects, *args, **kwargs):
        # TODO link from the StoreWorker documentation
        # TODO link to the pymongo documentation
        return self.coll.insert_many([obj.to_dict() for obj in objects],
                                     *args, **kwargs)

    def _update(self, objects, key='', method='$set', upsert=True,
                date=False):
        # TODO link from the StoreWorker documentation
        # TODO add pymongo documentation link.
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
            return self.coll.bulk_write(db_requests)
        return False

    def _read(self, template=None, url='', **kwargs):
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
