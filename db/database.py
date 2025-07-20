from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://root:root@localhost:5432/alfred"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)