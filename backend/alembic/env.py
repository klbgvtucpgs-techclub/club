from alembic import context

from app import models  # noqa: F401  (registers all tables on Base.metadata)
from app.database import Base, engine

if context.is_offline_mode():
    raise RuntimeError("Offline mode is not supported; run 'alembic upgrade head' against the database.")

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
