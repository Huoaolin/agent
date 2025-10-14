# OmniWorker/src/core/task_executor.py
import uuid
import time
import json
import requests
import re
from ..services.llm_service import LLMService
from AIToolsBridge.core.ToolAgent import ToolAgent
from ..core.step_recorder import StepRecorder
from typing import Dict


class MockLogger:
    def __init__(self, log_file):
        self.log_file = log_file

    def error(self, message: str):
        print(f"[ERROR] {message}")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[ERROR] {message}\n")

    def info(self, message: str):
        print(f"[INFO] {message}")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[INFO] {message}\n")


class TaskExecutor:
    def __init__(self, logger, step_recorder: StepRecorder, interaction_handler, max_steps: int=5):
        self.agent = ToolAgent(api_key="sk-2dd841cdc2624791bbf114e73e7fec01")
        # self.logger = logger
        self.job_id = str(uuid.uuid4())
        log_file_path = f"./tasks/{self.job_id}/task_steps.log"
        self.logger = MockLogger(log_file_path)  # 使用任务特定的日志文件

        self.llm = LLMService()
        self.interaction_handler = interaction_handler

        # 最大步骤限制
        self.max_steps = max_steps
        self.step_count = 0  # 初始化步骤计数器

        self.step_recorder = StepRecorder(self.job_id)
        self.logger.info(f"Generated job_id: {self.job_id}")
        self.logger.info(f"Registered tools: {self.agent.list_tools()}")
        self.api_base_url = "http://localhost:5011"  # API 服务地址

    def call_external_api(self, input_string):
        """调用 external_api 的 HTTP 接口"""
        try:
            response = requests.get(f"{self.api_base_url}/external?input={input_string}", timeout=5)
            response.raise_for_status()
            return response.json()["result"]
        except requests.RequestException as e:
            self.logger.error(f"调用 external API 失败: {str(e)}")
            return f"错误: {str(e)}"

    def call_final_result(self, input_string):
        """调用 get_final_result 的 HTTP 接口"""
        try:
            response = requests.get(f"{self.api_base_url}/final_result?input={input_string}", timeout=5)
            response.raise_for_status()
            return response.json()["result"]
        except requests.RequestException as e:
            self.logger.error(f"调用 final_result API 失败: {str(e)}")
            return f"错误: {str(e)}"

    def extract_json_list(self, raw_result: str) -> str:
        pattern = r'\{.*?\}'
        matches = re.findall(pattern, raw_result, re.DOTALL)
        if matches:
            try:
                json.loads(matches[0])
                return matches[0]
            except json.JSONDecodeError:
                print(f"提取的内容不是有效 JSON: {matches[0]}")
                return json.dumps({})
        else:
            print(f"未能在 LLM 输出中提取 JSON 对象: {raw_result}")
            return json.dumps({})

    def _needs_tool(self, step: str, previous_results: Dict) -> bool:
        prompt = (
            "Determine whether the following step requires the use of a tool (e.g., search engine, web scraper, API) "
            "to complete the action. Return the result as a JSON object with a single key 'needs_tool' and a boolean value:\n"
            "Step: '{step}'\n"
            "Context (previous results): {context}\n"
            "Guidelines:\n"
            "- A tool is needed if the step involves external data retrieval save data to file (e.g., searching, querying, downloading, writefile, savadata).\n"
            "- No tool is needed if the step can be completed with existing knowledge or simple computation.\n"
            "- Consider the context from previous results to assess if the data is already available.\n"
            "- Return true or false in JSON format."
        ).format(step=step, context=json.dumps(previous_results))

        response = self.llm.call(prompt)
        response = self.extract_json_list(response)
        print("response!!!!!", response)
        try:
            result = json.loads(response)
            needs_tool = result["needs_tool"]
            return needs_tool
        except (json.JSONDecodeError, KeyError):
            return True

    def _execute_direct_step(self, step: str, previous_results: dict) -> str:
        """使用 LLM 直接回答"""
        prompt = (
            f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
            f"直接回答: {step}"
        )
        result = self.llm.call(prompt)
        return result

    def _handle_user_interaction(self, step: str, result: str, steps: list, current_idx: int, previous_results: dict) -> tuple[list, bool]:
        interrupt, new_input = self.interaction_handler.check_interaction(step, result)
        if interrupt:
            self.logger.info(f"用户中断任务，输入调整: {new_input}")
            adjusted_steps = self.adjust_steps(steps, current_idx, new_input, previous_results)
            return adjusted_steps, True
        return steps, False

    # def execute(self, steps: list, state: dict) -> dict:
    #     """
    #     执行任务步骤，使用 ToolAgent 处理工具调用，并依赖前面步骤的结果。
    #     :param steps: 任务步骤列表。
    #     :param state: 任务状态字典。
    #     :return: 任务执行结果。
    #     """
    #     results = state.get("results", {})
    #     current_step = state.get("current_step", 0)
    #     for i, step in enumerate(steps[current_step:], current_step):
    #         print("----------------------------------")
    #         print("----------------------------------")
    #         print(f" ** 执行中: {step} [Loading...]")
    #         # results = str(results)[-10000:]
    #         # 判断是否需要工具
    #         if self._needs_tool(step, results):
    #             step_result = self._execute_tool_step(step, results)
    #             self.logger.info(f"完成: {step} 结果: {step_result}")
    #         else:
    #             step_result = self._execute_direct_step(step, results)
    #             self.logger.info(f"完成: {step} 结果: {step_result}")
    #         print(f" ** 执行结果：{step_result}")
    #         self.step_recorder.record(step, step_result)
    #         # 记录结果并更新状态
    #         results[step] = step_result
    #         state["current_step"] = i + 1
    #         state["results"] = results
    #         # 根据当前步骤结果调整后续步骤
    #         steps = self.adjust_steps_based_on_result(steps, i, step, step_result, results)
    #         print("**********DEBUG**********")
    #         print("调整后的测试步骤", steps)
    #         print("**********DEBUG**********")
    #         # 处理用户中断
    #         steps, interrupted = self._handle_user_interaction(step, step_result, steps, i, results)
    #         if interrupted:
    #             state["steps"] = steps
    #             break
    #     self.logger.info(f"最终结果: {results}")
    #     return results

    def execute_(self, steps: list, state: dict) -> dict:
        """
        执行任务步骤，使用 ToolAgent 处理工具调用，并依赖前面步骤的结果。
        :param steps: 任务步骤列表。
        :param state: 任务状态字典。
        :return: 任务执行结果。
        """
        results = state.get("results", {})
        current_step = state.get("current_step", 0)

        i = current_step
        while i < len(steps):
            # 检查是否超过最大步骤限制
            if self.step_count >= self.max_steps:
                self.logger.error(f"已达到最大步骤限制 {self.max_steps}，任务中止")
                results["error"] = f"Task aborted: Maximum step limit ({self.max_steps}) reached"
                break

            step = steps[i]
            print("**********************************")
            print("**********************************")
            print(f" ** 执行中: {step} [Loading...]")

            # 判断是否需要工具
            if self._needs_tool(step, results):
                step_result = self._execute_tool_step(step, results)
                self.logger.info(f"完成: {step} 结果: {step_result}")
            else:
                step_result = self._execute_direct_step(step, results)
                self.logger.info(f"完成: {step} 结果: {step_result}")
            print(f" ** 执行结果：{step_result}")

            self.step_recorder.record(step, step_result)
            # 记录结果并更新状态
            results[step] = step_result
            state["current_step"] = i + 1
            state["results"] = results

            # 增加步骤计数器
            self.step_count += 1
            self.logger.info(f"当前执行步骤数: {self.step_count}/{self.max_steps}")

            # 根据当前步骤结果调整后续步骤
            steps = self.adjust_steps_based_on_result(steps, i, step, step_result, results)
            # 处理用户中断
            steps, interrupted = self._handle_user_interaction(step, step_result, steps, i, results)
            if interrupted:
                state["steps"] = steps
                break

            i += 1  # 手动递增索引

        self.logger.info(f"最终结果: {results}")
        return results

    def _execute_tool_step(self, step: str, previous_results: dict) -> str:
        """
        执行需要工具的步骤。
        :param step: 当前步骤的描述。
        :param previous_results: 前面步骤的结果。
        :return: 工具执行的结果。
        """
        print(f"  ****  尝试调用使用工具")
        try:
            start_time = time.time()
            # 将 job_id 拼接到 query_with_context 中
            query_with_context = (
                f"Job ID: {self.job_id}\n"
                f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
                f"执行步骤：{step}"
            )
            tool_result = self.agent.process_query(query_with_context)
            print(f"完成: {step} [耗时: {time.time() - start_time:.2f}s]")
            # self.step_recorder.record(step, "调用 ToolAgent with context", tool_result)
            return tool_result
        except Exception as e:
            # self.logger.error(f"ToolAgent 执行失败: {str(e)}")
            return "工具执行失败"

    def adjust_steps(self, steps: list, current_idx: int, new_input: str, previous_results: dict) -> list:
        prompt = (
            f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
            f"根据新输入 '{new_input}' 调整后续步骤: {steps[current_idx:]}"
        )
        new_steps = self.llm.call(prompt).split("\n")

    def adjust_steps_based_on_result(self, steps: list, current_idx: int, step: str, step_result: str, previous_results: dict) -> list:
        """
        根据当前步骤的结果判断是否需要调整后续步骤。
        :param steps: 当前的任务步骤列表。
        :param current_idx: 当前步骤的索引。
        :param step: 当前执行的步骤。
        :param step_result: 当前步骤的执行结果。
        :param previous_results: 前面步骤的结果。
        :return: 调整后的步骤列表，或原始步骤列表（如果无需调整）。
        """
        # 构造 LLM 判断是否需要调整的提示
        judge_prompt = (
            "根据以下信息，判断当前步骤的结果是否需要调整后续步骤。\n"
            f"当前步骤: '{step}'\n"
            f"当前步骤结果: '{step_result}'\n"
            f"已有结果: {json.dumps(previous_results, ensure_ascii=False)}\n"
            f"后续步骤: {json.dumps(steps[current_idx + 1:], ensure_ascii=False)}\n"
            "Guidelines:\n"
            "- 如果当前步骤结果表明后续步骤无法继续执行（例如数据缺失、错误、或结果与预期不符），返回 JSON {'adjust_needed': true}。\n"
            "- 如果当前步骤结果正常且后续步骤可以继续执行，返回 JSON {'adjust_needed': false}。\n"
            "- 返回结果必须是有效的 JSON 格式。\n"
        )
        
        # 构造 LLM 判断是否需要调整的提示
        # judge_prompt = (
        #     "根据以下信息，判断当前步骤的结果是否需要调整后续步骤。\n"
        #     f"当前步骤: '{step}'\n"
        #     f"当前步骤结果: '{step_result}'\n"
        #     f"已有结果: {json.dumps(previous_results, ensure_ascii=False)}\n"
        #     f"后续步骤: {json.dumps(steps[current_idx + 1:], ensure_ascii=False)}\n"
        #     "任务目标: 尽可能收集足够的信息以得出最终结论。\n"
        #     "Guidelines:\n"
        #     "- 如果当前步骤结果和已有结果已足够得出最终结论（例如所有必要信息已收集齐全），返回 JSON {'adjust_needed': true, 'reason': '信息已足够，无需后续步骤', 'suggested_steps': []}。\n"
        #     "- 如果当前步骤结果表明后续步骤无法继续执行（例如数据缺失、错误、或结果与预期不符），返回 JSON {'adjust_needed': true, 'reason': '缺少必要信息', 'suggested_steps': ['补充步骤1', '补充步骤2', ...]}，其中 suggested_steps 是推荐的新步骤列表。\n"
        #     "- 如果当前步骤结果正常且后续步骤可以按计划执行，返回 JSON {'adjust_needed': false, 'reason': '无需调整', 'suggested_steps': []}。\n"
        #     "- 返回结果必须是有效的 JSON 格式，例如 {'adjust_needed': bool, 'reason': str, 'suggested_steps': list}。\n"
        #     "请结合任务目标和已有信息，分析当前结果是否满足需求，并提供具体理由和建议。\n"
        # )

        # 调用 LLM 判断是否需要调整
        judge_response = self.llm.call(judge_prompt)
        judge_json = self.extract_json_list(judge_response)
        try:
            judge_result = json.loads(judge_json)
            adjust_needed = judge_result.get("adjust_needed", False)
        except (json.JSONDecodeError, KeyError):
            self.logger.error(f"无法解析 LLM 判断结果: {judge_json}，默认需要调整")
            adjust_needed = True

        # 如果需要调整，则调用 LLM 生成新步骤
        if adjust_needed:
            self.logger.info(f"根据步骤结果 '{step_result}' 调整后续步骤")
            adjust_prompt = (
                f"基于以下信息调整后续步骤：\n"
                f"当前步骤: '{step}'\n"
                f"当前步骤结果: '{step_result}'\n"
                f"已有结果: {json.dumps(previous_results, ensure_ascii=False)}\n"
                f"需要调整的后续步骤: {json.dumps(steps[current_idx + 1:], ensure_ascii=False)}\n"
                "请返回调整后的步骤列表，按行分隔，每行一个步骤。"
            )
            new_steps_response = self.llm.call(adjust_prompt)
            adjusted_steps = new_steps_response.split("\n")
            # 过滤空行并返回调整后的完整步骤列表
            adjusted_steps = [s.strip() for s in adjusted_steps if s.strip()]
            return steps[:current_idx + 1] + adjusted_steps
        else:
            self.logger.info(f"无需调整后续步骤")
            return steps





