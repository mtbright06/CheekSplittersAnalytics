from __future__ import annotations

import sys
from collections.abc import Iterable

from sqlalchemy import inspect, text
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import engine


EXPECTED_TABLES = {
    "alembic_version",
    "games",
    "leagues",
    "model_runs",
    "model_versions",
    "recommendations",
    "teams",
}


def print_items(
    heading: str,
    items: Iterable[str],
) -> None:
    print(heading)

    for item in sorted(items):
        print(f"  - {item}")


def verify_model_run_foreign_key(
    inspector: Inspector,
) -> tuple[bool, str]:
    foreign_keys = inspector.get_foreign_keys(
        "recommendations",
        schema="public",
    )

    for foreign_key in foreign_keys:
        constrained_columns = foreign_key.get(
            "constrained_columns",
            [],
        )

        referred_table = foreign_key.get(
            "referred_table",
        )

        referred_columns = foreign_key.get(
            "referred_columns",
            [],
        )

        if (
            constrained_columns == ["model_run_id"]
            and referred_table == "model_runs"
            and referred_columns == ["id"]
        ):
            return (
                True,
                foreign_key.get("name")
                or "unnamed foreign key",
            )

    return (
        False,
        "recommendations.model_run_id foreign key not found",
    )


def main() -> int:
    print()
    print("=" * 68)
    print("SharpStack Azure PostgreSQL Schema Verification")
    print("=" * 68)
    print()

    try:
        inspector = inspect(engine)

        actual_tables = set(
            inspector.get_table_names(
                schema="public",
            )
        )

        print("Database connection: SUCCESS")
        print()

        print_items(
            "Tables found:",
            actual_tables,
        )

        missing_tables = EXPECTED_TABLES - actual_tables
        unexpected_tables = actual_tables - EXPECTED_TABLES

        print()

        if missing_tables:
            print("Schema verification: FAILED")
            print()

            print_items(
                "Missing tables:",
                missing_tables,
            )

            return 1

        model_run_fk_valid, model_run_fk_name = (
            verify_model_run_foreign_key(
                inspector,
            )
        )

        if not model_run_fk_valid:
            print("Schema verification: FAILED")
            print()
            print(model_run_fk_name)
            return 1

        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()

            database_user = connection.execute(
                text("SELECT current_user")
            ).scalar_one()

            migration_revision = connection.execute(
                text(
                    "SELECT version_num "
                    "FROM alembic_version"
                )
            ).scalar_one()

        print("Schema verification: SUCCESS")
        print()
        print(f"Database:             {database_name}")
        print(f"Connected user:       {database_user}")
        print(f"Alembic revision:     {migration_revision}")
        print(f"Expected tables:      {len(EXPECTED_TABLES)}")
        print(f"Actual tables:        {len(actual_tables)}")
        print(f"Model-run FK:         {model_run_fk_name}")

        if unexpected_tables:
            print()

            print_items(
                "Additional existing tables:",
                unexpected_tables,
            )

        print()
        print(
            "SharpStack model-run schema is ready."
        )

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
