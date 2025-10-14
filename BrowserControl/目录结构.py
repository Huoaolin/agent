BrowseControl/
├── src/
│   ├── task_manager.py
│   ├── task_parser.py      # 任务解析器，调用 LLM 服务
│   ├── browser_controller.py
│   ├── result_handler.py
│   ├── logger.py
│   ├── agent.py
│   ├── llm_call.py         # 新增：独立的 LLM 调用模块
│   ├── utils.py
├── tests/
├── tasks/
├── .env
├── requirements.txt
└── main.py