# import uuid
# import time
# import json
# from ..services.llm_service import LLMService
# from AIToolsBridge.core.ToolAgent import ToolAgent
# from ..core.step_recorder import StepRecorder
# from typing import Dict
# import re


# class TaskExecutor:
#     def __init__(self, logger, step_recorder: StepRecorder, interaction_handler):
#         self.agent = ToolAgent(api_key="sk-2dd841cdc2624791bbf114e73e7fec01")
#         self.logger = logger
#         self.llm = LLMService()
#         self.interaction_handler = interaction_handler
#         # 生成唯一的 job_id
#         self.job_id = str(uuid.uuid4())
#         self.step_recorder = StepRecorder(self.job_id)
#         self.logger.info(f"Generated job_id: {self.job_id}")
#         self.logger.info(f"Registered tools: {self.agent.list_tools()}")

#     def extract_json_list(self, raw_result: str) -> str:
#         """Extract the first JSON object ({}) from the raw LLM result."""
#         pattern = r'\{.*?\}'
#         matches = re.findall(pattern, raw_result, re.DOTALL)
#         if matches:
#             try:
#                 json.loads(matches[0])  # 验证 JSON 合法性
#                 return matches[0]
#             except json.JSONDecodeError:
#                 print(f"提取的内容不是有效 JSON: {matches[0]}")
#                 return json.dumps({})
#         else:
#             print(f"未能在 LLM 输出中提取 JSON 对象: {raw_result}")
#             return json.dumps({})

