```angular2html
personal-ai/
├─ config/              # 统一 YAML / TOML 配置
│  ├─ settings.yaml
│  └─ secrets.env
├─ data_ingest/
│  ├─ collectors/       # “拉”原始数据
│  │  ├─ notes_collector.py
│  │  ├─ blog_rss_collector.py
│  │  ├─ photos_scanner.py
│  │  └─ chats_collector.py
│  └─ extractors/       # “洗”成结构化+向量
│     ├─ text_extractor.py
│     ├─ image_extractor.py
│     ├─ video_extractor.py
│     └─ ocr_utils.py
├─ db/                  # 关系库迁移与模型
│  ├─ schema.sql
│  └─ alembic/          # 如用 Alembic 做迁移
├─ vector_store/
│  ├─ build_index.py    # PgVector / LanceDB 二选一
│  └─ search.py
├─ graph/               # 可选：GraphRAG 关系层
│  ├─ build_graph.py
│  └─ query_graph.py
├─ rag_engine/          # 核心：Retriever + LLM
│  ├─ embed.py          # Ollama/nomic-embed-text
│  ├─ retriever.py      # Hybrid (vector+metadata)
│  ├─ generator.py      # gemma:12b 统一出接口
│  └─ api.py            # FastAPI → OpenAI 兼容
├─ scheduler/           # Prefect / Airflow DAGs
│  ├─ flows.py
│  └─ tasks.py
├─ tests/
└─ scripts/             # 一键脚本、CLI 工具
```

