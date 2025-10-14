from abc import ABC, abstractmethod
import requests  # 用于调用外部服务，可以根据实际替换为其他通信方式


# 抽象文件处理器
class FileProcessor(ABC):
    @abstractmethod
    def process(self, file_path: str) -> str:
        """处理文件并返回 Markdown 格式的内容"""
        pass


# 具体文件处理器
class PDFProcessor(FileProcessor):
    def process(self, file_path: str, output_dir: str):
        # 调用外部接口,将文件分解成markdown和images
        self._call_pdf2mdAPI(file_path, output_dir)

    def _call_pdf2mdAPI(self, file_path: str, output_dir: str):
        # 调用外部 PDF 处理服务（假设通过 REST API）
        service_url = "http://127.0.0.1:5001/convert_pdf"  # 处理pdf的服务地址
        # 服务会读取本地指定路径 file_path 然后处理后的结果保存到 临时文件夹下
        with open(file_path, 'rb') as f:
            response = requests.post(service_url, files={'file': f})
        if response.status_code == 200:
            print("转换成功，文件已保存")
        else:
            print(f"转换失败: {response.json()}")


class WordProcessor(FileProcessor):
    def process(self, file_path: str, output_dir: str):
        # 调用外部接口,将文件分解成markdown和images
        self._file_to_markdown(file_path, output_dir)

    def _call_word2mdAPI(self, file_path: str, output_dir: str):
        # 调用外部 PDF 处理服务（假设通过 REST API）
        service_url = "http://127.0.0.1:5001/convert_word"  # 处理pdf的服务地址
        # 服务会读取本地指定路径 file_path 然后处理后的结果保存到 临时文件夹下
        with open(file_path, 'rb') as f:
            response = requests.post(service_url, files={'file': f})
        if response.status_code == 200:
            print("转换成功，文件已保存")
        else:
            print(f"转换失败: {response.json()}")


class ImageProcessor(FileProcessor):
    def process(self, file_path: str, output_dir: str):
        # 调用外部接口,将文件分解成markdown和images
        self._file_to_markdown(file_path, output_dir)

    def _call_image2mdAPI(self, file_path: str, output_dir: str):
        # 调用外部 PDF 处理服务（假设通过 REST API）
        service_url = "http://127.0.0.1:5001/convert_Image"  # 处理pdf的服务地址
        # 服务会读取本地指定路径 file_path 然后处理后的结果保存到 临时文件夹下
        with open(file_path, 'rb') as f:
            response = requests.post(service_url, files={'file': f})
        if response.status_code == 200:
            print("转换成功，文件已保存")
        else:
            print(f"转换失败: {response.json()}")