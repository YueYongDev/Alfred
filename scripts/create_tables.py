from sqlalchemy import create_engine
from db.models import Base
import os

if __name__ == "__main__":
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root:root@localhost:5432/alfred")
    engine = create_engine(DATABASE_URL)
    print(f"Creating tables in: {DATABASE_URL}")
    Base.metadata.create_all(engine)
    print("✅ All tables created.")

