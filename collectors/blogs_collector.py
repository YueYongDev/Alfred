import time
from datetime import datetime
from pathlib import Path

import frontmatter
from sqlalchemy import or_
from sqlalchemy.orm import Session
from tqdm import tqdm

from db.models import Blog
from summarizer.summarizer import summarize_text_file


def _process_single_blog_file(md_file, session):
    """处理单个博客文件"""
    try:
        post = frontmatter.load(md_file)
        title = post.get("title") or md_file.stem
        content = post.content
        slug = post.get("slug") or md_file.stem
        author = post.get("author") or "unknown"
        ai_tags = post.get("tags") or []
        published_at = post.get("published_at") or datetime.fromtimestamp(md_file.stat().st_mtime)

        # 查找是否已存在同名文件
        existing_blog = session.query(Blog).filter_by(file_path=str(md_file)).first()
        if existing_blog:
            existing_blog.title = title
            existing_blog.slug = slug
            existing_blog.body = content
            existing_blog.author = author
            existing_blog.ai_tags = ai_tags
            existing_blog.published_at = published_at
            return "update"
        else:
            blog = Blog(
                title=title,
                slug=slug,
                body=content,
                author=author,
                ai_tags=ai_tags,
                published_at=published_at,
                file_path=str(md_file)
            )
            session.add(blog)
            return "insert"
    except Exception as e:
        print(f"[⚠️] 导入 Blog 文件失败: {md_file} - {e}")
        return None


def import_blogs_from_directory(blog_dir: str, session: Session):
    """递归读取 blogs 目录下的 Markdown 文件，并写入 blog 表，若文件名已存在则更新"""
    md_files = list(Path(blog_dir).rglob("*.md"))
    count_insert = 0
    count_update = 0
    use_tqdm = len(md_files) > 10000
    iterator = tqdm(md_files, desc="导入博客", unit="file") if use_tqdm else md_files
    
    for md_file in iterator:
        result = _process_single_blog_file(md_file, session)
        if result == "insert":
            count_insert += 1
        elif result == "update":
            count_update += 1
            
    session.commit()
    print(f"✅ 新增 {count_insert} 条 Blog，更新 {count_update} 条 Blog 数据")


def _process_single_blog_summary(blog, session):
    """处理单个博客的AI摘要"""
    try:
        ai_summary, ai_tags = summarize_text_file(blog.file_path)
        blog.ai_summary = ai_summary
        blog.ai_tags = ai_tags
        blog.last_summarized_at = datetime.now()
        session.commit()
        return True
    except Exception as e:
        print(f"[⚠️] 博客分析失败: {blog.file_path} - {e}")
        return False


def summarize_blogs(session: Session):
    blogs = session.query(Blog).filter(
        or_(Blog.ai_summary == None, Blog.ai_summary == "", Blog.ai_tags == None, Blog.ai_tags == [])).all()
    if not blogs:
        print("没有需要总结的 Blog")
        return
    
    count = 0
    start_time = time.time()
    
    for blog in tqdm(blogs, desc="总结博客", unit="blog"):
        if _process_single_blog_summary(blog, session):
            count += 1
    
    elapsed = time.time() - start_time
    print(f"✅ Blog 总结完成，共处理 {count} 条，用时 {elapsed:.2f} 秒")