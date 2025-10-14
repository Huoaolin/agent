# tools/scripts/string_length.py

import sys
import json


def calculate_string_length(input_str) -> int:
    
    """
    计算字符串的长度

    :param input_str: 输入的字符串
    :return: 字符串的长度
    """
    # input_str = input_dic.get("text", "")
    return len(input_str)


if __name__ == "__main__":
    # 从命令行参数中获取输入
    try:
        # 解析 JSON 格式的输入
        
        input_data = json.loads(sys.argv[1])
        input_str = input_data.get("text", "")

        # 计算字符串长度
        length = calculate_string_length(input_str)

        # 返回结果
        result = {"length": length}
        print(json.dumps(result))
    except Exception as e:
        # 处理错误
        error_result = {"error": str(e)}
        print(json.dumps(error_result))