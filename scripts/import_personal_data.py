import os
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from collectors.blogs_collector import import_blogs_from_directory, summarize_blogs
from collectors.notes_collector import import_notes_from_directory, summarize_notes
from collectors.photos_collector import import_photo_from_directory, summarize_photos


# === 主入口 ===
def main():
    # === 配置你的文件夹路径（替换为实际路径） ===
    NOTES_DIR = os.getenv("NOTES_DIR", "/Users/yueyong/alfred_test_data/notes")
    BLOGS_DIR = os.getenv("BLOGS_DIR", "/Users/yueyong/alfred_test_data/blogs")
    PHOTOS_DIR = os.getenv("PHOTOS_DIR", "/Users/yueyong/alfred_test_data/photos")

    # === 数据库连接配置 ===
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root:root@localhost:5432/alfred")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    steps = [
        ("📥 正在导入笔记 ...", lambda: import_notes_from_directory(NOTES_DIR, session)),
        ("📝 正在总结笔记 ...", lambda: summarize_notes(session)),
        ("📥 正在导入博客 ...", lambda: import_blogs_from_directory(BLOGS_DIR, session)),
        ("📝 正在总结博客 ...", lambda: summarize_blogs(session)),
        ("📷 正在导入照片 EXIF 信息 ...", lambda: import_photo_from_directory(PHOTOS_DIR, session)),
        ("📝 正在总结照片 ...", lambda: summarize_photos(session)),
    ]
    for desc, func in steps:
        tqdm.write(desc)
        start_time = time.time()
        func()
        elapsed = time.time() - start_time
    tqdm.write("✅ 全部导入完成")
    session.close()


if __name__ == "__main__":
    main()
