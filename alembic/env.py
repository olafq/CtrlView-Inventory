from logging.config import fileConfig
from dotenv import load_dotenv
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

# Cargar variables de entorno
load_dotenv()

# Alembic config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importar Base y modelos
from app.db.session import Base
from app.db.models.channel import Channel
from app.db.models.product import Product
from app.db.models.external_item import ExternalItem
from app.db import models  # importante para que Alembic registre los modelos

target_metadata = Base.metadata

# 👉 ESTO ES LO QUE FALTABA
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

config.set_main_option("sqlalchemy.url", DATABASE_URL)
# 👆👆👆 ESTA LÍNEA ES CLAVE


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
