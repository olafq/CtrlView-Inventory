import os
from pydantic import BaseModel

class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://inv:inv@localhost:5433/inventory")

settings = Settings()

ENV = os.getenv("ENV", "prod")

def is_dev() -> bool:
    return ENV == "dev"