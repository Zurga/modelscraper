import csv
import json
import logging
import os
import pprint
import subprocess
import sqlite3
import time
from datetime import datetime
from multiprocessing import Process, JoinableQueue
from collections import defaultdict

from pymongo import MongoClient, UpdateMany
from pymongo.collection import Collection

from .helpers import add_other_doc

pp = pprint.PrettyPrinter(indent=4)


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

    def __init__(self, parent=None, database=None, table='', cache=10):
        super().__init__()
        self.parent = parent
        self.db = database
        self.table = table
        self.in_q = parent.in_q
        self.parent = parent
        self.cache = cache
        self.templates = None

    def run(self):
        while True:
            item = self.in_q.get()

            if item is None:
                print('received stopping sign')
                break
            template, objects, urls = item

            # Call to the functions in this class
            try:
                func = getattr(self, template.func, None)
                if func:
                    res = func(template, objects, urls, **template.kws)
                self.in_q.task_done()
            except Exception as e:
                logging.log(logging.ERROR,
                            'This template did not store correctly ' +
                            str(template.name) + str(template.url) +
                            str(objects) + str(e))


class BaseDatabase(object):
    forbidden_chars = []

    def __init__(self):
        self.in_q = JoinableQueue()

    def check_forbidden_chars(self, key):
        if any(c in key for c in self.forbidden_chars):
            raise Exception(forbidden_characters.format(str(forbidden_chars),
                                                        str(key)))

    def store(self, template, objects, urls):
        #pp.pprint(objects)
        self.worker.in_q.put((template, objects, urls))

    def start(self):
        assert self.worker, "There is no worker to start"
        self.worker.start()

    def stop(self):
        if self.worker.is_alive():
            print('stopping', self.name)
            self.worker.in_q.put(None)


class MongoDB(BaseDatabase):
    '''
    A database class for MongoDB.
    The variables that can be set are:
        host
        port
    '''
    name = 'MongoDB'
    forbidden_chars = ('.', '$')

    def __init__(self, db, host=None, port=None, **kwargs):
        super().__init__(**kwargs)
        self.client = MongoClient(host=host, port=port, connect=False)
        db = getattr(self.client, db)
        self.worker = MongoDBWorker(parent=self, database=db, **kwargs)


class MongoDBWorker(BaseDatabaseImplementation):
    def get_collection(self, table):
        if table:
            return getattr(self.db, table)
        return getattr(self.db, self.table)

    #!@add_other_doc(Collection.insert_many)
    def create(self, template, objects, urls, *args, **kwargs):
        coll = self.get_collection(template.table)
        return coll.insert_many(objects, *args, **kwargs)

    #!@add_other_doc(Collection.bulk_write)
    def update(self, template, objects, urls, key='', method='$set',
               upsert=True, date=False):
        coll = self.get_collection(template.table)
        queries = self._create_queries(key, objects)
        if date:
            date = datetime.datetime.fromtimestamp(time.time())
            objects = ({date.isoformat(): obj}
                       for obj in objects)

        # insert all the objects in the database
        db_requests = [UpdateMany(query, {method: obj}, upsert=upsert)
                       for obj, query in zip(objects, queries)]
        return coll.bulk_write(db_requests)

    #!@add_other_doc(Collection.find)
    def read(self, table='', query={}, **kwargs):
        coll = self.get_collection(table)
        yield from coll.find(query, **kwargs)

    def delete(self):
        pass

    def _create_queries(self, key, objects):
        if not key:
            return ({'url': obj['_url']} for obj in objects)
        else:
            return ({key: obj[key][0]} for obj in objects)


# TODO fix this to the new spec
class ShellCommand(BaseDatabase):
    name = 'ShellCommand'

    def __init__(self, db, table='', database=None):
        super().__init__()

class ShellCommandWorker(BaseDatabaseImplementation):
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


