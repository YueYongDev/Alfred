# ingest/embed_and_store.py
from typing import Any

from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy.orm import Session

from db.crud import (
    get_unembedded_notes, update_note_embedding,
    get_unembedded_blogs, update_blog_embedding,
    get_unembedded_photos, update_photo_embedding
)
from db.database import SessionLocal


def embed_table(
        table_name: str,
        items: list[Any],
        text_getter,
        update_fn,
        store: PGVectorStore,
        embed_model: OllamaEmbedding,
):
    """
    通用 embedding 与存储函数
    """
    if not items:
        return

    texts = [text_getter(i) for i in items]
    resp = embed_model.embed(texts)
    for item, emb in zip(items, resp.embeddings):
        doc = {
            "id": str(item.id),
            "content": text_getter(item),
            "embedding": emb,
        }
        store.add([doc])
        update_fn(db, item.id, emb)


def main():
    # 1. 初始化 DB 与模型、store
    db: Session = SessionLocal()
    embed_model = OllamaEmbedding(model_name="mxbai-embed-large")
    store_note = PGVectorStore.from_params(
        host="localhost", port=5432, database="alfred",
        user="root", password="root",
        table_name="note", embed_dim=768)
    store_blog = PGVectorStore.from_params(
        host="localhost", port=5432, database="alfred",
        user="root", password="root",
        table_name="blog", embed_dim=768)
    store_photo = PGVectorStore.from_params(
        host="localhost", port=5432, database="alfred",
        user="root", password="root",
        table_name="photo", embed_dim=768)

    # 2. 拉取未嵌入数据
    notes = get_unembedded_notes(db)
    blogs = get_unembedded_blogs(db)
    photos = get_unembedded_photos(db)

    # 3. 一一处理
    embed_table(
        "note", notes,
        text_getter=lambda n: n.content,
        update_fn=update_note_embedding,
        store=store_note,
        embed_model=embed_model
    )
    embed_table(
        "blog", blogs,
        text_getter=lambda b: b.body,
        update_fn=update_blog_embedding,
        store=store_blog,
        embed_model=embed_model
    )
    embed_table(
        "photo", photos,
        text_getter=lambda p: p.caption or "",
        update_fn=update_photo_embedding,
        store=store_photo,
        embed_model=embed_model
    )

    # 4. 结束
    db.close()


if __name__ == "__main__":
    main()
