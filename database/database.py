import mysql.connector
from mysql.connector import pooling
from mysql.connector.errors import InterfaceError


class Database:
    def __init__(self, config):
        self.table_types = {}
        self.config = config

        self.db_config = {
            'host': self.config.DATABASE_HOST,
            'user': self.config.DATABASE_USER,
            'password': self.config.DATABASE_PASSWORD,
            'autocommit': True,
            'time_zone': self.config.DATABASE_TIMEZONE
        }

        self.db_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="db_pool", pool_size=self.config.DATABASE_POOL_SIZE, **self.db_config)
        self._generate_table_types()
        self.db_config['database'] = self.config.DATABASE_NAME
        self.db_pool.set_config(**self.db_config)

    def query(self, query_string, params=None):
        print("Query Start")
        connection = self.db_pool.get_connection()
        cursor = connection.cursor()
        cursor.execute(query_string, params)
        try:
            result = cursor.fetchall()
        except InterfaceError:
            result = []
        id = cursor.lastrowid
        cursor.close()
        connection.close()
        print("Query Done")
        return result, id

    def rows_to_json(self, table_name, rows):
        if table_name not in self.table_types:
            return None

        if not isinstance(rows, list):
            rows = [rows]

        column_names = self.table_types[table_name]
        output = []
        for row in rows:
            json = {}
            assert len(row) is len(column_names), "Incoming row has %d fields when it is expected to have %d." % (
                len(row), len(column_names))
            for i in range(len(column_names)):
                json[column_names[i]] = row[i]
            output.append(json)
        return output

    def json_to_rows(self, table_name, json):
        if table_name not in self.table_types:
            return None

        if not isinstance(json, list):
            json = [json]

        column_names = self.table_types[table_name]
        output = []
        for item in json:
            row = []
            for i in range(len(column_names)):
                assert column_names[i] in item, "Incoming JSON Item is missing key '%s'." % (
                    column_names[i])
                row[i] = item[column_names[i]]
            output.append(tuple(row))
        return output

    def _generate_table_types(self):
        self.table_types = {}
        query = "SELECT DISTINCT TABLE_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        query += "WHERE TABLE_SCHEMA = %s"
        table_names = [
            x[0] for x in self.query(
                query, (self.config.DATABASE_NAME,))[0]]
        for name in table_names:
            query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            query += "WHERE TABLE_NAME = %s "
            query += "ORDER BY ORDINAL_POSITION"
            column_names = [x[0] for x in self.query(query, (name,))[0]]
            self.table_types[name] = column_names
        return
