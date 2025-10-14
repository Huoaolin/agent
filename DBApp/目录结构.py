"""
主要模块功能说明：

FileParsing (文件解析模块)
    负责处理输入文件的解析
    包含文件到Markdown的转换功能

Knowledge (知识处理模块)
    处理文档内容的分割和知识提取
    包含不同的分块策略和知识处理工作流

LogManager (日志管理模块)
    管理系统运行日志
    提供日志记录和存储功能

ModelServer (模型服务模块)
    核心服务组件，包含三个子服务：
        EmbeddingServer：向量嵌入服务
        PDF2MDServer：PDF转Markdown服务
        ReRanker：结果重排序服务

Storage (存储模块)
    管理文件和向量数据的存储
    支持文件存储和向量存储（含Elasticsearch集成）
"""



├── FileParsing/                # 文件解析模块
│   ├── File2MarkdownProcesser.py  # 文件到Markdown的处理器
│   └── FilePrase.py            # 文件解析主文件
│
├── Knowledge/                  # 知识处理模块
│   ├── chunking.py             # 内容分块处理
│   ├── chunkStrategy.py        # 分块策略
│   ├── knowledgeExtraction.py  # 知识提取
│   ├── knowledgeStrategy.py    # 知识处理策略
│   ├── meta_chunk.py           # 元数据分块
│   ├── workflow.py             # 工作流管理
│   └── try.ipynb               # 测试笔记本
│
├── LogManager/                 # 日志管理模块
│   ├── logs/                   # 日志存储目录
│   └── untitled.py             # 日志相关功能
│
├── ModelServer/                # 模型服务模块
│   ├── EmbeddingServer/        # 嵌入服务
│   │   ├── utils.py            # 工具函数
│   │   └── readme.ipynb        # 说明文档
│   ├── PDF2MDServer/           # PDF转Markdown服务
│   │   ├── pdf2markdownAPI.py  # API实现
│   │   ├── OutputTemp/         # 输出临时目录
│   │   ├── UploadTemp/         # 上传临时目录
│   │   └── readme.ipynb        # 说明文档
│   └── ReRanker/               # 重排序服务
│       └── utils.py            # 工具函数
│
├── Storage/                    # 存储模块
│   ├── filestorage/            # 文件存储
│   ├── storage.py              # 存储主文件
│   └── verctorstorage/         # 向量存储
│       └── esModule.py         # Elasticsearch模块
│
└── QueryEngine/
    ├── __init__.py           # 标记为 Python 包
    ├── query_rewriter.py     # 查询改写逻辑（QueryRewriter 类）
    ├── query_executor.py     # 查询执行逻辑（QueryExecutor 类）
    ├── query_engine.py       # QueryEngine 主类，整合 Rewriter 和 Executor
    ├── utils.py              # 查询相关的工具函数
    └── readme.ipynb          # 模块说明文档