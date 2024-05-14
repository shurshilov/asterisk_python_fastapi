# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

from typing import Literal

from schemas.config_schema import Config


class DatabaseStrategy:
    """CDR native asterisk table
    CREATE TABLE cdr (
        calldate datetime NOT NULL default '0000-00-00 00:00:00',
        clid varchar(80) NOT NULL default '',
        src varchar(80) NOT NULL default '',
        dst varchar(80) NOT NULL default '',
        dcontext varchar(80) NOT NULL default '',
        channel varchar(80) NOT NULL default '',
        dstchannel varchar(80) NOT NULL default '',
        lastapp varchar(80) NOT NULL default '',
        lastdata varchar(80) NOT NULL default '',
        duration int(11) NOT NULL default '0',
        billsec int(11) NOT NULL default '0',
        disposition varchar(45) NOT NULL default '',
        amaflags int(11) NOT NULL default '0',
        accountcode varchar(20) NOT NULL default '',
        uniqueid varchar(32) NOT NULL default '',
        userfield varchar(255) NOT NULL default '',
        did varchar(255) NOT NULL default '',
        recordingfile varchar(255) NOT NULL default ''
    )ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

    if cdr table have answer,start,end instead native:
        start = calldate
        end = start + duration
        answer = start + (duration - billsec)
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.cdr_start_field: Literal["calldate", "start"] = "start"

    async def check_cdr_old(self):
        """Check that Asterisk cdr have start column or not"""

    async def get_cdr(self, start_date, end_date):
        """Return calls history

        Arguments:
            start_date -- start date of calls
            end_date -- end date of calls

        Raises:
            BusinessError: The start date cannot be greater than or equal to the end date

        Returns:
            cdr list of calls
        """


class SqliteStrategy(DatabaseStrategy):
    async def check_cdr_old(self):
        import aiosqlite

        check_column = f"SELECT COUNT(*) AS CNTREC FROM pragma_table_info('{self.config.db_table_cdr_name}') WHERE name='calldate'"
        async with aiosqlite.connect(self.config.db_host) as database:
            database.row_factory = aiosqlite.Row

            async with database.execute(check_column) as cursor:
                async for row in cursor:
                    self.cdr_start_field = "calldate"
                    return

    async def get_cdr(self, start_date, end_date):
        import aiosqlite

        # host==path "/var/lib/asterisk/astdb.sqlite3"
        result = []
        async with aiosqlite.connect(self.config.db_host) as database:
            database.row_factory = aiosqlite.Row
            async with database.execute(
                f"SELECT * FROM {self.config.db_table_cdr_name} where {self.cdr_start_field} >= %s and {self.cdr_start_field} <= %s limit 100000;",
                [start_date, end_date],
            ) as cursor:
                async for row in cursor:
                    result.append(row)
        return result


class MysqlStrategy(DatabaseStrategy):
    async def get_conn_cur(self):
        import aiomysql

        conn: aiomysql.Connection = await aiomysql.connect(
            host=self.config.db_host,
            port=self.config.db_port,
            user=self.config.db_user,
            password=self.config.db_password,
            db=self.config.db_database,
        )

        cur: aiomysql.Cursor = await conn.cursor(aiomysql.DictCursor)
        return conn, cur

    async def check_cdr_old(self):
        conn, cur = await self.get_conn_cur()
        check_column = f"SHOW COLUMNS FROM `{self.config.db_table_cdr_name}` LIKE 'calldate'"
        await cur.execute(check_column)
        rows = await cur.fetchall()
        await cur.close()
        conn.close()
        if len(rows):
            self.cdr_start_field = "calldate"
            return

    async def get_cdr(self, start_date, end_date):
        conn, cur = await self.get_conn_cur()
        await cur.execute(
            f"SELECT * FROM {self.config.db_table_cdr_name} where {self.cdr_start_field} >= %s and {self.cdr_start_field} <= %s limit 100000;",
            (start_date, end_date),
        )
        rows = await cur.fetchall()
        await cur.close()
        conn.close()
        return rows


class PostgresqlStrategy(DatabaseStrategy):
    async def get_conn_cur(self):
        import aiopg

        dsn = f"dbname={self.config.db_database} user={self.config.db_user} password={self.config.db_password} host={self.config.db_host} port={self.config.db_port}"
        conn = await aiopg.connect(dsn)
        cur = await conn.cursor()
        return conn, cur

    async def check_cdr_old(self):
        conn, cur = await self.get_conn_cur()
        await cur.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name='{self.config.db_table_cdr_name}' and column_name='calldate'"
        )

        rows = await cur.fetchall()
        await conn.close()
        if len(rows):
            self.cdr_start_field = "calldate"
            return

    async def get_cdr(self, start_date, end_date):
        conn, cur = await self.get_conn_cur()
        await cur.execute(
            f"SELECT * FROM {self.config.db_table_cdr_name} where {self.cdr_start_field} >= %s and {self.cdr_start_field} <= %s limit 100000;",
            (start_date, end_date),
        )
        rows = await cur.fetchall()
        await conn.close()
        return rows
