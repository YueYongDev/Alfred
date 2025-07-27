# rag_engine/formatters/formatter.py

def format_note(note) -> str:
    return f"""[笔记]
标题：{note.title}
标签：{", ".join(note.ai_tags or [])}
创建时间：{note.created_at}
摘要：{note.ai_summary or ""}
正文：{note.content}
"""


def format_blog(blog) -> str:
    return f"""[博客]
标题：{blog.title}
作者：{blog.author}
标签：{", ".join(blog.ai_tags or [])}
发布时间：{blog.published_at}
摘要：{blog.ai_summary or ""}
正文：{blog.body}
"""


def format_photo(photo) -> str:
    return f"""[照片]
路径：{photo.file_path}
拍摄时间：{photo.taken_at}
地点：{photo.location}
相机：{photo.camera_model}
坐标：{photo.gps_lat}, {photo.gps_lng}
标签：{", ".join(photo.ai_tags or [])}
描述：{photo.ai_summary or ""}
"""


def format_rednote(rednote) -> str:
    return f"""[小红书笔记]
笔记id：{rednote.note_id}
笔记url：{rednote.note_url}
笔记类型：{rednote.note_type}
用户id：{rednote.user_id}
用户主页url：{rednote.home_url}
昵称：{rednote.nickname}
头像url：{rednote.avatar}
标题：{rednote.title}
描述：{rednote.description}
点赞数量：{rednote.liked_count}
收藏数量：{rednote.collected_count}
评论数量：{rednote.comment_count}
分享数量：{rednote.share_count}
视频封面url：{rednote.video_cover}
视频地址url：{rednote.video_addr}
图片地址url列表：{', '.join(rednote.image_list or [])}
标签：{", ".join(rednote.tags or [])}
上传时间：{rednote.upload_time}
ip归属地：{rednote.ip_location}
"""