from playwright.async_api import async_playwright
from .task_manager import TaskManager
from .action_result import ActionResult
from bs4 import BeautifulSoup
import re
import asyncio
from .llm_call import LLMCall
import json


class BrowserController:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.observers = []
        self.llm = LLMCall()

    async def start(self):
        self.playwright = await async_playwright().start()
        # 优化浏览器启动：关闭 headless 模式（可选），添加更多反爬配置
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # 可改为 False 用于调试
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1280, "height": 720},  # 设置窗口大小
            java_script_enabled=True,
            ignore_https_errors=True  # 忽略 HTTPS 错误
        )
        self.page = await self.context.new_page()
        # 添加反爬脚本，伪装 webdriver 和其他特性
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)
        print("浏览器初始化成功")
        self.notify_observers("Browser initialized")

    async def open_page(self, url):
        """打开指定 URL，优化加载等待和反爬处理"""
        try:
            # 设置代理（如果需要，需替换为实际代理地址）
            # await self.page.setExtraHTTPHeaders({"Proxy-Server": "http://your_proxy:port"})
            # 增加超时时间并放宽等待条件
            print(f"开始导航到: {url}")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)  # 从 networkidle 改为 domcontentloaded
            await self.page.wait_for_load_state("domcontentloaded")  # 确保 DOM 加载完成
            # 检查是否遇到验证码或登录页面
            content = await self.page.content()
            if "验证码" in content or "login.taobao.com" in self.page.url:
                print("检测到验证码或登录页面，尝试等待手动处理或调整策略")
                await asyncio.sleep(5)  # 短暂等待，观察是否可加载
                content = await self.page.content()  # 重新获取内容
            current_url = self.page.url
            title = await self.page.title()
            msg = f"🔗  Navigated to {url} (Loaded URL: {current_url}, Title: {title})"
            self.notify_observers(msg)
            return content
        except Exception as e:
            error_msg = f"执行任务 open_page 时出错: {e}"
            self.notify_observers(error_msg)
            print(f"错误详情: {e}")
            print(f"当前页面内容: {content[:200] if 'content' in locals() else '未加载'}")
            raise Exception(error_msg)

    async def search(self, query):
        """在当前页面执行搜索，支持百度或淘宝"""
        try:
            current_url = self.page.url if self.page.url else "https://www.taobao.com"
            if "baidu.com" in current_url:
                await self.page.goto("https://www.baidu.com", wait_until="domcontentloaded", timeout=60000)
                await self.page.fill("input#kw", query)
                await self.page.press("input#kw", "Enter")
                await self.page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2)  # 等待动态内容
                msg = f"🔍  Searched for '{query}' on Baidu"
            elif "taobao.com" in current_url:
                await self.page.fill("input#q", query)  # 淘宝搜索框
                await self.page.press("input#q", "Enter")
                await self.page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2)
                msg = f"🔍  Searched for '{query}' on Taobao"
            else:
                await self.page.goto(f"https://www.google.com/search?q={query}&udm=14", wait_until="domcontentloaded", timeout=60000)
                msg = f"🔍  Searched for '{query}' on Google"
            self.notify_observers(msg)
            return await self.page.content()
        except Exception as e:
            error_msg = f"Search failed for '{query}': {str(e)}"
            self.notify_observers(error_msg)
            raise Exception(error_msg)

    async def click_element(self, selector):
        """点击指定元素，添加可见性检查"""
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=30000)
            await self.page.locator(selector).click()
            msg = f"🖱️  Clicked element: {selector}"
            self.notify_observers(msg)
            await self.page.wait_for_load_state("domcontentloaded")
            return await self.page.content()
        except Exception as e:
            error_msg = f"Click element failed for '{selector}': {str(e)}"
            self.notify_observers(error_msg)
            raise Exception(error_msg)

    async def extract_text(self, query):
        """使用规则函数预处理 HTML，再由 LLM 提取与 query 相关的信息"""
        try:
            html_content = await self.page.content()
            if not html_content:
                error_msg = "Page content is empty"
                self.notify_observers(error_msg)
                return error_msg

            structured_text = await self._extract_structured_text(html_content)
            self.notify_observers(f"📋  Structured text extracted: {structured_text[:200]}...")

            prompt = f"""
            从以下结构化网页内容中提取与 '{query}' 相关的信息。
            - 查询内容可能是任何类型的信息，请根据上下文尽可能提取相关内容。
            - 如果查询包含具体对象，即使内容中未明确提及该对象，只要信息在上下文中合理相关，也应提取。
            - 返回提取到的信息，可以是简洁的文本或按类别组织的键值对，具体格式根据内容自然选择。
            返回一个 JSON 对象，包含以下字段：
            - "result": 提取到的信息（字符串或字典）
            - "status": "success" 或 "error"
            如果找不到相关信息，返回 "未找到相关信息"。
            结构化内容：
            {structured_text}
            """
            if asyncio.iscoroutinefunction(self.llm.call):
                raw_response = await self.llm.call(prompt, response_format={"type": "json_object"})
            else:
                raw_response = self.llm.call(prompt, response_format={"type": "json_object"})

            self.notify_observers(f"📝  LLM raw response: {raw_response}")
            if isinstance(raw_response, str):
                response = json.loads(raw_response)
            else:
                response = raw_response

            if response.get("status") == "success":
                # 将 query 和提取结果包装为字典
                extracted_result = response.get("result", "未找到相关信息")
                result = {
                    "query": query,
                    "extracted": extracted_result
                }
            else:
                result = "未找到相关信息"  # 失败时保持原逻辑

            self.notify_observers(f"📝  LLM extracted: {result}")
            return result
        except Exception as e:
            error_msg = f"Failed to extract text with LLM for '{query}': {str(e)}"
            self.notify_observers(error_msg)
            return error_msg

    async def extract_image(self, query):
        n = 3
        """从页面中提取与 query 最相关的 N 个图片 URL 和标题对"""
        try:
            # 获取当前页面完整内容
            html_content = await self.page.content()
            if not html_content:
                error_msg = "Page content is empty"
                self.notify_observers(error_msg)
                return error_msg

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            image_title_pairs = []
            # 查找所有带有 class="cos-image-body" 的图片
            for img in soup.find_all('img', class_='cos-image-body'):
                src = img.get('src')
                alt = img.get('alt', '')
                if src and src.startswith('http'):  # 只保留有效的图片 URL
                    # 查找最近的标题（class="cosc-title-slot"）
                    title_tag = img.find_next('span', class_='cosc-title-slot')
                    title = ""
                    if title_tag:
                        inner_span = title_tag.find('span')
                        title = inner_span.get_text(strip=True) if inner_span else title_tag.get_text(strip=True)
                    image_title_pairs.append({
                        "url": src,
                        "alt": alt,
                        "title": title if title else "无标题",
                        "context": self._get_image_context(img, soup)
                    })
            if not image_title_pairs:
                error_msg = "No image-title pairs found on the page"
                self.notify_observers(error_msg)
                return error_msg
            # 将图片-标题对信息传递给 LLM
            pairs_json = json.dumps(image_title_pairs, ensure_ascii=False)
            self.notify_observers(f"🖼️  Image-title pairs extracted: {pairs_json[:200]}...")
            self.notify_observers(f"🖼️ *************DEBUG*************")
            self.notify_observers(f"🖼️ {pairs_json}")
            self.notify_observers(f"🖼️ *************DEBUG*************")
            # 修改 prompt，要求返回 N 个相关图片
            prompt = f"""
            从以下页面中提取的图片-标题对信息中，找出与 '{query}' 最相关的 {n} 张图片。
            - 查询内容可能是任何类型的信息，请根据图片的 URL、alt 属性、标题或周围上下文，判断哪些图片最符合查询意图。
            - 如果查询包含具体对象，即使信息中未明确提及该对象，只要标题或上下文合理相关，也应选择相关图片。
            - 返回一个 JSON 对象，包含以下字段：
            - "results": 一个列表，每个元素包含：
              - "url": 图片的 URL（字符串）
              - "title": 图片的标题（字符串）
            - "status": "success" 或 "error"
            - 如果相关图片少于 {n} 张，返回所有相关图片；如果没有相关图片，返回空列表。
            图片-标题对信息：
            {pairs_json}
            """
            if asyncio.iscoroutinefunction(self.llm.call):
                raw_response = await self.llm.call(prompt, response_format={"type": "json_object"})
            else:
                raw_response = self.llm.call(prompt, response_format={"type": "json_object"})

            self.notify_observers(f"📝  LLM raw response: {raw_response}")
            if isinstance(raw_response, str):
                response = json.loads(raw_response)
            else:
                response = raw_response

            if response.get("status") == "success":
                # 提取 LLM 返回的图片列表
                results_list = response.get("results", [])
                # 转换为所需的格式
                result = {
                    "query": query,
                    "images": [
                        {"extracted": item["url"], "title": item["title"]}
                        for item in results_list
                    ]
                }
            else:
                result = {
                    "query": query,
                    "images": []  # 如果失败，返回空列表
                }
            self.notify_observers(f"🖼️  LLM extracted image-title pairs: {result}")
            return result
        except Exception as e:
            error_msg = f"Failed to extract images with LLM for '{query}': {str(e)}"
            self.notify_observers(error_msg)
            return error_msg

    def _get_image_context(self, img_tag, soup):
        """从更宽泛的范围内提取图片的上下文文本（保留原有逻辑）"""
        context = ""
        alt_text = img_tag.get('alt', '').strip()
        if alt_text:
            context += alt_text + " "
        parent = img_tag.parent
        if parent:
            parent_text = parent.get_text(strip=True)
            if parent_text and len(parent_text) > len(context):
                context = parent_text
            for sibling in parent.find_previous_siblings()[:2]:
                sibling_text = sibling.get_text(strip=True)
                if sibling_text:
                    context += " " + sibling_text
            for sibling in parent.find_next_siblings()[:2]:
                sibling_text = sibling.get_text(strip=True)
                if sibling_text:
                    context += " " + sibling_text
        if len(context) < 20 and parent:
            grandparent = parent.parent
            if grandparent:
                grandparent_text = grandparent.get_text(strip=True)
                if grandparent_text:
                    context = grandparent_text
        for ancestor in img_tag.find_parents():
            if ancestor.name in ['h1', 'h2', 'h3', 'p', 'div', 'article']:
                ancestor_text = ancestor.get_text(strip=True)
                if ancestor_text and len(ancestor_text) > len(context):
                    context = ancestor_text
                break
        return context.strip() if context else "无上下文信息"

    async def find_most_relevant_link(self, query, previous_state=None):
        """找到页面中最相关的链接 URL，基于 previous_state 或当前页面"""
        try:
            html_content = previous_state if previous_state else await self.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            links = []
            for a_tag in soup.find_all('a', href=True):
                link_text = a_tag.get_text(strip=True)
                href = a_tag['href']
                if link_text and href and href.startswith('http'):
                    links.append({"text": link_text, "url": href})
            if not links:
                self.notify_observers("🔗  No valid links found")
                return None

            prompt = f"""
            Given the query: '{query}',
            and the following list of links with their text:
            {json.dumps(links, ensure_ascii=False, indent=2)},
            determine which link is most relevant to the query.
            Return a JSON object with:
            - "url": the most relevant URL (or null if none is relevant)
            - "reason": a brief explanation of the choice
            """
            if asyncio.iscoroutinefunction(self.llm.call):
                raw_response = await self.llm.call(prompt, response_format={"type": "json_object"})
            else:
                raw_response = self.llm.call(prompt, response_format={"type": "json_object"})

            self.notify_observer(f"🔗  LLM raw response for link selection: {raw_response}")
            if isinstance(raw_response, str):
                response = json.loads(raw_response)
            else:
                response = raw_response

            relevant_url = response.get("url")
            reason = response.get("reason", "No reason provided")
            if relevant_url:
                self.notify_observers(f"🔗  Most relevant link found: {relevant_url} ({reason})")
                return relevant_url
            else:
                self.notify_observers(f"🔗  No relevant link found: {reason}")
                return None
        except Exception as e:
            error_msg = f"Failed to find relevant link for '{query}': {str(e)}"
            self.notify_observers(error_msg)
            return None

    async def _extract_structured_text(self, html_content):
        """从 HTML 中提取自然语言文字信息，保留配置相关内容"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for tag in soup(['script', 'style', 'noscript', 'footer', 'nav', 'meta', 'link', 'head']):
                tag.decompose()

            extracted_text = []
            content_containers = soup.find_all(['div', 'section', 'article', 'ul', 'li', 'p', 'span', 'td'])

            text_pattern = re.compile(r'^[\w\s.,;:!?¥%-®™/\(\)=+]+$', re.UNICODE)
            code_pattern = re.compile(r'[<{][^>]+>|http[s]?://|\b(var|function|json|script)\b', re.I)

            for container in content_containers:
                text = container.get_text(strip=True)
                if (text and len(text) > 2 and
                    text_pattern.match(text) and
                    not code_pattern.search(text) and
                    text not in extracted_text):
                    extracted_text.append(text)

            if extracted_text:
                structured_text = "\n".join(extracted_text)
            else:
                structured_text = "未找到相关信息"
            return structured_text
        except Exception as e:
            self.notify_observers(f"Failed to extract structured text: {str(e)}")
            return f"提取结构化文本失败: {str(e)}"

    async def take_screenshot(self, filename):
        """截取屏幕截图"""
        path = f"{TaskManager().get_task_dir()}/{filename}"
        await self.page.screenshot(path=path)
        msg = f"📸  Screenshot saved to: {path}"
        self.notify_observers(msg)
        return path

    async def download_file(self, url, filename):
        """下载文件"""
        async with self.page.expect_download() as download_info:
            await self.page.goto(url)
        download = await download_info.value
        path = f"{TaskManager().get_task_dir()}/{filename}"
        await download.save_as(path)
        self.notify_observers(f"💾  Downloaded file to: {path}")
        return path

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.notify_observers("Browser closed")

    def add_observer(self, observer):
        self.observers.append(observer)

    def notify_observers(self, event):
        for observer in self.observers:
            observer.update(event)
