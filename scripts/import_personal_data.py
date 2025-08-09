import os
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from collectors.blogs_collector import import_blogs_from_directory, summarize_blogs
from collectors.notes_collector import import_notes_from_directory, summarize_notes
from collectors.photos_collector import import_photo_from_directory, summarize_photos, import_photo_from_photoprism
from client.photoprism_client import Client
from server import config


# === 主入口 ===
def main():
    # === 配置你的文件夹路径（替换为实际路径） ===
    NOTES_DIR = config.NOTES_DIR
    BLOGS_DIR = config.BLOGS_DIR
    PHOTOS_DIR = config.PHOTOS_DIR

    # === 数据库连接配置 ===
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root:root@192.168.100.197:5432/alfred")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # === Photoprism 客户端配置 ===
    PHOTO_PRISM_USERNAME = os.getenv("PHOTO_PRISM_USERNAME", "yueyong")
    PHOTO_PRISM_PASSWORD = os.getenv("PHOTO_PRISM_PASSWORD", "Liang19991108@")
    PHOTO_PRISM_DOMAIN = os.getenv("PHOTO_PRISM_DOMAIN", "http://dx4800-25d3.local:2342")
    
    photoprism_client = Client(
        username=PHOTO_PRISM_USERNAME,
        password=PHOTO_PRISM_PASSWORD,
        domain=PHOTO_PRISM_DOMAIN
    )

    steps = [
        # ("📥 正在导入笔记 ...", lambda: import_notes_from_directory(NOTES_DIR, session)),
        # ("📥 正在导入博客 ...", lambda: import_blogs_from_directory(BLOGS_DIR, session)),
        # ("📷 正在导入照片 EXIF 信息 ...", lambda: import_photo_from_directory(PHOTOS_DIR, session)),
        # ("📸 正在从 Photoprism 导入照片 ...", lambda: import_photo_from_photoprism(photoprism_client, session)),
        # ("📝 正在总结博客 ...", lambda: summarize_blogs(session)),
        # ("📝 正在总结笔记 ...", lambda: summarize_notes(session)),
        ("📝 正在总结照片 ...", lambda: summarize_photos(photoprism_client,session)),
    ]
    for desc, func in steps:
        tqdm.write(desc)
        start_time = time.time()
        func()
        elapsed = time.time() - start_time
        print(f"{desc} took {elapsed:.2f} seconds")
    tqdm.write("✅ 全部导入完成")
    session.close()


if __name__ == "__main__":
    main()