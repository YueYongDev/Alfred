# rag_engine/vector_rag/query_engine.py

from db.database import SessionLocal
from db.models import UnifiedEmbedding
from llm.providers import get_embed_model, get_llm


def search_vector_db(query, top_k=8):
    embed_model = get_embed_model()
    q_emb = embed_model.get_text_embedding(query)

    session = SessionLocal()
    stmt = (
        session.query(
            UnifiedEmbedding.entry_type,
            UnifiedEmbedding.entry_id,
            UnifiedEmbedding.text,
            UnifiedEmbedding.embedding.cosine_distance(q_emb).label("score"),
        )
        .order_by("score")
        .limit(top_k)
    )
    results = stmt.all()
    session.close()
    return [
        {
            "entry_type": r[0],
            "entry_id": r[1],
            "text": r[2],
            "score": r[3]
        }
        for r in results
    ]


def answer_question_sync(question, top_k=8):
    docs = search_vector_db(question, top_k=top_k)
    context = "\n---\n".join([doc['text'] for doc in docs])
    prompt = (
        f"请参考以下信息来回答用户的问题。\n"
        f"如果信息相关，请依据信息作答。如果信息不相关或不足以回答问题，请利用你自己的知识来回答。\n"
        f"在回答的末尾，请另起一行简单说明你的回答主要依据的是“外部信息”还是“自身知识”。\n\n"
        f"--- 检索到的相关信息 ---\n{context}\n\n"
        f"--- 用户问题 ---\n{question}\n\n"
        f"请用简洁明了的中文作答。"
    )
    llm = get_llm()
    return llm.complete(prompt).text


def answer_question_stream(question, top_k=8):
    import json
    import requests
    from server.config import OLLAMA_BASE_URL, BASE_MODEL

    docs = search_vector_db(question, top_k=top_k)
    context = "\n---\n".join([doc['text'] for doc in docs])
    prompt = (
        f"请参考以下信息来回答用户的问题。\n"
        f"如果信息相关，请依据信息作答。如果信息不相关或不足以回答问题，请利用你自己的知识来回答。\n"
        f"--- 检索到的相关信息 ---\n{context}\n\n"
        f"--- 用户问题 ---\n{question}\n\n"
        f"请用简洁明了的中文作答。"
    )

    s = requests.Session()
    with s.post(
        f"{OLLAMA_BASE_URL}/v1/chat/completions",
        json={
            "model": OLLAMA_BASE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        },
        headers={"Content-Type": "application/json"},
        stream=True,
    ) as resp:
        for line in resp.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    try:
                        json_data = json.loads(decoded_line[6:])
                        if "content" in json_data["choices"][0]["delta"]:
                            yield json_data["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        pass


if __name__ == "__main__":
    q = "我之前是不是拍过一张猫的照片你还记得吗"
    for chunk in answer_question_stream(q):
        print("Streamed chunk:", chunk)