#     def _needs_tool(self, step: str, previous_results: Dict) -> bool:
#         """Use LLM to determine if a step requires a tool."""
#         prompt = (
#             "Determine whether the following step requires the use of a tool (e.g., search engine, web scraper, API) "
#             "to complete the action. Return the result as a JSON object with a single key 'needs_tool' and a boolean value:\n"
#             "Step: '{step}'\n"
#             "Context (previous results): {context}\n"
#             "Guidelines:\n"
#             "- A tool is needed if the step involves external data retrieval (e.g., searching, querying, downloading).\n"
#             "- No tool is needed if the step can be completed with existing knowledge or simple computation.\n"
#             "- Consider the context from previous results to assess if the data is already available.\n"
#             "- Return true or false in JSON format."
#         ).format(step=step, context=json.dumps(previous_results))

#         response = self.llm.call(prompt)
#         response = self.extract_json_list(response)
#         print("response!!!!!", response)
#         try:
#             result = json.loads(response)
#             needs_tool = result["needs_tool"]
#             reason = "需要工具" if needs_tool else "直接回答"
#             # self.step_recorder.record(step, f"LLM 判断：{reason}", reason)
#             return needs_tool
#         except (json.JSONDecodeError, KeyError):
#             # self.step_recorder.record(step, "LLM 返回无效响应，默认需要工具", "需要工具")
#             return True

