import mysql.connector
from mysql.connector.errors import InterfaceError


class Database:
    def __init__(self, config):
        self.table_types = {}
        self.config = config
        self.db = mysql.connector.connect(
            host=self.config.DATABASE_HOST,
            user=self.config.DATABASE_USER,
            passwd=self.config.DATABASE_PASSWORD,
        )
        self._generate_table_types()
        self.db.close()

        self.db = mysql.connector.connect(
            host=self.config.DATABASE_HOST,
            user=self.config.DATABASE_USER,
            passwd=self.config.DATABASE_PASSWORD,
            database=self.config.DATABASE_NAME
        )
        self.db.autocommit = True

    def __del__(self):
        self.db.close()

    def query(self, query_string, params=None):
        print("QUERY")
        cursor = self.db.cursor()
        cursor.execute(query_string, params)
        try:
            result = cursor.fetchall()
        except InterfaceError:
            result = []
        id = cursor.lastrowid
        cursor.close()
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
        table_names = [x[0]
                       for x in self.query(query, (self.config.DATABASE_NAME,))[0]]
        for name in table_names:
            query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            query += "WHERE TABLE_NAME = %s "
            query += "ORDER BY ORDINAL_POSITION"
            column_names = [x[0] for x in self.query(query, (name,))[0]]
            self.table_types[name] = column_names
        return