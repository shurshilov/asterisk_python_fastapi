# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

from schemas.config_schema import Config


class DatabaseStrategy:
    def __init__(self, config: Config) -> None:
        self.config = config


class SqliteStrategy(DatabaseStrategy):
    async def get_cdr(self, start_date, end_date):
        import aiosqlite

        # host==path "/var/lib/asterisk/astdb.sqlite3"
        async with aiosqlite.connect(self.config.db_host) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM {self.config.db_table_cdr_name} where start >= %s and start <= %s limit 100000;",
                [start_date, end_date],
            ) as cursor:
                rows = await cursor.fetchall()
                return rows


class MysqlStrategy(DatabaseStrategy):
    async def get_cdr(self, start_date, end_date):
        import aiomysql

        conn = await aiomysql.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            user=self.config.db_user,
            password=self.config.db_password,
            db=self.config.db_database,
        )

        cur = await conn.cursor()
        await cur.execute(
            f"SELECT * FROM {self.config.db_table_cdr_name} where start >= %s and start <= %s limit 100000;",
            (start_date, end_date),
        )
        rows = await cur.fetchall()
        await cur.close()
        conn.close()
        return rows


class PostgresqlStrategy(DatabaseStrategy):
    async def get_cdr(self, start_date, end_date):
        import aiopg

        dsn = f"dbname={self.config.db_database} user={self.config.db_user} password={self.config.db_password} host={self.config.db_host} port={self.config.db_port}"
        conn = await aiopg.connect(dsn)
        cur = await conn.cursor()
        await cur.execute(
            f"SELECT * FROM {self.config.db_table_cdr_name} where start >= %s and start <= %s limit 100000;",
            (start_date, end_date),
        )
        rows = await cur.fetchall()
        await conn.close()
        return rows
