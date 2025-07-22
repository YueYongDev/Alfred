# test_graphrag.py

from rag_engine.vector_rag.query_engine import answer_question_sync, answer_question_stream

if __name__ == "__main__":
    # print("▶️ 正在构建 Vector 索引…")
    # build_index()

    print("\n✅ 开始问答测试：")

    # 测试问题1
    # q1 = "我去年拍过哪些猫？都在哪里拍的？"
    # print(f"Q: {q1}")
    # print(f"A: {answer_question_sync(q1)}")
    #
    # # 测试问题2
    # q2 = "有哪些关于策略模式的笔记？"
    # print(f"\nQ: {q2}")
    # print(f"A: {answer_question_sync(q2)}")

    q3 = "你还记得猫的照片吗？"
    print(f"\nQ: {q3}")
    # print(f"A: {answer_question_sync(q3)}")

    for x in answer_question_stream(q3):
        print(x)
