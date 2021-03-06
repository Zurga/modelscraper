from collections import defaultdict
from contextlib import closing
from datetime import datetime
from itertools import zip_longest
from multiprocessing import JoinableQueue as Queue
from multiprocessing import Process
import csv
import json
import logging
import os
import pprint
import sqlite3
import subprocess
import time


from .helpers import add_other_doc

pp = pprint.PrettyPrinter(indent=4)
path = os.path


unsupported = 'The "{}" function is not supported by the {} adapter'
implement_error = "These methods are not implemented in the subclass {}: {}"
forbidden_characters = 'These characters {} cannot be in the name {}'
logger = logging.getLogger(__name__)


class MetaDatabaseImplementation(type):
    def __new__(meta, name, bases, class_dict):
        funcs = ['create', 'read', 'update', 'delete']
        if bases != (object, ):
            not_implemented = [func for func in funcs if func not in
                               class_dict]
            if not_implemented:
                raise NotImplementedError(
                    implement_error.format(name, str(not_implemented)))
        return type.__new__(meta, name, bases, class_dict)


class BaseDatabaseImplementation(Process,
                                 metaclass=MetaDatabaseImplementation):
    create, read, update, delete = None, None, None, None

    def __init__(self, parent=None, database=None, table='', cache=10):
        super().__init__()
        self.parent = parent
        self.db = database
        self.table = table
        self.in_q = parent.in_q
        self.parent = parent
        self.cache = cache
        self.func = getattr(self, parent.func, None)
        self.logger = logging.getLogger('Databases.' + self.__class__.__name__)

    def run(self):
        while True:
            item = self.in_q.get()

            if item is None:
                break
            model, objects, urls = item

            # Call to the functions in this class
            try:
                self.func(model, objects, urls, **model.kws)
                self.in_q.task_done()
            except Exception:
                self.logger.exception('Template storing error:' +
                                      str(model.name) + str(objects))


