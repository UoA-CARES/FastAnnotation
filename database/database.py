import mysql.connector
from mysql.connector import pooling
from mysql.connector.errors import InterfaceError
from mysql.connector.errors import PoolError

import time


class Database:
    def __init__(self, config):
        self.config = config
        self.db_config = {
            'host': self.config.DATABASE_HOST,
            'user': self.config.DATABASE_USER,
            'database': self.config.DATABASE_NAME,
            'password': self.config.DATABASE_PASSWORD,
            'autocommit': True,
            'time_zone': self.config.DATABASE_TIMEZONE
        }

        self.db_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="db_pool", pool_size=self.config.DATABASE_POOL_SIZE, **self.db_config)

    def query(self, query_string, params=None, timeout=3):
        t0 = time.time()
        t1 = t0

        connection = None
        while (t1 - t0) < timeout:
            t1 = time.time()
            try:
                connection = self.db_pool.get_connection()
            except PoolError:
                print("Retrying Connection..")
                time.sleep(1)
                continue
            else:
                break
        print("Connection Made")

        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query_string, params)
            try:
                result = cursor.fetchall()
            except InterfaceError as ex:
                result = []
            id = cursor.lastrowid
        finally:
            cursor.close()
            connection.close()
        return result, id