class CSVWorker(BaseDatabaseImplementation):
    def __init__(self, db, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = {}
        self.columns = {}

    def filename(self, table):
        assert table or self.table, 'No table has been set in the template'
        return '{}_{}.csv'.format(self.db, table if table else self.table)

    def check_existing(self, template):
        filename = self.filename(template.table)
        if os.path.isfile(filename):
            self.index[filename] = self.create_index(filename)

    def create_index(self, filename):
        index = {}
        with open(filename) as fle:
            reader = csv.DictReader(fle)
            for i, row in enumerate(reader):
                index[row['_url']] = i
        return index

    def create(self, template, objects, urls, **kwargs):
        filename = self.filename(template.table)
        if not self.index.get('filename', False):
            self.index[filename] = self.create_index(filename)
        with open(filename, 'a') as fle:
            writer = csv.DictWriter(fle,
                                    fieldnames=objects[0].keys())
            writer.writeheader()
            writer.writerows(objects)
            index = dict(enumerate((o['_url'] for o in objects)))
            self.index[filename] = {**self.index[filename], **index}

    # TODO Fix this
    def read(self, template, urls):
        pass

    def update(self, template, objects, urls):
        filename = self.filename(template.table)
        if not self.index.get('filename', False):
            self.index[filename] = self.create_index(filename)

        with open(filename, 'a') as fle:
            writer = csv.DictWriter(fle,
                                    fieldnames=objects[0].keys())
            writer.writerows(objects)

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

    def get_table(self, table):
        if not table:
            return self.table
        return table

    def create_schema(self, template):
        attrs = template.attrs
        table = self.get_table(template.table)
        # TODO set correct types for the attrs
        yield self.template_table.format(table=table)
        yield self.template_index.format(table=table)
        yield from self.attr_schema(template, table)

    def attr_schema(self, template, table):
        '''
        Creates the table definitions for each attribute of a
        template.
        '''
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

    def create(self, template, objects, urls, *args, **kwargs):
        self.check_schema(template)
        table = self.get_table(template.table)

        query = "INSERT INTO {table} VALUES (?, ?);"

        with self.db as con:
            # By inserting NULL into the id column SQLITE will create the id.
            values = list(zip([None] * len(urls), urls))
            con.executemany(query.format(table=table), values)

            # We select all the ids that were inserted to create the attrs
            urls_ids = dict(self.urls_ids(table, urls))

            for attr in template.attrs.keys():
                table_name = '_'.join((table, attr))

                for obj, url in zip(objects, urls):
                    db_id = urls_ids[url]
                    for value in obj[attr]:
                        con.execute(query.format(table=table_name), (db_id, value))

    def urls_ids(self, table, urls):
        id_query = """ SELECT url, id FROM {table} WHERE url =
        ?""".format(table=table)
        urls_ids = []
        with self.db as con:
            for url in urls:
                urls_ids.extend(con.execute(id_query, (url,)).fetchall())
        return urls_ids

    def update(self, template, objects, urls, *args, **kwargs):
        self.check_schema(template)
        table = self.get_table(template.table)

        query = "UPDATE {} SET {} = ? WHERE id = ?"

        for (url, i) in self.urls_ids(table, urls):
            obj_idx = urls.index(url)
            obj = objects[obj_idx]

            for attr in obj.keys():
                table_name = '_'.join((table, attr))
                for value in obj[attr]:
                    con.execute(query.format(table_name, attr), (value, i))

    def delete(self, template, objects, urls, *args, **kwargs):
        self.check_schema(template)
        table = self.get_table(template.table)
        urls_ids = dict(self.urls_ids(table, urls))
        delete_query = 'DELETE FROM {table} WHERE id = ?'
        with self.connect(template) as con:
            for url in urls:
                db_id = urls_ids[url]
                con.execute(delete_query.format(table), (db_id,))

    #TODO fix this method
    def read(self, template, urls, *args, **kwargs):
        pass
