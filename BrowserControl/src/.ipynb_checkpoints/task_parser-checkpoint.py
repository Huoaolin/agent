from .llm_call import LLMCall
import json
import re
import yaml
import os


class TaskParser:
    def __init__(self):
        self.llm = LLMCall()
        # 加载 YAML 文件中的 prompts
        self.prompts = self.load_prompts()

    def load_prompts(self):
        """从 prompts.yaml 文件加载所有 prompt"""
        yaml_path = os.path.join(os.path.dirname(__file__), "parser_prompts.yaml")
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                prompts = yaml.safe_load(f)
            if not isinstance(prompts, dict):
                raise ValueError("YAML 文件未正确加载为字典")
            if "evaluate_image_task" not in prompts:
                raise KeyError("YAML 文件中缺少 'evaluate_image_task' 键")
            if not isinstance(prompts["evaluate_image_task"], str):
                raise ValueError("'evaluate_image_task' 不是字符串")
            return prompts
        except Exception as e:
            print(f"加载 prompts.yaml 失败: {e}")
            return {}

    def parse(self, user_input):
        # Step 1: Recognize intent
        intent_json = self._recognize_intent(user_input)
        intent_json = json.loads(intent_json)
        intent = intent_json["intent"]
        print("****意图分析****")
        print("intent", intent)
        print("****意图分析****")

        # Step 2: Parse based on intent
        if intent == "text":
            raw_result = self._parse_text_task(user_input)
        elif intent == "image":
            raw_result = self._parse_image_task(user_input)
        else:  # "other"
            raw_result = self._parse_other_task(user_input)

        # Step 3: Extract and refine
        json_list = self.extract_json_list(raw_result, user_input)
        return self.refine_tasks(json_list, user_input)

    def _recognize_intent(self, user_input):
        prompt = self.prompts["recognize_intent"].format(user_input=user_input)
        return self.llm.call(prompt, response_format={"type": "json_object"})

    def _parse_text_task(self, user_input):
        prompt = self.prompts["parse_text_task"].format(user_input=user_input)
        return self.llm.call(prompt, response_format={"type": "json_object"})

    def _parse_image_task(self, user_input):
        prompt = self.prompts["parse_image_task"].format(user_input=user_input)
        return self.llm.call(prompt, response_format={"type": "json_object"})

    def _parse_other_task(self, user_input):
        prompt = self.prompts["parse_other_task"].format(user_input=user_input)
        return self.llm.call(prompt, response_format={"type": "json_object"})

    def evaluate_current_task(self, current_state, current_task):
        """根据任务类型调用对应的评估函数"""
        if current_task["action"] == "extract_text":
            return self._evaluate_text_task(current_state, current_task)
        elif current_task["action"] in ["extract_image"]:
            return self._evaluate_image_task(current_state, current_task)
        else:
            print(f"未知的任务动作: {current_task['action']}，使用默认评估")
            return False, [{"action": "search", "value": current_task["value"], "type": "text", "sub_goal": "retry " + current_task["sub_goal"]}]

    def _evaluate_text_task(self, current_state, current_task):
        prompt = self.prompts["evaluate_text_task"].format(
            current_state=current_state,
            current_task=json.dumps(current_task, ensure_ascii=False)
        )
        raw_result = self.llm.call(prompt, response_format={"type": "json_object"})
        try:
            result_dict = json.loads(raw_result)
            satisfied = result_dict.get("satisfied", False)
            next_tasks = self.refine_tasks(json.dumps(result_dict.get("next_tasks", [])), current_task.get("value", ""))
            return satisfied, next_tasks
        except (json.JSONDecodeError, Exception) as e:
            print(f"文本任务评估失败: {e}")
            return False, [{"action": "search", "value": current_task["value"], "type": "text", "sub_goal": "retry " + current_task["sub_goal"]}]

    def _evaluate_image_task(self, current_state, current_task):
        prompt = str(self.prompts["evaluate_image_task"]).format(
            current_state=str(current_state),
            current_task=str(current_task)
        )
        raw_result = self.llm.call(prompt, response_format={"type": "json_object"})
        try:
            result_dict = json.loads(raw_result)
            satisfied = result_dict.get("satisfied", False)
            next_tasks = self.refine_tasks(json.dumps(result_dict.get("next_tasks", [])), current_task.get("value", ""))
            return satisfied, next_tasks
        except (json.JSONDecodeError, Exception) as e:
            print(f"图片任务评估失败: {e}")
            return False, [{"action": "search", "value": current_task["value"], "type": "image", "sub_goal": "retry " + current_task["sub_goal"]}]

    def evaluate_final_goal(self, user_input, previous_results):
        prompt = self.prompts["evaluate_final_goal"].format(
            user_input=user_input,
            previous_results=json.dumps(previous_results, ensure_ascii=False)
        )
        raw_result = self.llm.call(prompt, response_format={"type": "json_object"})
        try:
            result_dict = json.loads(raw_result)
            satisfied = result_dict.get("satisfied", False)
            next_tasks = self.refine_tasks(json.dumps(result_dict.get("next_tasks", [])), user_input)
            return satisfied, next_tasks
        except (json.JSONDecodeError, Exception) as e:
            print(f"最终目标评估失败: {e}")
            return False, [{"action": "search", "value": user_input, "type": "text", "sub_goal": "retry original request"}]

    async def update_next_task(self, user_input, current_state, current_task, remaining_tasks):
        prompt = self.prompts["update_next_task"].format(
            user_input=user_input,
            current_state=current_state,
            current_task=current_task,
            remaining_tasks=remaining_tasks
        )
        raw_result = self.llm.call(prompt, response_format={"type": "json_object"})
        json_list = self.extract_json_list(raw_result, user_input)
        return self.refine_tasks(json_list, user_input)

    async def retry_task(self, user_input, current_state, current_task):
        prompt = self.prompts["retry_task"].format(
            user_input=user_input,
            current_state=current_state[:500],
            current_task=current_task
        )
        raw_result = self.llm.call(prompt, response_format={"type": "json_object"})
        json_list = self.extract_json_list(raw_result, user_input)
        return self.refine_tasks(json_list, user_input)

    async def replan_tasks(self, user_input, current_state):
        prompt = self.prompts["replan_tasks"].format(
            user_input=user_input,
            current_state=current_state[:500]
        )
        raw_result = self.llm.call(prompt, response_format={"type": "json_object"})
        json_list = self.extract_json_list(raw_result, user_input)
        return self.refine_tasks(json_list, user_input)

    def extract_json_list(self, raw_result, user_input):
        pattern = r'\[.*?\]'
        matches = re.findall(pattern, raw_result, re.DOTALL)
        if matches:
            return matches[0]
        else:
            print(f"未能在 LLM 输出中提取 JSON 列表: {raw_result}")
            return json.dumps([{"action": "search", "value": user_input, "type": "text", "sub_goal": "retry"}])

    def refine_tasks(self, json_list, user_input):
        try:
            tasks = json.loads(json_list)
            if not isinstance(tasks, list):
                raise ValueError("提取的 JSON 不是列表格式")
            valid_actions = {"open_page", "search", "click_element", "extract_text", "extract_image", "take_screenshot", "download_file", "done"}
            valid_types = {"text", "image", "file", None}
            refined_tasks = []
            for task in tasks:
                if not isinstance(task, dict) or "action" not in task or "value" not in task:
                    continue
                refined_task = {
                    "action": task["action"] if task["action"] in valid_actions else "search",
                    "value": str(task["value"]),
                    "type": task.get("type") if task.get("type") in valid_types else None,
                    "sub_goal": task.get("sub_goal", "unknown")
                }
                refined_tasks.append(refined_task)
            return refined_tasks
        except json.JSONDecodeError:
            print(f"JSON 解析失败: {json_list}")
            return [{"action": "search", "value": user_input, "type": "text", "sub_goal": "retry"}]