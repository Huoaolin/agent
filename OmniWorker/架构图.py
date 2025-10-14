OmniWorker/
├── src/                        # 源代码目录
│   ├── core/                   # 核心模块
│   │   ├── input_processor.py  # 输入处理器模块
│   │   ├── task_planner.py     # 任务规划器模块
│   │   ├── task_executor.py    # 任务执行器模块
│   │   ├── tool_manager.py     # 工具管理器模块
│   │   ├── state_manager.py    # 状态管理器模块
│   │   ├── interaction_handler.py  # 交互处理器模块（可选）
│   │   ├── logger.py           # 日志记录器（只记录错误/警告）
│   │   └── step_recorder.py    # 步骤记录器（新增）
│   ├── llm/                    # LLM 相关模块
│   │   ├── llm_interface.py    # LLM 接口抽象类
│   │   └── mock_llm.py         # Mock LLM 实现（用于测试）
│   └── main.py                 # 主程序入口
├── config/                     # 配置文件目录
│   ├── config.yaml             # 系统配置文件（如 LLM API 密钥、日志路径等）
│   └── tool_config.json        # 工具配置（如工具参数）
├── logs/                       # 日志存储目录
│   ├── task_log.txt            # 默认任务日志文件
│   └── [task_id]_log.txt       # 按任务 ID 分隔的日志（动态生成）
├── states/                     # 状态存储目录
│   ├── state_task_001.json     # 任务状态文件（动态生成）
│   └── state_task_002.json     # 示例状态文件
├── tests/                      # 测试目录
│   ├── test_input_processor.py # 输入处理器测试
│   ├── test_task_planner.py    # 任务规划器测试
│   ├── test_executor.py        # 执行器测试
│   └── test_tools.py           # 工具测试
├── docs/                       # 文档目录
│   ├── README.md               # 项目说明
│   └── architecture.md         # 系统架构文档
├── requirements.txt            # 依赖文件
└── setup.py                    # 项目安装脚本（可选）




from openai import AzureOpenAI

client = AzureOpenAI(
            api_key='eb48d776240f4c42aa35522bfd4e6c31',
            api_version="2024-08-01-preview",
            azure_endpoint='https://qe2.openai.azure.com'
        )
completion = client.chat.completions.create(
                model='gpt-35-turbo-16k',
                temperature=0.8,
                messages=[
                    {"role": "system", "content": "你是一个助手"},
                    {"role": "user", "content": "你好"},
                ]
            )
response = completion.choices[0].message.content
print(response)



import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List

# 输入处理器
class InputProcessor:
    def __init__(self, llm):
        self.llm = llm  # 大语言模型实例（如 Grok）

    def process(self, query: str) -> Dict:
        prompt = f"解析用户输入并提取意图和目标：{query}"
        response = self.llm.generate(prompt)
        return json.loads(response)  # 返回结构化任务描述

# 任务规划器
class TaskPlanner:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, task_desc: Dict) -> List[str]:
        prompt = f"根据任务描述生成步骤：{json.dumps(task_desc)}"
        response = self.llm.generate(prompt)
        return response.split("\n")  # 返回步骤列表

# 工具接口
class Tool(ABC):
    @abstractmethod
    def execute(self, input_data: Dict) -> str:
        pass

class WebSearchTool(Tool):
    def execute(self, input_data: Dict) -> str:
        query = input_data["query"]
        # 调用 Web 搜索 API 或 Grok 的搜索功能
        return f"搜索结果 for {query}"

class ReportGeneratorTool(Tool):
    def execute(self, input_data: Dict) -> str:
        data = input_data["data"]
        # 生成报告
        return f"报告：{data}"

# 工具管理器（工厂模式）
class ToolManager:
    def __init__(self):
        self.tools = {
            "web_search": WebSearchTool(),
            "report_generator": ReportGeneratorTool()
        }

    def get_tool(self, tool_name: str) -> Tool:
        return self.tools.get(tool_name)

# 任务执行器
class TaskExecutor:
    def __init__(self, tool_manager: ToolManager, logger):
        self.tool_manager = tool_manager
        self.logger = logger

    def execute(self, steps: List[str], state: Dict) -> Dict:
        results = state.get("results", {})
        for step in steps[state.get("current_step", 0):]:
            self.logger.log(f"执行步骤：{step}")
            tool_name, input_data = self.parse_step(step)
            tool = self.tool_manager.get_tool(tool_name)
            result = tool.execute(input_data)
            results[step] = result
            state["current_step"] += 1
            state["results"] = results
            self.logger.log(f"结果：{result}")
        return results

    def parse_step(self, step: str) -> tuple:
        # 解析步骤，提取工具名和输入（可以用 LLM 解析）
        return "web_search", {"query": step}  # 示例

# 状态管理器
class StateManager:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.state_file = f"state_{task_id}.json"

    def save(self, state: Dict):
        with open(self.state_file, "w") as f:
            json.dump(state, f)

    def load(self) -> Dict:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {"current_step": 0, "results": {}}

# 日志记录器
class Logger:
    def __init__(self, log_file: str):
        self.log_file = log_file

    def log(self, message: str):
        with open(self.log_file, "a") as f:
            f.write(f"{message}\n")

# 主系统
class TaskSystem:
    def __init__(self, llm):
        self.llm = llm
        self.input_processor = InputProcessor(llm)
        self.task_planner = TaskPlanner(llm)
        self.tool_manager = ToolManager()
        self.logger = Logger("task_log.txt")

    def run(self, query: str, task_id: str):
        # 初始化状态
        state_manager = StateManager(task_id)
        state = state_manager.load()

        # 处理输入
        task_desc = self.input_processor.process(query)
        self.logger.log(f"任务描述：{task_desc}")

        # 规划任务
        steps = self.task_planner.plan(task_desc)
        self.logger.log(f"任务步骤：{steps}")

        # 执行任务
        executor = TaskExecutor(self.tool_manager, self.logger)
        results = executor.execute(steps, state)
        state_manager.save(state)

        return results

# 示例使用
if __name__ == "__main__":
    class MockLLM:
        def generate(self, prompt):
            if "解析用户输入" in prompt:
                return '{"intent": "竞品分析", "target": "本公司产品", "output": "研究报告"}'
            elif "生成步骤" in prompt:
                return "收集公司产品信息\n搜索竞品\n生成报告"
            return "mock response"

    system = TaskSystem(MockLLM())
    result = system.run("我想了解本公司的产品有哪些竞品，帮我出一份研究报告", "task_001")
    print(result)