from flask import Flask, request, jsonify
from googletrans import Translator

# 初始化 Flask 应用
app = Flask(__name__)

# 初始化翻译器
translator = Translator()

@app.route('/translate', methods=['POST'])
def translate_text():
    """
    翻译 API
    请求体格式：
    {
        "text": "要翻译的文本",
        "src_lang": "源语言代码（可选，默认自动检测）",
        "dest_lang": "目标语言代码（必填）"
    }
    """
    # 获取请求体中的 JSON 数据
    data = request.get_json()

    # 检查必要字段
    if not data or 'text' not in data or 'dest_lang' not in data:
        return jsonify({"error": "Missing required fields: 'text' and 'dest_lang'"}), 400

    text = data['text']
    try:
        dest_lang = data['dest_lang']
    except:
        dest_lang = "zh-cn"
    src_lang = data.get('src_lang', 'auto')  # 如果未提供源语言，则自动检测

    try:
        # 调用翻译器进行翻译
        translated = translator.translate(text, src=src_lang, dest=dest_lang)
        # 返回翻译结果
        return jsonify({
            "original_text": text,
            "translated_text": translated.text,
            "src_lang": translated.src,
            "dest_lang": dest_lang
        })
    except Exception as e:
        print(e)
        # 处理翻译错误
        return jsonify({"error": str(e)}), 500

# 启动 Flask 应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)