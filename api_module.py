# api_server.py
import requests
from functools import lru_cache
from flask import Flask, request, jsonify

app = Flask(__name__)

@lru_cache(maxsize=128)
def external_api(input_string):
    """
    调用外部 API，接收输入字符串并返回结果。
    """
    try:
        response = requests.get(f"https://api.example.com/data?input={input_string}", timeout=5)
        response.raise_for_status()
        return response.text
    except requests.Timeout:
        return f"错误: API 调用超时 (输入: {input_string})"
    except requests.RequestException as e:
        return f"错误: API 调用失败 - {str(e)} (输入: {input_string})"

@lru_cache(maxsize=128)
def get_final_result(input_string):
    """
    调用外部 API，获取最终处理结果。
    """
    try:
        response = requests.get(f"https://api.example.com/final_result?input={input_string}", timeout=5)
        response.raise_for_status()
        return response.text
    except requests.Timeout:
        return f"错误: 最终结果 API 调用超时 (输入: {input_string})"
    except requests.RequestException as e:
        return f"错误: 最终结果 API 调用失败 - {str(e)} (输入: {input_string})"

# API 端点 1：external_api
@app.route('/external', methods=['GET'])
def external_endpoint():
    input_string = request.args.get('input', '')
    if not input_string:
        return jsonify({"error": "缺少 input 参数"}), 400
    result = external_api(input_string)
    return jsonify({"result": result})

# API 端点 2：get_final_result
@app.route('/final_result', methods=['GET'])
def final_result_endpoint():
    input_string = request.args.get('input', '')
    if not input_string:
        return jsonify({"error": "缺少 input 参数"}), 400
    result = get_final_result(input_string)
    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=True)