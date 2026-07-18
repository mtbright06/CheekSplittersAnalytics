from __future__ import annotations

import sys

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import engine


EXPECTED_TABLES = {
    "alembic_version",
    "games",
    "leagues",
    "model_versions",
    "recommendations",
    "teams",
}


def main() -> int:
    print()
    print("=" * 64)
    print("SharpStack Azure PostgreSQL Schema Verification")
    print("=" * 64)
    print()

    try:
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names(schema="public"))

        print("Database connection: SUCCESS")
        print()
        print("Tables found:")

        for table_name in sorted(actual_tables):
            print(f"  - {table_name}")

        missing_tables = EXPECTED_TABLES - actual_tables
        unexpected_tables = actual_tables - EXPECTED_TABLES

        print()

        if missing_tables:
            print("Schema verification: FAILED")
            print()
            print("Missing tables:")

            for table_name in sorted(missing_tables):
                print(f"  - {table_name}")

            return 1

        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            database_user = connection.execute(
                text("SELECT current_user")
            ).scalar_one()

            migration_revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

        print("Schema verification: SUCCESS")
        print()
        print(f"Database:          {database_name}")
        print(f"Connected user:    {database_user}")
        print(f"Alembic revision:  {migration_revision}")
        print(f"Expected tables:   {len(EXPECTED_TABLES)}")
        print(f"Actual tables:     {len(actual_tables)}")

        if unexpected_tables:
            print()
            print("Additional existing tables:")

            for table_name in sorted(unexpected_tables):
                print(f"  - {table_name}")

        print()
        print("SharpStack recommendation history schema is ready.")
        return 0

    except SQLAlchemyError as exc:
        print("Schema verification: FAILED")
        print()
        print(f"Database error: {exc}")
        return 1

    except Exception as exc:
        print("Schema verification: FAILED")
        print()
        print(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
