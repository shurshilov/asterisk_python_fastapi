# Copyright 2024 Artem Shurshilov
# Apache License Version 2.0

from schemas.config_schema import Config
from services.database import MysqlStrategy, PostgresqlStrategy, SqliteStrategy


def get_db_connector(
    config: Config,
) -> PostgresqlStrategy | MysqlStrategy | SqliteStrategy:
    """
    Pattern strategy. Select strategy for work with databases.
    """
    if config.db_dialect == "sqlite":
        connector_database = SqliteStrategy(config)
    if config.db_dialect == "mysql":
        connector_database = MysqlStrategy(config)
    if config.db_dialect == "postgresql":
        connector_database = PostgresqlStrategy(config)
    return connector_database
