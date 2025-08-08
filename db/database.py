from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://root:root@192.168.100.197:5432/alfred"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)