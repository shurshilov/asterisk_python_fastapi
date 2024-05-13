# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

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


class SqliteStrategy(DatabaseStrategy):
    async def get_cdr(self, start_date, end_date):
        import aiosqlite

        # host==path "/var/lib/asterisk/astdb.sqlite3"
        async with aiosqlite.connect(self.config.db_host) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM {self.config.db_table_cdr_name} where calldate >= %s and calldate <= %s limit 100000;",
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
            f"SELECT * FROM {self.config.db_table_cdr_name} where calldate >= %s and calldate <= %s limit 100000;",
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
            f"SELECT * FROM {self.config.db_table_cdr_name} where calldate >= %s and calldate <= %s limit 100000;",
            (start_date, end_date),
        )
        rows = await cur.fetchall()
        await conn.close()
        return rows
