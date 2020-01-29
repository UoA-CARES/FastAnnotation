import mysql.connector


class Database:
    def __init__(self, config):
        self.table_types = {}
        self.config = config
        self.db = mysql.connector.connect(
            host=self.config.DATABASE_HOST,
            user=self.config.DATABASE_USER,
            passwd=self.config.DATABASE_PASSWORD,
            database=self.config.DATABASE_NAME
        )
        self.db_cursor = self.db.cursor()
        self._generate_table_types()

    def query(self, query_string):
        self.db_cursor.execute(query_string)
        return self.db_cursor.fetchall()

    def form_results(self, table_name, results):
        if table_name not in self.table_types:
            return None

        column_names = self.table_types[table_name]
        output = {"results": []}
        for result in results:
            row = {}
            for i in range(len(column_names)):
                row[column_names[i]] = result[i]
            output["results"].append(row)
        return output

    def _generate_table_types(self):
        self.table_types = {}
        query = "SELECT DISTINCT TABLE_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        query += "WHERE TABLE_SCHEMA = \"" + self.config.DATABASE_NAME + "\""
        table_names = [x[0] for x in self.query(query)]
        for name in table_names:
            query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            query += "WHERE TABLE_NAME = \"" + name + "\" "
            query += "ORDER BY ORDINAL_POSITION"
            column_names = [x[0] for x in self.query(query)]
            self.table_types[name] = column_names
        return
