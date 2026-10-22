"""Apply pending schema migrations: python -m app.persistence.migrate"""
from .settings import load_settings
from .sqlite_repository import SqliteRepository


def main() -> None:
    settings = load_settings()
    applied = SqliteRepository(settings.database_path).migrate()
    print(f"database: {settings.database_path}")
    print("applied: " + (", ".join(applied) if applied else "none (already up to date)"))


if __name__ == "__main__":
    main()
