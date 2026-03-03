"""数据库连接工具：封装 PostgreSQL 连接与事务提交/回滚。"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.core.settings import get_db_url


@contextmanager
def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    """提供带自动提交/回滚的数据库连接。"""

    connection = psycopg.connect(get_db_url(), row_factory=dict_row)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