#     def _execute_tool_step(self, step: str, previous_results: dict) -> str:
#         """
#         执行需要工具的步骤。
#         :param step: 当前步骤的描述。
#         :param previous_results: 前面步骤的结果。
#         :return: 工具执行的结果。
#         """
#         print(f"  ****  尝试调用使用工具")
#         try:
#             start_time = time.time()
#             # 将 job_id 拼接到 query_with_context 中
#             query_with_context = (
#                 f"Job ID: {self.job_id}\n"
#                 f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
#                 f"执行步骤：{step}"
#             )
#             tool_result = self.agent.process_query(query_with_context)
#             print(f"完成: {step} [耗时: {time.time() - start_time:.2f}s]")
#             # self.step_recorder.record(step, "调用 ToolAgent with context", tool_result)
#             return tool_result
#         except Exception as e:
#             # self.logger.error(f"ToolAgent 执行失败: {str(e)}")
#             return "工具执行失败"

#     def _execute_direct_step(self, step: str, previous_results: dict) -> str:
#         """
#         执行不需要工具的步骤（直接回答）。
#         :param step: 当前步骤的描述。
#         :param previous_results: 前面步骤的结果。
#         :return: LLM 直接回答的结果。
#         """
#         prompt = (
#             f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
#             f"直接回答: {step}"
#         )
#         result = self.llm.call(prompt)
#         # self.step_recorder.record(step, prompt, result)
#         return result

