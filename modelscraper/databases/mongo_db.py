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

    def __init__(self, in_q=None):
        super(MongoDB, self).__init__(in_q=in_q)
        # TODO add connection details
        self.client = MongoClient()

    def _handle(self, template):
        self.db = self.client[template.db]
        self.coll = self.db[template.table]

        if template.objects:
            # Call to the functions in this class
            func = getattr(self, template.func, None)
            if func:
                return func(template.objects, **template.kws)
        return False

    def _create(self, objects, *args, **kwargs):
        # TODO link from the StoreWorker documentation
        # TODO link to the pymongo documentation
        return self.coll.insert_many([obj.to_dict() for obj in objects],
                                     *args, **kwargs)

    def _update(self, objects, key='', method='$set', upsert=True,
                date=False, **kwargs):
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

            return self.coll.bulk_write(db_requests, **kwargs)
        return False

    def _read(self, uri, objct, **kwargs):
        db_object = self.coll.find_one({'url': uri}, **kwargs)
        if db_object:
            new_objct = objct.__class__()
            new_objct.attrs = objct.attrs_from_dict(db_object)
            return new_objct
        return False

    def _create_queries(self, key, objects):
        if not key:
            return ({'url': obj.url} for obj in objects)
        else:
            return ({key: getattr(key, obj, '')} for obj in objects)
