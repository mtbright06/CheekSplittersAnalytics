from sqlalchemy import text

from app.database.session import SessionLocal


def database_health():

    db = SessionLocal()

    try:

        db.execute(text("SELECT 1"))

        return True

    finally:

        db.close()