class BaseDatabase(object):
    forbidden_chars = []

    def __init__(self, db='', table='', func='create', drop_on_start=False):
        assert db, "At least the database name is required"
        self.in_q = Queue()
        self.db = db
        self.table = table
        self.func = func
        self.drop_on_start = drop_on_start

    def check_forbidden_chars(self, key):
        if any(c in key for c in self.forbidden_chars):
            raise Exception(
                forbidden_characters.format(str(self.forbidden_chars),
                                            str(key)))

    def store(self, model, objects, urls):
        # pp.pprint(objects)
        self.worker.in_q.put((model, objects, urls))

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
    '''
    name = 'MongoDB'
    forbidden_chars = ('.', '$')

    @add_other_doc(BaseDatabase.__init__, 'Parameters')
    def __init__(self, host=None, port=None, *args, **kwargs):
        '''
        Parameters
        ----------
        host : str, optional
               The host that the MongoClient will connect to.

        port : int, optional
               The port that will be used with the MongoClient.
        '''
        from pymongo import MongoClient, UpdateMany # noqa
        from pymongo.collection import Collection # noqa
        from pymongo.errors import ConnectionFailure

        super().__init__(*args, **kwargs)
        test_client = MongoClient(host=host, port=port)
        # Check if the MongoDB instance is reachable
        try:
            test_client.admin.command('ismaster')
            del test_client
            self.client = MongoClient(host=host, port=port, connect=False)
            db = getattr(self.client, self.db)
            self.worker = MongoDBWorker(parent=self, database=db,
                                        table=self.table)
        except ConnectionFailure:
            raise Exception('Database or server is not available. ' +
                            'Is MongoDB installed?')


class MongoDBWorker(BaseDatabaseImplementation):
    def get_collection(self, table):
        if table:
            return getattr(self.db, table)
        return getattr(self.db, self.table)

    # @add_other_doc(Collection.insert_many)
    def create(self, model, objects, urls, *args, **kwargs):
        coll = self.get_collection(model.table)
        return coll.insert_many(objects, *args, **kwargs)

    # @add_other_doc(Collection.bulk_write)
    def update(self, model, objects, urls, key='', method='$set',
               upsert=True, date=False):
        coll = self.get_collection(model.table)
        queries = self._create_queries(key, objects)
        if date:
            date = datetime.datetime.fromtimestamp(time.time())
            objects = ({date.isoformat(): obj}
                       for obj in objects)

        # insert all the objects in the database
        db_requests = [UpdateMany(query, {method: obj}, upsert=upsert) # noqa
                       for obj, query in zip(objects, queries)]
        return coll.bulk_write(db_requests)

    # @add_other_doc(Collection.find)
    def read(self, table='', filter={}, **kwargs):
        '''
        Parameters
        ----------
        table : str, optional
                Which table to apply the find method to. This will be passed
                automatically by the ::Model.query:: method.
        '''
        coll = self.get_collection(table)
        yield from coll.find(filter=filter, **kwargs)

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


class ShellCommandWorker(BaseDatabaseImplementation):
    def _handle(self, item):
        for objct in item.objects:
            arguments = item.kws['command'].format(**objct).split()
            subprocess.Popen(arguments)

    def create(self, objects):
        pass

    def read(self, model):
        pass

    def update(self, model):
        pass

    def delete(self, model):
        pass


class CSV(BaseDatabase):
    name = 'CSV database'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db = os.path.abspath(self.db)
        self.worker = CSVWorker(parent=self, database=db, table=self.table)


class CSVWorker(BaseDatabaseImplementation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = {}
        self.columns = {}

    def filename(self, table):
        return '{}_{}.csv'.format(self.db, table if table else self.table)

    def fieldnames(self, model):
        return sorted([*list(model.attrs.keys()), '_url'])

    def check_existing(self, model):
        filename = self.filename(model.table)
        if path.isfile(filename):
            return True
        return False

    def create_index(self, filename):
        index = defaultdict(list)
        if path.isfile(filename):
            with closing(open(filename)) as fle:
                reader = csv.DictReader(fle)
                for i, row in enumerate(reader):
                    index[row['url']].append(i)
        return index

    # TODO fix the indexing method. Though maybe update and delete
    # should not be supported...
    def create(self, model, objects, urls, **kwargs):
        filename = self.filename(model.table)
        existing = self.check_existing(model)
        with closing(open(filename, 'a')) as fle:
            writer = csv.DictWriter(fle,
                                    fieldnames=self.fieldnames(model))
            if not existing:
                writer.writeheader()
            writer.writerows(objects)

    # TODO Fix this
    def read(self, model, urls):
        pass

    def update(self, model, objects, urls):
        filename = self.filename(model.table)
        if not self.index.get('filename', False):
            self.index[filename] = self.create_index(filename)

        with closing(open(filename, 'a')) as fle:
            writer = csv.DictWriter(fle,
                                    fieldnames=self.fieldnames(model))
            writer.writerows(objects)

    def delete(self, model):
        pass


def json_adapter(dictionary):
    return json.dumps(dictionary)


def json_converter(s):
    return json.loads(s)


class Sqlite(BaseDatabase):
    name = 'SQlite'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        connection = sqlite3.connect(self.db + '.db',
                                     sqlite3.PARSE_DECLTYPES)
        sqlite3.register_adapter(dict, json_adapter)
        sqlite3.register_converter('dict', json_converter)
        sqlite3.register_adapter(list, json_adapter)
        sqlite3.register_converter('list', json_converter)
        sqlite3.register_adapter(tuple, json_adapter)
        sqlite3.register_converter('tuple', json_converter)
        self.worker = SqliteWorker(parent=self, database=connection,
                                   table=self.table)


class SqliteWorker(BaseDatabaseImplementation):
    ''' A database implementation for Sqlite3.'''

    url_table = '''CREATE TABLE IF NOT EXISTS {table}
        (id INTEGER PRIMARY KEY ASC, url TEXT);'''

    url_index = 'CREATE INDEX IF NOT EXISTS urlindex ON {table} (url)'

    attr_table = '''CREATE TABLE IF NOT EXISTS {table}_{attr}
        (id INTEGER, value {type})'''

    attr_trigger = '''
        CREATE TRIGGER IF NOT EXISTS delete_{table}
        AFTER DELETE ON {table} BEGIN DELETE FROM {table}_{attr}
        WHERE OLD.id = {table}_{attr}.id; END;
        '''

    insert_query = "INSERT INTO {table} VALUES (?, ?);"

    update_query = "UPDATE {table} SET {attr} = ? WHERE id = ?"

    id_query = "SELECT url, id FROM {table} WHERE url = ?"

    def __init__(self, parent, database, new=False, **kwargs):
        super().__init__(parent, database, **kwargs)
        self.model_schema = {}
        self.connections = {}

    def get_table(self, table):
        if not table:
            return self.table
        return table

    def create_schema(self, model):
        table = self.get_table(model.table)
        # TODO set correct types for the attrs
        yield self.url_table.format(table=table)
        yield self.url_index.format(table=table)
        yield from self.attr_schema(model, table)

    def attr_schema(self, model, table):
        '''
        Creates the table definitions for each attribute of a
        model.
        '''
        for attr in model.attrs:
            if attr.type:
                value_type = attr.type
            else:
                value_type = 'TEXT'
            yield self.attr_table.format(table=table, attr=attr.name,
                                         type=value_type)
            yield self.attr_trigger.format(table=table, attr=attr.name,
                                           type=value_type)

    def check_schema(self, model):
        # Is there a schema of the model we are storing
        if not self.model_schema.get(model.name):
            schema = self.create_schema(model)
            with self.db as connection:
                for line in schema:
                    connection.execute(line)

            self.model_schema[model.name] = schema

    def create(self, model, objects, urls, *args, **kwargs):
        self.check_schema(model)
        table = self.get_table(model.table)

        with self.db as con:
            values = ((none, str(url)) for none, url in
                      zip([None] * len(urls), urls))
            con.executemany(self.insert_query.format(table=table), values)

            # We select all the ids that were inserted to create the attrs
            urls_ids = dict(self.urls_ids(table, urls))

            for attr in model.attrs:
                table_name = '_'.join((table, attr.name))

                for obj, url in zip(objects, urls):
                    db_id = urls_ids[str(url)]
                    if attr.multiple and len(obj[attr.name]) > 1:
                        values = list(zip_longest(obj[attr.name], [db_id],
                                                  fillvalue=db_id))
                        con.executemany(self.insert_query.format(
                            table=table_name), values)
                    else:
                        values = (db_id, obj[attr.name])
                        con.execute(self.insert_query.format(table=table_name),
                                    values)

    def urls_ids(self, table, urls):
        id_query = self.id_query.format(table=table)
        urls_ids = []
        with self.db as con:
            for url in urls:
                urls_ids.extend(con.execute(id_query, (str(url),)).fetchall())
        return urls_ids

    def update(self, model, objects, urls, *args, **kwargs):
        self.check_schema(model)
        table = self.get_table(model.table)

        with self.db as con:
            for (url, i) in self.urls_ids(table, urls):
                obj_idx = urls.index(str(url))
                obj = objects[obj_idx]

                for attr in model.attr.values():
                    table_name = '_'.join((table, attr.name))
                    for value in obj[attr]:
                        con.execute(self.update_query.format(table_name, attr),
                                    (value, i))

    def delete(self, model, objects, urls, *args, **kwargs):
        self.check_schema(model)
        table = self.get_table(model.table)
        urls_ids = dict(self.urls_ids(table, urls))
        delete_query = 'DELETE FROM {table} WHERE id = ?'
        with self.connect(model) as con:
            for url in urls:
                db_id = urls_ids[url]
                con.execute(delete_query.format(table), (db_id,))

    # TODO fix this method
    def read(self, model, urls, *args, **kwargs):
        pass


class File(BaseDatabase):
    '''
    A database that has files as storage. The db parameter will be interpreted
    as the base folder in which to store the objects. The table parameter will
    be interpreted as the subfolders that the objects will be stored in.
    '''

    name = 'File'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        database_folder = path.abspath(self.db) + '/'
        self.worker = FileWorker(database=database_folder, parent=self,
                                 table=self.table)


class FileWorker(BaseDatabaseImplementation):
    def get_path(self, table):
        full_path = os.getcwd() + self.db + table if table else self.table + '/'
        if not path.exists(full_path):
            os.makedirs(full_path)
        return full_path

    def create(self, model, objects, urls, **kwargs):
        path = self.get_path(model.table)
        for objct in objects:
            filename = path + '/' + str(objct['_url']).split('/')[-1]
            # Check if the path is not a directory else remove the slash
            if filename.endswith('/'):
                filename = filename[:-1]
            with closing(open(filename, 'w')) as fle:
                fle.write(str(objct))

    def update(self, model, objects, urls, **kwargs):
        pass

    def delete(self, model, objects, urls, **kwargs):
        pass

    def read(self, model, objects, urls, **kwargs):
        pass


class InfluxDB(BaseDatabase):
    '''
    A implementation of the Influx Database for the storage of
    timeseries data.
    '''

    _name = 'InfluxDB'

    def __init__(self, host='localhost', port=8086, *args, **kwargs):
        from influxdb import InfluxDBClient

        super().__init__(*args, **kwargs)
        database = InfluxDBClient(host=host, port=port, database=self.db)
        self.worker = InfluxDBWorker(parent=self, database=database,
                                     table=self.table)


class InfluxDBWorker(BaseDatabaseImplementation):
    def create(self, model, objects, urls, **kwargs):
        pass

    def update(self, model, objects, urls, **kwargs):
        pass

    def read(self, model, objects, urls, **kwargs):
        pass

    def delete(self, model, objects, urls, **kwargs):
        pass
