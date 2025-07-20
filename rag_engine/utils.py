# rag_engine/utils.py
# --------------------------------------------------
# Utilities for loading blog/notes markdown and photos
# --------------------------------------------------
"""
依赖：
  pip install python-frontmatter Pillow exifread

返回类型：
  list[llama_index.core.schema.Document]
"""
from __future__ import annotations
from typing import Iterable, Union

import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Sequence
import pillow_heif
import exifread          # EXIF 解析
import frontmatter       # 解析 markdown front-matter
from llama_index.core.schema import Document
from datetime import date, datetime

# ---------- 公共辅助 ----------

pillow_heif.register_heif_opener()        # 让 PIL 支持 HEIC
_IMG_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tiff", ".bmp"}

def _to_jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- Markdown 处理 ----------


def _normalize_date(v) -> str:
    """把多种日期格式统一成 YYYY-MM-DD 字符串"""
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v).strftime("%Y-%m-%d")
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    try:
        return datetime.fromisoformat(str(v)[:10]).strftime("%Y-%m-%d")
    except Exception:
        return ""


# rag_engine/utils.py 片段
def load_markdown_docs(md_dir: Path | str) -> list[Document]:
    md_dir = Path(md_dir)
    docs: list[Document] = []

    for fp in md_dir.rglob("*.md"):
        post  = frontmatter.loads(fp.read_text(encoding="utf-8"))

        meta = {
            "title": str(post.get("title") or fp.stem),
            "date":  _to_jsonable(post.get("date") or fp.stat().st_mtime),
            "tags":  post.get("tags", []),
            "file_path": str(fp),
        }

        docs.append(Document(text=post.content, metadata=meta))
    return docs


# ---------- Photo 处理 ----------

JSONSafe = Union[str, int, float, None]

def _to_jsonable(v) -> JSONSafe:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v

def load_photo_docs(photo_src: Union[str, Path, Iterable]) -> list[Document]:
    """
    支持三种调用方式：
    1. `photo_src="/path/to/photos_dir"`                -> 扫整个目录
    2. `photo_src=[{"file_path": "...", ...}, ...]`     -> 已带元数据的列表
    3. `photo_src=["/a.jpg", "/b.png", ...]`            -> 只有路径的列表
    """
    # ── ① 如果传进来是路径（目录） ──────────────────────────────
    if isinstance(photo_src, (str, Path)):
        from .photos_db import get_db_connection
        conn   = get_db_connection()
        cursor = conn.execute("SELECT * FROM photos")
        photos = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # ── ② 如果传进来是列表 ─────────────────────────────────
    else:
        photos = []
        for item in photo_src:
            if isinstance(item, (str, Path)):
                # 仅有文件路径 → 造一个最简 dict
                photos.append({"file_path": str(item)})
            else:
                photos.append(dict(item))  # 已是 dict，拷贝一份防止修改原始对象

    # ── ③ 列表统一转成 Document ────────────────────────────────
    docs: list[Document] = []
    for p in photos:
        file_path = Path(p["file_path"])
        tags = (p.get("ai_tags") or "").split(",")
        tag_str = ",".join(tags)
        text = (p.get("ai_description") or "") + \
               "\n关键词: " + " ".join(tags)
        meta = {
            "title":     file_path.stem,
            "date":      _to_jsonable(p.get("date")),
            "file_path": str(file_path),
            "camera":    p.get("camera"),
            "lat":       p.get("lat"),
            "lon":       p.get("lon"),
            "ai_tags":   tag_str,
            "src":       p["file_path"],
        }
        
        docs.append(Document(text=text, metadata=meta))

    return docs