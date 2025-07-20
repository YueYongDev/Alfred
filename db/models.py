# db/models.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Text, ARRAY, TIMESTAMP, Double

Base = declarative_base()

class Note(Base):
    __tablename__ = "note"
    id = Column(Integer, primary_key=True)
    file_path = Column(Text, nullable=False)
    title = Column(Text)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(Text))
    summary = Column(Text)
    created_at = Column(TIMESTAMP)
    last_summarized_at = Column(TIMESTAMP)
    last_embedded_at = Column(TIMESTAMP)

class Blog(Base):
    __tablename__ = "blog"
    id = Column(Integer, primary_key=True)
    file_path = Column(Text, nullable=False)
    slug = Column(Text, unique=True)
    title = Column(Text)
    body = Column(Text, nullable=False)
    author = Column(Text)
    published_at = Column(TIMESTAMP)
    tags = Column(ARRAY(Text))
    summary = Column(Text)
    last_summarized_at = Column(TIMESTAMP)
    last_embedded_at = Column(TIMESTAMP)

class Photo(Base):
    __tablename__ = "photo"
    id = Column(Integer, primary_key=True)
    file_path = Column(Text, nullable=False)
    caption = Column(Text)
    taken_at = Column(TIMESTAMP)
    location = Column(Text)
    camera_model = Column(Text)
    gps_lat = Column(Double)
    gps_lng = Column(Double)
    tags = Column(ARRAY(Text))
    summary = Column(Text)
    last_summarized_at = Column(TIMESTAMP)
    last_embedded_at = Column(TIMESTAMP)