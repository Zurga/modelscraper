import csv
import json
import os
import subprocess
import sqlite3
import time
from datetime import datetime
from multiprocessing import Process, JoinableQueue
from collections import defaultdict

from pymongo import MongoClient, UpdateMany
from pymongo.collection import Collection

from .helpers import add_other_doc

unsupported = 'The "{}" function is not supported by the {} adapter'
implement_error = "These methods are not implemented in the subclass {}: {}"

class MetaDatabase(type):
    def __new__(meta, name, bases, class_dict):
        funcs = ['create', 'read', 'update', 'delete']
        if bases != (object, ):
            not_implemented = [func for func in funcs if func not in class_dict]
            if not_implemented:
                raise NotImplementedError(
                    implement_error.format(name, str(not_implemented)))
        return type.__new__(meta, name, bases, class_dict)

class BaseDatabase(Process, metaclass=MetaDatabase):
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
        self.index = {}
        self.columns = {}

    def filename(self, template):
        if '_attr:' in template.table:
            table = template.objects[0][template.table.replace('_attr:', '')]
        else:
            table = template.table
        return os.path.abspath('{}/{}.csv'.format(template.db, table))

    def check_existing(self, template):
        filename = self.filename(template)
        if os.path.isfile(os.path.abspath(filename)):
            self.index[filename] = self.create_index(filename)

    def create_index(self, filename):
        index = {}
        with open(filename) as fle:
            reader = csv.DictReader(fle)
            for i, row in enumerate(reader):
                index[row['_url']] = i
        return index

    def create(self, template, **kwargs):
        filename = self.filename(template)
        if not self.index.get('filename', False):
            self.index[filename] = self.create_index(filename)
        try:
            with open(filename, 'a') as fle:
                writer = csv.DictWriter(fle,
                                        fieldnames=template.objects[0].keys())
                writer.writeheader()
                writer.writerows(template.objects)
                index = dict(enumerate((o['_url'] for o in template.objects)))
                self.index[filename] = {**self.index[filename], **index}
        except Exception as E:
            print('CSVDatabse', E)
            return False
        return True

    def read(self, template):
        pass

    def update(self, template):
        filename = self.filename(template)
        if not self.index.get('filename', False):
            self.index[filename] = self.create_index(filename)
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


def dictionary_adapter(dictionary):
    return json.dumps(dictionary)

def dictionary_converter(s):
    return json.loads(s)


class Sqlite(BaseDatabase):
    ''' A database implementation for Sqlite3.'''

    template_table = '''CREATE TABLE IF NOT EXISTS {table}
        (id INTEGER PRIMARY KEY ASC, url TEXT);'''

    template_index = 'CREATE INDEX IF NOT EXISTS urlindex ON {table} (url)'

    attr_table = '''CREATE TABLE IF NOT EXISTS {table}_{attr}
        (id INTEGER, value {type})'''

    attr_trigger = '''
        CREATE TRIGGER IF NOT EXISTS delete_{table}
        AFTER DELETE ON {table} BEGIN DELETE FROM {table}_{attr}
        WHERE OLD.id = {table}_{attr}.id; END;
        '''

    def __init__(self, new=False, **kwargs):
        super().__init__(**kwargs)
        self.template_schema = {}
        self.connections = {}

    def create_schema(self, template):
        attrs = template.attrs
        # TODO set correct types for the attrs
        yield self.template_table.format(table=template.table)
        yield self.template_index.format(table=template.table)
        yield from self.attr_schema(template)

    def attr_schema(self, template):
        '''
        Creates the table definitions for each attribute of a
        template.
        '''
        table = template.table
        for attr in template.attrs:
            if attr.type:
                value_type = attr.type
            else:
                value_type = 'TEXT'
            yield self.attr_table.format(table=table, attr=attr.name,
                                         type=value_type)
            yield self.attr_trigger.format(table=table, attr=attr.name,
                                           type=value_type)

    def connect(self, template):
        connection = self.connections.get(template.db, False)
        if not connection:
            connection = sqlite3.connect(template.db + '.db',
                                         sqlite3.PARSE_DECLTYPES)
            sqlite3.register_adapter(dict, dictionary_adapter)
            sqlite3.register_converter('dict', dictionary_converter)
            self.connections[template.db] = connection

        # Is there a schema of the template we are storing
        if not self.template_schema.get(template.name):
            schema = self.create_schema(template)
            with connection:
                for line in schema:
                    print(line)
                    connection.execute(line)
            self.template_schema[template.name] = schema

        return connection

    def create(self, template, *args, **kwargs):
        to_insert = len(template.objects)

        query = "INSERT INTO {table} VALUES (?, ?);"
        with self.connect(template) as con:
            # By inserting NULL into the id column SQLITE will create the id.
            values = list(zip([None] * len(template.urls), template.urls))
            con.executemany(query.format(table=template.table), values)

            # We select all the ids that were inserted to create the attrs
            urls_ids = dict(self.urls_ids(template))

            for attr in template.objects[0].keys():
                table_name = '_'.join((template.table, attr))

                for obj, url in zip(template.objects, template.urls):
                    db_id = urls_ids[url]
                    for value in obj[attr]:
                        con.execute(query.format(table=table_name), (db_id, value))

    def urls_ids(self, template):
        id_query = """ SELECT url, id FROM {table} WHERE url =
        ?""".format(table=template.table)
        urls_ids = []
        with self.connect(template) as con:
            for url in template.urls:
                print('getting', url)
                urls_ids.extend(con.execute(id_query, (url,)).fetchall())
        return urls_ids

    def update(self, template, *args, **kwargs):
        query = "UPDATE {} SET {} = ? WHERE id = ?"
        for (url, i) in self.urls_ids(template):
            obj_idx = template.urls.index(url)
            obj = template.objects[obj_idx]

            for attr in obj.keys():
                table_name = '_'.join((template.name, attr))
                for value in obj[attr]:
                    con.execute(query.format(table_name, attr), (value, i))

    def delete(self, template, *args, **kwargs):
        urls_ids = dict(self.urls_ids(template))
        delete_query = 'DELETE FROM {table} WHERE id = ?'
        with self.connect(template) as con:
            for url in template.urls:
                db_id = urls_ids[url]
                con.execute(delete_query.format(table=template.table),
                            (db_id,))

    def read(self, template, *args, **kwargs):
        pass
