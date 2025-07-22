from datetime import datetime
from pathlib import Path
import time

import frontmatter
from sqlalchemy import or_
from sqlalchemy.orm import Session
from tqdm import tqdm

from db.models import Note
from summarizer.summarizer import summarize_text_file


def import_notes_from_directory(notes_dir: str, session: Session):
    """递归读取 notes 目录下的 Markdown 文件，并写入 note 表，若文件名已存在则更新"""
    md_files = list(Path(notes_dir).rglob("*.md"))
    count_insert = 0
    count_update = 0
    use_tqdm = len(md_files) > 10000
    iterator = tqdm(md_files, desc="导入笔记", unit="file") if use_tqdm else md_files
    for md_file in iterator:
        try:
            post = frontmatter.load(md_file)
            title = post.get("title") or md_file.stem
            content = post.content
            tags = post.get("tags") or []
            created_at = post.get("created_at") or datetime.fromtimestamp(md_file.stat().st_mtime)

            # 查找是否已存在同名文件
            existing_note = session.query(Note).filter_by(file_path=str(md_file)).first()
            if existing_note:
                existing_note.title = title
                existing_note.content = content
                existing_note.tags = tags
                existing_note.created_at = created_at
                count_update += 1
            else:
                note = Note(
                    title=title,
                    content=content,
                    tags=tags,
                    created_at=created_at,
                    file_path=str(md_file)
                )
                session.add(note)
                count_insert += 1
        except Exception as e:
            print(f"[⚠️] 导入 Note 文件失败: {md_file} - {e}")
    session.commit()
    print(f"✅ 新增 {count_insert} 条 Note，更新 {count_update} 条 Note 数据")


def summarize_notes(session: Session):
    notes = session.query(Note).filter(or_(Note.summary == None, Note.summary == "", Note.tags == None, Note.tags == [])).all()
    count = 0
    if not notes:
        print("没有需要总结的 Note")
        return
    start_time = time.time()
    for note in tqdm(notes, desc="总结笔记", unit="note"):
        summary, tags = summarize_text_file(note.file_path)
        note.summary = summary
        note.tags = tags
        note.last_summarized_at = datetime.now()
        count += 1
    session.commit()
    elapsed = time.time() - start_time
    print(f"✅ Note 总结完成，共处理 {count} 条，用时 {elapsed:.2f} 秒")
