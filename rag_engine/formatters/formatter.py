# rag_engine/formatters/formatter.py

def format_note(note) -> str:
    return f"""[笔记]
标题：{note.title}
标签：{", ".join(note.tags or [])}
创建时间：{note.created_at}
摘要：{note.summary or ""}
正文：{note.content}
"""


def format_blog(blog) -> str:
    return f"""[博客]
标题：{blog.title}
作者：{blog.author}
标签：{", ".join(blog.tags or [])}
发布时间：{blog.published_at}
摘要：{blog.summary or ""}
正文：{blog.body}
"""


def format_photo(photo) -> str:
    return f"""[照片]
路径：{photo.file_path}
拍摄时间：{photo.taken_at}
地点：{photo.location}
相机：{photo.camera_model}
坐标：{photo.gps_lat}, {photo.gps_lng}
标签：{", ".join(photo.tags or [])}
描述：{photo.summary or ""}
"""
