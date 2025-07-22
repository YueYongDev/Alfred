from llama_index.core.graph_stores import SimpleGraphStore


class SimpleGraphStoreWithSchema(SimpleGraphStore):
    def get_schema(self, **kwargs) -> str:
        # 尝试从 self._triplets 获取所有关系类型
        triplets = getattr(self, "_triplets", set())  # 避免 IDE 报错
        if not triplets:
            return "图谱中暂无三元组"
        relations = {rel for _, rel, _ in triplets}
        return f"关系类型: {', '.join(sorted(relations))}"