#     def _handle_user_interaction(self, step: str, result: str, steps: list, current_idx: int, previous_results: dict) -> tuple[list, bool]:
#         """
#         处理用户中断和交互逻辑。
#         :param step: 当前步骤的描述。
#         :param result: 当前步骤的执行结果。
#         :param steps: 当前任务步骤列表。
#         :param current_idx: 当前步骤的索引。
#         :param previous_results: 前面步骤的结果。
#         :return: 返回调整后的步骤列表和是否中断的标志。
#         """
#         interrupt, new_input = self.interaction_handler.check_interaction(step, result)
#         if interrupt:
#             self.logger.info(f"用户中断任务，输入调整: {new_input}")
#             adjusted_steps = self.adjust_steps(steps, current_idx, new_input, previous_results)
#             return adjusted_steps, True
#         return steps, False

#     def execute(self, steps: list, state: dict) -> dict:
#         """
#         执行任务步骤，使用 ToolAgent 处理工具调用，并依赖前面步骤的结果。
#         :param steps: 任务步骤列表。
#         :param state: 任务状态字典。
#         :return: 任务执行结果。
#         """
#         results = state.get("results", {})
#         current_step = state.get("current_step", 0)

#         for i, step in enumerate(steps[current_step:], current_step):
#             print("----------------------------------")
#             print("----------------------------------")
#             print(f" ** 执行中: {step} [Loading...]")

#             results = str(results)[-10000:]
#             # 判断是否需要工具
#             if self._needs_tool(step, results):
#                 step_result = self._execute_tool_step(step, results)
#             else:
#                 step_result = self._execute_direct_step(step, results)
#             print(f" ** 执行结果：{step_result}")

#             self.step_recorder.record(step, step_result)
#             # 记录结果并更新状态
#             results[step] = step_result
#             state["current_step"] = i + 1

#             state["results"] = results

