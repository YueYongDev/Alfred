# test_graphrag.py
import os

from rag_engine import config
from rag_engine.graph_rag.build_index import build_graph_index
from rag_engine.graph_rag.query_engine import ask_question


def clear_storage_dir():
    """清空存储目录（仅用于测试）"""
    storage_dir = config.GRAPH_DB_DIR  # 替换为你的实际存储路径
    if os.path.exists(storage_dir):
        for file in os.listdir(storage_dir):
            os.remove(os.path.join(storage_dir, file))
        print(f"🧹 已清空存储目录: {storage_dir}")


if __name__ == "__main__":
    # 清空存储目录（确保从头开始）
    # clear_storage_dir()
    # #
    # # print("▶️ 正在构建 GraphRAG 索引…")
    # build_graph_index()

    print("\n✅ 开始问答测试：")

    # 测试问题1
    q1 = "我去年拍过哪些猫？都在哪里拍的？"
    print(f"Q: {q1}")
    print(f"A: {ask_question(q1)}")

    # 测试问题2
    q2 = "有哪些关于策略模式的笔记？"
    print(f"\nQ: {q2}")
    print(f"A: {ask_question(q2)}")