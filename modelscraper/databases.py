from multiprocessing import Process, JoinableQueue
import subprocess
from datetime import datetime
import time
import csv
import os

from pymongo import MongoClient, UpdateMany
from pymongo.collection import Collection

from .helpers import add_other_doc

unsupported = 'The "{}" function is not supported by the {} adapter'
implement_error = "These methods are not implemented in the subclass {}: {}"

class ValidateDatabase(type):
    def __new__(meta, name, bases, class_dict):
        funcs = ['create', 'read', 'update', 'delete']
        if bases != (object, ):
            not_implemented = [func for func in funcs if func not in class_dict]
            if not_implemented:
                raise NotImplementedError(
                    implement_error.format(name, str(not_implemented)))
        return type.__new__(meta, name, bases, class_dict)

class BaseDatabase(Process, metaclass=ValidateDatabase):
    create, read, update, delete = None, None, None, None

    def __init__(self, cache=10):
        super().__init__()
        self.in_q = JoinableQueue()
        self.result_q = JoinableQueue()
        self.cache = cache

    def run(self):
        while True:
            template = self.in_q.get()

            if template is None:
                break

            # Call to the functions in this class
            func = getattr(self, template.func, None)
            if func:
                res = func(template, **template.kws)
            self.result_q.put(res)
            self.in_q.task_done()
        print('stopping store')

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

    def get_collection(self, template):
        return getattr(getattr(self.client, template.db), template.table)

    #!@add_other_doc(Collection.insert_many)
    def create(self, template, *args, **kwargs):
        coll = self.get_collection(template)
        return coll.insert_many(template.objects, *args, **kwargs)

    #!@add_other_doc(Collection.bulk_write)
    def update(self, template, key='', method='$set', upsert=True, date=False):
        coll = self.get_collection(template)
        queries = self._create_queries(key, template.objects)
        if date:
            date = datetime.datetime.fromtimestamp(time.time())
            objects = ({date.isoformat(): obj}
                       for obj in objects)

        # insert all the objects in the database
        db_requests = [UpdateMany(query, {method: obj}, upsert=upsert)
                       for obj, query in zip(objects, queries)]
        return coll.bulk_write(db_requests)

    #!@add_other_doc(Collection.find)
    def read(self, template=None, query={}, **kwargs):
        coll = self.get_collection(template)

        for db_object in coll.find(query, **kwargs):
            objct = template()
            objct.attrs_from_dict(db_object)
            yield objct

    def delete(self):
        pass

    def _create_queries(self, key, objects):
        if not key:
            return ({'url': obj['_url']} for obj in objects)
        else:
            return ({key: obj[key][0]} for obj in objects)


# TODO fix this to the new spec
class ShellCommand(BaseDatabase):
    def _handle(self, item):
        for objct in item.objects:
            arguments = item.kws['command'].format(**objct).split()
            subprocess.Popen(arguments)

    def create(self, objects):
        pass

    def read(self, template):
        pass

    def update(self, template):
        pass

    def delete(self, template):
        pass

class CSV(BaseDatabase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def filename(self, template):
        if '_attr:' in template.table:
            table = template.objects[0][template.table.replace('_attr:', '')]
        else:
            table = template.table
        return '{}/{}.csv'.format(template.db, table)

    def create(self, template, **kwargs):
        filename = self.filename(template)
        try:
            with open(filename, 'w') as fle:
                writer = csv.DictWriter(fle,
                                        fieldnames=template.objects[0].keys())
                writer.writeheader()
                writer.writerows(template.objects)
        except Exception as E:
            print('CSVDatabse', E)
            return False
        return True

    def read(self, template):
        pass

    def update(self, template):
        filename = self.filename(template)
        try:
            with open(filename, 'a') as fle:
                writer = csv.DictWriter(fle,
                                        fieldnames=template.objects[0].keys())
                writer.writerows(template.objects)
        except Exception as E:
            print('CSVDatabse', E)
            return False
        return True
        pass

    def delete(self, template):
        pass