#             # 处理用户中断
#             steps, interrupted = self._handle_user_interaction(step, step_result, steps, i, results)
#             if interrupted:
#                 state["steps"] = steps
#                 break
#         return results

#     def adjust_steps(self, steps: list, current_idx: int, new_input: str, previous_results: dict) -> list:
#         """
#         根据用户新输入调整后续步骤，考虑前面结果。
#         :param steps: 当前任务步骤列表。
#         :param current_idx: 当前步骤的索引。
#         :param new_input: 用户新输入。
#         :param previous_results: 前面步骤的结果。
#         :return: 调整后的步骤列表。
#         """
#         prompt = (
#             f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
#             f"根据新输入 '{new_input}' 调整后续步骤: {steps[current_idx:]}"
#         )
#         new_steps = self.llm.call(prompt).split("\n")
#         return steps[:current_idx] + [step.strip() for step in new_steps if step.strip()]





# # import time
# # import json
# # from ..services.llm_service import LLMService
# # from AIToolsBridge.core.ToolAgent import ToolAgent
# # from ..core.step_recorder import StepRecorder
# # from typing import Dict
# # import re


# # class TaskExecutor:
# #     def __init__(self, logger, step_recorder: StepRecorder, interaction_handler):
# #         self.agent = ToolAgent(api_key="sk-2dd841cdc2624791bbf114e73e7fec01")
# #         self.logger = logger
# #         self.step_recorder = step_recorder
# #         self.llm = LLMService()
# #         self.interaction_handler = interaction_handler
# #         self.logger.info(f"Registered tools: {self.agent.list_tools()}")

# #     def extract_json_list(self, raw_result: str) -> str:
# #         """Extract the first JSON object ({}) from the raw LLM result."""
# #         pattern = r'\{.*?\}'
# #         matches = re.findall(pattern, raw_result, re.DOTALL)
# #         if matches:
# #             try:
# #                 json.loads(matches[0])  # 验证 JSON 合法性
# #                 return matches[0]
# #             except json.JSONDecodeError:
# #                 print(f"提取的内容不是有效 JSON: {matches[0]}")
# #                 return json.dumps({})
# #         else:
# #             print(f"未能在 LLM 输出中提取 JSON 对象: {raw_result}")
# #             return json.dumps({})

# #     def _needs_tool(self, step: str, previous_results: Dict) -> bool:
# #         """Use LLM to determine if a step requires a tool."""
# #         prompt = (
# #             "Determine whether the following step requires the use of a tool (e.g., search engine, web scraper, API) "
# #             "to complete the action. Return the result as a JSON object with a single key 'needs_tool' and a boolean value:\n"
# #             "Step: '{step}'\n"
# #             "Context (previous results): {context}\n"
# #             "Guidelines:\n"
# #             "- A tool is needed if the step involves external data retrieval (e.g., searching, querying, downloading).\n"
# #             "- No tool is needed if the step can be completed with existing knowledge or simple computation.\n"
# #             "- Consider the context from previous results to assess if the data is already available.\n"
# #             "- Return true or false. in JSON format."
# #         ).format(step=step, context=json.dumps(previous_results))

# #         response = self.llm.call(prompt)
# #         response = self.extract_json_list(response)
# #         print("response!!!!!", response)
# #         try:
# #             result = json.loads(response)
# #             needs_tool = result["needs_tool"]
# #             reason = "需要工具" if needs_tool else "直接回答"
# #             self.step_recorder.record(step, f"LLM 判断：{reason}", reason)
# #             return needs_tool
# #         except (json.JSONDecodeError, KeyError):
# #             # 默认需要工具，记录错误
# #             self.step_recorder.record(step, "LLM 返回无效响应，默认需要工具", "需要工具")
# #             return True

