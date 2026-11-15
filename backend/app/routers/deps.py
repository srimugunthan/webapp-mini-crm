from fastapi import Request

from ..db import connect


def get_db(request: Request):
    conn = connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def settings(request: Request):
    return request.app.state.settings
