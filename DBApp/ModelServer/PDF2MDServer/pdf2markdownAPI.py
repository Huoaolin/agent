import os
import subprocess
from flask import Flask, request, send_file, jsonify
import time
import shutil

app = Flask(__name__)

# 配置路径
UPLOAD_FOLDER = './UploadTemp'  # 上传文件临时存储路径
OUTPUT_FOLDER = './OutputTemp'  # 输出文件存储路径
ALLOWED_EXTENSIONS = {'pdf'}  # 允许的文件类型

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_pdf(input_path, output_dir):
    """调用 magic-pdf 转换 PDF，返回生成的输出文件路径"""
    try:
        cmd = ["magic-pdf", "-p", input_path, "-o", output_dir]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        pass
    except subprocess.CalledProcessError as e:
        print(f"转换失败: {e.stderr}")  # 简单错误输出，可替换为日志


def copy_specified_items(source_dir, dest_dir, keep_files, keep_folders):
    """
    将指定的文件和文件夹从 source_dir 复制到 dest_dir
    参数:
        source_dir (str): 源目录路径
        dest_dir (str): 目标目录路径
        keep_files (set): 需要复制的文件名集合
        keep_folders (set): 需要复制的文件夹名集合
    """
    try:
        # 确保目标目录存在
        os.makedirs(dest_dir, exist_ok=True)

        # 递归遍历源目录
        for root, dirs, files in os.walk(source_dir, topdown=False):
            # 复制指定的文件
            for file in files:
                if file in keep_files:
                    src_path = os.path.join(root, file)
                    dest_path = os.path.join(dest_dir, file)
                    shutil.copy2(src_path, dest_path)  # 使用 copy2 保留元数据
                    print(f"复制文件: {src_path} -> {dest_path}")

            # 复制指定的文件夹
            for dir_name in dirs:
                if dir_name in keep_folders:
                    src_path = os.path.join(root, dir_name)
                    dest_path = os.path.join(dest_dir, dir_name)
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)  # 如果目标已存在，先删除
                    shutil.copytree(src_path, dest_path)  # 复制整个文件夹
                    print(f"复制文件夹: {src_path} -> {dest_path}")

    except Exception as e:
        print(f"复制失败: {str(e)}")


def delete_specified_folder(target_dir, folder_name):
    """
    删除指定路径下的特定文件夹
    参数:
        target_dir (str): 目标目录路径
        folder_name (str): 要删除的文件夹名称
    """
    try:
        delete_path = os.path.join(target_dir, folder_name)
        if os.path.isdir(delete_path):
            shutil.rmtree(delete_path)
            print(f"删除文件夹: {delete_path}")
        else:
            print(f"文件夹不存在: {delete_path}")
    except Exception as e:
        print(f"删除失败: {str(e)}")


@app.route('/convert_pdf', methods=['POST'])
def convert_pdf_api():
    """PDF 转换 API 端点"""
    if 'file' not in request.files:
        return jsonify({"error": "未提供文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "仅支持 PDF 文件"}), 400

    if any(c in file.filename for c in ['/', '\\', '..']):
        return jsonify({"error": "文件名包含非法字符"}), 400

    filename = f"{file.filename}"

    file_path = UPLOAD_FOLDER + "/" + filename

    # 执行转换
    convert_pdf(file_path, OUTPUT_FOLDER)

    # 定义路径和参数
    output_dir_df = os.path.join(OUTPUT_FOLDER, filename.rsplit('.', 1)[0])
    os.makedirs(output_dir_df, exist_ok=True)

    SOURCE_DIR = output_dir_df
    DEST_DIR = SOURCE_DIR
    DELETE_FOLDER = "auto"
    md_name = filename.rsplit('.', 1)[0] + ".md"
    KEEP_FILES = {md_name}
    KEEP_FOLDERS = {"images"}

    # 复制指定文件和文件夹并删除指定文件夹
    copy_specified_items(SOURCE_DIR, DEST_DIR, KEEP_FILES, KEEP_FOLDERS)
    delete_specified_folder(DEST_DIR, DELETE_FOLDER)

    return jsonify({"message": "转换成功"}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010, debug=False)