# #     def _execute_tool_step(self, step: str, previous_results: dict) -> str:
# #         """
# #         执行需要工具的步骤。
# #         :param step: 当前步骤的描述。
# #         :param previous_results: 前面步骤的结果。
# #         :return: 工具执行的结果。
# #         """
# #         print(f"  ****  尝试调用使用工具")
# #         try:
# #             start_time = time.time()
# #             query_with_context = (
# #                 f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
# #                 f"执行步骤：{step}"
# #             )
# #             tool_result = self.agent.process_query(query_with_context)
# #             print(f"完成: {step} [耗时: {time.time() - start_time:.2f}s]")
# #             self.step_recorder.record(step, "调用 ToolAgent with context", tool_result)
# #             return tool_result
# #         except Exception as e:
# #             self.logger.error(f"ToolAgent 执行失败: {str(e)}")
# #             return "工具执行失败"

# #     def _execute_direct_step(self, step: str, previous_results: dict) -> str:
# #         """
# #         执行不需要工具的步骤（直接回答）。
# #         :param step: 当前步骤的描述。
# #         :param previous_results: 前面步骤的结果。
# #         :return: LLM 直接回答的结果。
# #         """
# #         prompt = (
# #             f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
# #             f"直接回答: {step}"
# #         )
# #         result = self.llm.call(prompt)
# #         self.step_recorder.record(step, prompt, result)
# #         return result

# #     def _handle_user_interaction(self, step: str, result: str, steps: list, current_idx: int, previous_results: dict) -> tuple[list, bool]:
# #         """
# #         处理用户中断和交互逻辑。
# #         :param step: 当前步骤的描述。
# #         :param result: 当前步骤的执行结果。
# #         :param steps: 当前任务步骤列表。
# #         :param current_idx: 当前步骤的索引。
# #         :param previous_results: 前面步骤的结果。
# #         :return: 返回调整后的步骤列表和是否中断的标志。
# #         """
# #         interrupt, new_input = self.interaction_handler.check_interaction(step, result)
# #         if interrupt:
# #             self.logger.info(f"用户中断任务，输入调整: {new_input}")
# #             adjusted_steps = self.adjust_steps(steps, current_idx, new_input, previous_results)
# #             return adjusted_steps, True
# #         return steps, False

# #     def execute(self, steps: list, state: dict) -> dict:
# #         """
# #         执行任务步骤，使用 ToolAgent 处理工具调用，并依赖前面步骤的结果。
# #         :param steps: 任务步骤列表。
# #         :param state: 任务状态字典。
# #         :return: 任务执行结果。
# #         """
# #         results = state.get("results", {})
# #         current_step = state.get("current_step", 0)

# #         for i, step in enumerate(steps[current_step:], current_step):
# #             print("----------------------------------")
# #             print("----------------------------------")
# #             print(f" ** 执行中: {step} [Loading...]")

# #             # 判断是否需要工具
# #             if self._needs_tool(step, results):
# #                 step_result = self._execute_tool_step(step, results)
# #             else:
# #                 step_result = self._execute_direct_step(step, results)
# #             print(" ** 执行结果：")
# #             print(step_result)
# #             # 记录结果并更新状态
# #             results[step] = step_result
# #             state["current_step"] = i + 1
# #             state["results"] = results

# #             # 处理用户中断
# #             steps, interrupted = self._handle_user_interaction(step, step_result, steps, i, results)
# #             if interrupted:
# #                 state["steps"] = steps
# #                 break

# #         return results

# #     def adjust_steps(self, steps: list, current_idx: int, new_input: str, previous_results: dict) -> list:
# #         """
# #         根据用户新输入调整后续步骤，考虑前面结果。

# #         :param steps: 当前任务步骤列表。
# #         :param current_idx: 当前步骤的索引。
# #         :param new_input: 用户新输入。
# #         :param previous_results: 前面步骤的结果。
# #         :return: 调整后的步骤列表。
# #         """
# #         prompt = (
# #             f"基于以下已有结果：{json.dumps(previous_results, ensure_ascii=False)}\n"
# #             f"根据新输入 '{new_input}' 调整后续步骤: {steps[current_idx:]}"
# #         )
# #         new_steps = self.llm.call(prompt).split("\n")
# #         return steps[:current_idx] + [step.strip() for step in new_steps if step.strip()]