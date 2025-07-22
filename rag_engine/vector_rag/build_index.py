from llm.providers import get_embed_model
from rag_engine.formatters.formatter import format_note, format_blog, format_photo
from db.models import Note, Blog, Photo, UnifiedEmbedding
from db.database import SessionLocal

def build_index():
    embed_model = get_embed_model()
    session = SessionLocal()

    # Note
    notes = session.query(Note).all()
    for note in notes:
        text = format_note(note)
        embedding = embed_model.get_text_embedding(text)
        item = UnifiedEmbedding(
            entry_type='note',
            entry_id=note.id,
            text=text,
            embedding=embedding.tolist() if hasattr(embedding, "tolist") else embedding,
        )
        session.add(item)

    # Blog
    blogs = session.query(Blog).all()
    for blog in blogs:
        text = format_blog(blog)
        embedding = embed_model.get_text_embedding(text)
        item = UnifiedEmbedding(
            entry_type='blog',
            entry_id=blog.id,
            text=text,
            embedding=embedding.tolist() if hasattr(embedding, "tolist") else embedding,
        )
        session.add(item)

    # Photo
    photos = session.query(Photo).all()
    for photo in photos:
        text = format_photo(photo)
        embedding = embed_model.get_text_embedding(text)
        item = UnifiedEmbedding(
            entry_type='photo',
            entry_id=photo.id,
            text=text,
            embedding=embedding.tolist() if hasattr(embedding, "tolist") else embedding,
        )
        session.add(item)

    session.commit()
    session.close()

if __name__ == "__main__":
    build_index()