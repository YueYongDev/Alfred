# db/models.py
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, Text, ARRAY, TIMESTAMP, Double
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Note(Base):
    __tablename__ = "note"
    id = Column(Integer, primary_key=True)
    file_path = Column(Text, nullable=False)
    title = Column(Text)
    content = Column(Text, nullable=False)
    ai_tags = Column(ARRAY(Text))
    ai_summary = Column(Text)
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
    ai_tags = Column(ARRAY(Text))
    ai_summary = Column(Text)
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
    ai_tags = Column(ARRAY(Text))
    ai_summary = Column(Text)
    last_summarized_at = Column(TIMESTAMP)
    last_embedded_at = Column(TIMESTAMP)


class Rednote(Base):
    __tablename__ = "rednote"
    note_id = Column(Text, primary_key=True)
    note_url = Column(Text)
    note_type = Column(Text)
    user_id = Column(Text)
    home_url = Column(Text)
    nickname = Column(Text)
    avatar = Column(Text)
    title = Column(Text)
    description = Column(Text)
    liked_count = Column(Integer)
    collected_count = Column(Integer)
    comment_count = Column(Integer)
    share_count = Column(Integer)
    video_cover = Column(Text)
    video_addr = Column(Text)
    image_list = Column(ARRAY(Text))
    tags = Column(ARRAY(Text))
    upload_time = Column(TIMESTAMP)
    ip_location = Column(Text)
    last_update_time = Column(TIMESTAMP)
    ai_tags = Column(ARRAY(Text))
    ai_summary = Column(Text)
    video_download_at= Column(TIMESTAMP)
    image_download_at = Column(TIMESTAMP)
    last_summarized_at = Column(TIMESTAMP)
    last_embedded_at = Column(TIMESTAMP)


class DailyHot(Base):
    __tablename__ = "daily_hot"
    id = Column(Integer, primary_key=True)
    category = Column(Text, nullable=False)  # 热点分类，如 36kr, tieba 等
    title = Column(Text, nullable=False)
    description = Column(Text)  # 描述
    cover = Column(Text)  # 封面图片链接
    hot_score = Column(Integer)  # 热度值
    url = Column(Text)  # 原始链接
    mobile_url = Column(Text)  # 移动端链接
    publish_time = Column(TIMESTAMP)  # 发布时间
    collected_at = Column(TIMESTAMP)  # 收集时间
    ai_tags = Column(ARRAY(Text))  # AI生成的标签
    ai_summary = Column(Text)  # AI生成的摘要
    last_summarized_at = Column(TIMESTAMP)  # 最后一次AI处理时间
    last_embedded_at = Column(TIMESTAMP)  # 最后一次向量化时间


class UnifiedEmbedding(Base):
    __tablename__ = "unified_embeddings"
    id = Column(Integer, primary_key=True)
    entry_type = Column(Text)
    entry_id = Column(Integer)
    text = Column(Text)
    embedding = Column(Vector(1024))  # 用 Vector 而不是 VECTOR