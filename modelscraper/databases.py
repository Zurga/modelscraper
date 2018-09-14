import csv
import json
import logging
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
forbidden_characters = 'These characters {} cannot be in the name {}'
logger = logging.getLogger(__name__)


class MetaDatabaseImplementation(type):
    def __new__(meta, name, bases, class_dict):
        funcs = ['create', 'read', 'update', 'delete']
        if bases != (object, ):
            not_implemented = [func for func in funcs if func not in class_dict]
            if not_implemented:
                raise NotImplementedError(
                    implement_error.format(name, str(not_implemented)))
        return type.__new__(meta, name, bases, class_dict)


class BaseDatabaseImplementation(Process, metaclass=MetaDatabaseImplementation):
    create, read, update, delete = None, None, None, None

    def __init__(self, parent=None, table='', cache=10):
        super().__init__()
        self.in_q = parent.in_q
        self.cache = cache
        self.templates = None

    @property
    def templates(self):
        return self._templates

    @templates.setter
    def templates(self, templates):
        self._templates = templates

    def run(self):
        while True:
            template = self.in_q.get()

            if template is None:
                print('received stopping sign')
                break

            # Call to the functions in this class
            try:
                func = getattr(self, template.func, None)
                if func:
                    res = func(template, **template.kws)
                self.in_q.task_done()
            except Exception as e:
                logging.log(logging.WARNING,
                            'This template did not store correctly' +
                            str(template.objects) + e)


class BaseDatabase(object):
    forbidden_chars = []

    def __init__(self):
        self.in_q = JoinableQueue()

    def check_forbidden_chars(self, key):
        if any(c in key for c in self.forbidden_chars):
            raise Exception(forbidden_characters.format(str(forbidden_chars),
                                                        str(key)))


class MongoDB(BaseDatabase):
    '''
    A database class for MongoDB.
    The variables that can be set are:
        host
        port
    '''
    name = 'MongoDB'
    forbidden_chars = ('.', '$')

    def __init__(self, db, table='', host=None, port=None, **kwargs):
        super().__init__()
        self.client = MongoClient(host=host, port=port, connect=False)
        db = getattr(self.client, db)
        self.worker = MongoDBWorker(parent=self, database=db, **kwargs)
        self.worker.daemon = True
        self.worker.start()


class MongoDBWorker(BaseDatabaseImplementation):
    def __init__(self, database, **kwargs):
        super().__init__(**kwargs)
        self.db = database
        # TODO add connection details

    def get_collection(self, template):
        return getattr(self.db, template.table)

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
class ShellCommand(BaseDatabaseImplementation):
    def __init__(self):
        super.__init__()

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
    name = 'CSV database'

    def __init__(self, db):
        super().__init__()
        db = os.path.abspath(template.db)
        self.worker = CSVWorker(db, parent=self)
        self.worker.start()


class CSVWorker(BaseDatabaseImplementation):
    def __init__(self, db, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = {}
        self.columns = {}
        self.db = db

    def filename(self, template):
        return self.db + template.table + '.csv'

    def check_existing(self, template):
        filename = self.filename(template)
        if os.path.isfile(filename):
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
    name = 'SQlite'

    def __init__(self, db, *args, **kwargs):
        super().__init__()
        connection = sqlite3.connect(db + '.db',
                                     sqlite3.PARSE_DECLTYPES)
        sqlite3.register_adapter(dict, dictionary_adapter)
        sqlite3.register_converter('dict', dictionary_converter)
        self.worker = SqliteWorker(connection, parent=self)
        self.worker.start()


class SqliteWorker(BaseDatabaseImplementation):
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

    def __init__(self, db, new=False, **kwargs):
        super().__init__(**kwargs)
        self.template_schema = {}
        self.connections = {}
        self.db = db

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

    def check_schema(self, template):
        # Is there a schema of the template we are storing
        if not self.template_schema.get(template.name):
            schema = self.create_schema(template)
            with self.db as connection:
                for line in schema:
                    connection.execute(line)
            self.template_schema[template.name] = schema

    def create(self, template, *args, **kwargs):
        self.check_schema(template)
        query = "INSERT INTO {table} VALUES (?, ?);"
        with self.db as con:
            # By inserting NULL into the id column SQLITE will create the id.
            values = list(zip([None] * len(template.urls), template.urls))
            con.executemany(query.format(table=template.table), values)

            # We select all the ids that were inserted to create the attrs
            urls_ids = dict(self.urls_ids(template))

            for attr in template.attrs.keys():
                table_name = '_'.join((template.table, attr))

                for obj, url in zip(template.objects, template.urls):
                    db_id = urls_ids[url]
                    for value in obj[attr]:
                        con.execute(query.format(table=table_name), (db_id, value))

    def urls_ids(self, template):
        id_query = """ SELECT url, id FROM {table} WHERE url =
        ?""".format(table=template.table)
        urls_ids = []
        with self.db as con:
            for url in template.urls:
                urls_ids.extend(con.execute(id_query, (url,)).fetchall())
        return urls_ids

    def update(self, template, *args, **kwargs):
        self.check_schema(template)
        query = "UPDATE {} SET {} = ? WHERE id = ?"
        for (url, i) in self.urls_ids(template):
            obj_idx = template.urls.index(url)
            obj = template.objects[obj_idx]

            for attr in obj.keys():
                table_name = '_'.join((template.name, attr))
                for value in obj[attr]:
                    con.execute(query.format(table_name, attr), (value, i))

    def delete(self, template, *args, **kwargs):
        self.check_schema(template)
        urls_ids = dict(self.urls_ids(template))
        delete_query = 'DELETE FROM {table} WHERE id = ?'
        with self.connect(template) as con:
            for url in template.urls:
                db_id = urls_ids[url]
                con.execute(delete_query.format(table=template.table),
                            (db_id,))

    #TODO fix this method
    def read(self, template, *args, **kwargs):
        pass
