from typing import Dict, Any, List
import json


class ParamHandler:
    def __init__(self, tool_params: List[Dict[str, Any]]):
        """
        参数处理类

        :param tool_params: 工具定义的参数列表（来自 ToolMetaInfo）
        """
        self.tool_params = tool_params
        
    def convert_params(self, user_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换和校验用户提供的参数，支持复合类型如 list[number]。

        :param user_params: 用户提供的原始参数
        :return: 转换后的参数
        """
        result = {}
        param_definitions = {p["name"]: p for p in self.tool_params}

        for name, value in user_params.items():
            if name not in param_definitions:
                continue  # 忽略未定义的参数
            param_def = param_definitions[name]
            param_type = param_def["type"]

            try:
                if isinstance(value, str) and value.startswith("="):
                    value = value[1:]
                # 处理简单类型
                if param_type == "string":
                    # 确保字符串是 UTF-8 编码
                    if isinstance(value, bytes):
                        result[name] = value.decode('utf-8')
                    else:
                        result[name] = str(value).encode('utf-8').decode('utf-8')
                elif param_type == "int":
                    result[name] = int(value)
                elif param_type == "float":
                    result[name] = float(value)
                elif param_type == "binary_file":
                    if isinstance(value, str):  # 假设 value 是文件路径
                        with open(value, "rb") as f:
                            result[name] = f.read()
                    else:
                        result[name] = value  # 直接使用二进制数据
                # 处理复合类型 list[type]
                elif param_type.startswith("list["):
                    inner_type = param_type[5:-1]  # 提取 list 内的类型，如 "number"
                    if not isinstance(value, (list, str)):  # 支持列表或字符串（如 "[1, 2, 3]"）
                        raise ValueError(f"Parameter '{name}' must be a list or string representation of a list")

                    # 如果是字符串，尝试解析为列表
                    if isinstance(value, str):
                        normalised = value.strip()
                        if normalised.startswith("[") and "'" in normalised and '"' not in normalised:
                            normalised = normalised.replace("'", '"')
                        try:
                            value = json.loads(normalised)  # 假设输入是 JSON 格式的字符串
                        except json.JSONDecodeError:
                            raise ValueError(f"Parameter '{name}' string is not a valid list: {value}")

                    if not isinstance(value, list):
                        raise ValueError(f"Parameter '{name}' must be a list after parsing")

                    # 转换列表中的每个元素
                    converted_list = []
                    for item in value:
                        if inner_type == "number":  # 支持 number（int 或 float）
                            if isinstance(item, (int, float)):
                                converted_list.append(item)
                            else:
                                try:
                                    converted_list.append(float(item) if "." in str(item) else int(item))
                                except (ValueError, TypeError):
                                    raise ValueError(f"Item '{item}' in '{name}' cannot be converted to number")
                        elif inner_type == "string":
                            # 处理字符串，确保 UTF-8 编码
                            if isinstance(item, bytes):
                                converted_list.append(item.decode('utf-8'))
                            else:
                                converted_list.append(str(item).encode('utf-8').decode('utf-8'))
                        elif inner_type == "int":
                            converted_list.append(int(item))
                        elif inner_type == "float":
                            converted_list.append(float(item))
                        else:
                            converted_list.append(item)  # 未识别类型，默认不转换
                    result[name] = converted_list
                else:
                    result[name] = value  # 默认不转换
            except Exception as e:
                raise ValueError(f"Failed to convert parameter '{name}' to {param_type}: {str(e)}")

        # 检查必需参数
        for param in self.tool_params:
            if param.get("required", False) and param["name"] not in result:
                raise ValueError(f"Required parameter '{param['name']}' is missing")

        return result

    def validate_params(self, user_params: Dict[str, Any]):
        """
        校验参数是否符合定义

        :param user_params: 用户提供的参数
        """
        param_definitions = {p["name"]: p for p in self.tool_params}
        for param in self.tool_params:
            if param.get("required", False) and param["name"] not in user_params:
                raise ValueError(f"Missing required parameter: {param['name']}")