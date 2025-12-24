import hashlib
import json
import random
import sys
import requests
import hashlib
import random
from PyQt6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMessageBox, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QTextEdit, 
                           QLabel, QLineEdit, QTabWidget, QComboBox, QDateTimeEdit,
                           QProgressBar, QStatusBar, QSplitter, QDialog, QCheckBox, QSlider, QDateEdit)
from PyQt6.QtCore import Qt, QDateTime, QTimer, QDate
from PyQt6.QtGui import QIcon, QColor, QClipboard
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
import xml.etree.ElementTree as ET
from datetime import datetime

# 导入数据库处理类
try:
    from DatabaseHandler import DatabaseHandler
except ImportError:
    # 如果直接导入失败，尝试通过修改sys.path导入
    import os
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from DatabaseHandler import DatabaseHandler

# 检查PyQt6是否正确安装
# 检查PyQt6是否正确安装
# 检查PyQt6是否正确安装
try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QPushButton, QListWidget, QTextEdit, 
                                QLabel, QLineEdit, QTabWidget, QComboBox, QDateTimeEdit,
                                QProgressBar, QStatusBar, QSplitter)
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon, QColor
except ImportError as e:
    print(f"导入PyQt6时出错: {e}")
    print("请确保已正确安装PyQt6:")
    print("pip install PyQt6")
    sys.exit(1)

# ---------------------- RSS新闻处理器 ----------------------
class NewsAPIHandler:
    def __init__(self):
        # RSS源地址 (修正后的正确地址)
        self.rss_sources = {
            "央视新闻": "https://news.cctv.com/2019/07/gaiban/cmsdata/index.xml",
            "人民日报": "http://www.people.com.cn/rss/politics.xml",
            "澎湃新闻": "https://www.thepaper.cn/list_news_xml.jsp?channelIDs=25949&dateType=0&count=20"
        }
        self.category_map = {
            "business": "财经", "technology": "科技", "science": "科技",
            "health": "健康", "sports": "体育", "entertainment": "娱乐",
            "general": "国际", "politics": "国际"
        }

    def get_top_headlines(self, source="all"):
        """获取指定RSS源的新闻"""
        print(f"开始获取新闻，源: {source}")
        all_news = []
        
        if source == "all":
            sources_to_fetch = list(self.rss_sources.items())
        else:
            if source in self.rss_sources:
                sources_to_fetch = [(source, self.rss_sources[source])]
            else:
                print(f"未知的新闻源: {source}")
                return []
        
        print(f"将要获取 {len(sources_to_fetch)} 个新闻源")
        for source_name, rss_url in sources_to_fetch:
            try:
                print(f"正在获取 {source_name} 的新闻: {rss_url}")
                news_list = self._fetch_rss_news(rss_url, source_name)
                print(f"从 {source_name} 获取到 {len(news_list)} 条新闻")
                all_news.extend(news_list)
            except Exception as e:
                error_msg = f"获取 {source_name} 新闻时出错: {str(e)}"
                print(error_msg)
                # 即使某个源出错也继续处理其他源
                
        print(f"总共获取到 {len(all_news)} 条新闻")
        return all_news

    def search_news(self, keyword, start_date, end_date, language="zh"):
        """搜索新闻（在RSS新闻中进行过滤）"""
        # 对于RSS源，我们获取所有新闻然后进行关键词过滤
        all_news = self.get_top_headlines()
        
        # 根据关键词过滤
        if keyword:
            filtered_news = [news for news in all_news if 
                            keyword.lower() in news["title"].lower() or 
                            keyword.lower() in news["summary"].lower() or
                            keyword.lower() in news["content"].lower()]
        else:
            filtered_news = all_news
            
        return filtered_news

    def test_rss_feeds(self):
        """测试所有RSS源是否可用"""
        results = {}
        for source_name, rss_url in self.rss_sources.items():
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(rss_url, timeout=10, headers=headers)
                response.raise_for_status()
                results[source_name] = {
                    'status': 'success',
                    'content_length': len(response.text),
                    'status_code': response.status_code
                }
            except Exception as e:
                results[source_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
        return results

    def _fetch_rss_news(self, rss_url, source_name):
        """获取并解析RSS新闻"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(rss_url, timeout=15, headers=headers)
            response.raise_for_status()  # 检查HTTP错误
            response.encoding = response.apparent_encoding or 'utf-8'  # 自动检测编码
            
            # 如果内容为空，抛出异常
            if not response.text or len(response.text) < 20:
                raise Exception("收到空的或过短的响应内容")
            
            # 解析XML
            root = ET.fromstring(response.text)
            
            news_list = []
            # 尝试不同的item查找方式
            items = root.findall('.//item')
            if not items:
                items = root.findall('item')
            if not items:
                items = root.findall('.//entry')  # Atom格式
            if not items:
                # 如果还找不到，尝试遍历所有子节点
                items = [elem for elem in root if elem.tag and 'item' in elem.tag.lower()]
                if not items:
                    items = [elem for elem in root if elem.tag and 'entry' in elem.tag.lower()]
            
            # 如果仍然没有找到任何项，记录响应内容用于调试
            if not items:
                print(f"警告: 在 {rss_url} 中未找到任何新闻项")
                print(f"响应内容前500字符: {response.text[:500]}")
            
            # 限制最多处理20条新闻
            items = items[:20]
            
            successful_items = 0
            for item in items:
                try:
                    # 尝试多种可能的元素名称
                    title_elem = item.find('title')
                    title = title_elem.text if title_elem is not None and hasattr(title_elem, 'text') and title_elem.text else "无标题"
                    
                    description_elem = item.find('description')
                    if description_elem is None:
                        description_elem = item.find('content')
                    if description_elem is None:
                        description_elem = item.find('summary')
                    if description_elem is None:
                        description_elem = item.find('.//description')
                    
                    description = ""
                    if description_elem is not None:
                        if hasattr(description_elem, 'text') and description_elem.text:
                            description = description_elem.text
                        elif hasattr(description_elem, 'itertext'):
                            # 对于包含HTML标签的描述，提取纯文本
                            description = ''.join(description_elem.itertext())
                    
                    # 尝试多种方式获取链接
                    link_elem = item.find('link')
                    link = ""
                    if link_elem is not None:
                        if hasattr(link_elem, 'text') and link_elem.text:
                            link = link_elem.text
                        elif link_elem.get('href'):  # Atom格式
                            link = link_elem.get('href')
                        elif link_elem.get('rel') == 'alternate' and link_elem.get('href'):
                            link = link_elem.get('href')
                    
                    # 如果link元素没有文本值，尝试获取其属性
                    if not link and link_elem is not None:
                        link = link_elem.get('href') or link_elem.get('url') or ""
                    
                    # 处理日期
                    pub_date_elem = item.find('pubDate')
                    if pub_date_elem is None:
                        pub_date_elem = item.find('published')
                    if pub_date_elem is None:
                        pub_date_elem = item.find('updated')
                    if pub_date_elem is None:
                        pub_date_elem = item.find('.//pubDate')
                    
                    pub_date_str = ""
                    if pub_date_elem is not None:
                        if hasattr(pub_date_elem, 'text') and pub_date_elem.text:
                            pub_date_str = pub_date_elem.text
                        else:
                            # 尝试获取属性
                            pub_date_str = pub_date_elem.get('datetime') or ""
                    
                    # 解析发布日期
                    publish_time = QDateTime.currentDateTime()  # 默认值
                    if pub_date_str:
                        try:
                            # 尝试多种日期格式
                            date_formats = [
                                '%a, %d %b %Y %H:%M:%S %z',
                                '%a, %d %b %Y %H:%M:%S %Z',
                                '%Y-%m-%d %H:%M:%S',
                                '%Y年%m月%d日 %H:%M',
                                '%Y-%m-%dT%H:%M:%SZ',
                                '%Y-%m-%dT%H:%M:%S.%fZ',
                                '%Y-%m-%d',
                                '%Y/%m/%d %H:%M:%S',
                                '%Y-%m-%dT%H:%M:%S',
                                '%d %b %Y %H:%M:%S %z',
                                '%d %B %Y %H:%M:%S',
                                '%m/%d/%Y %H:%M:%S'
                            ]
                            
                            for fmt in date_formats:
                                try:
                                    parsed_date = datetime.strptime(pub_date_str, fmt)
                                    publish_time = QDateTime.fromString(
                                        parsed_date.strftime('%Y-%m-%d %H:%M:%S'), 
                                        'yyyy-MM-dd HH:mm:ss'
                                    )
                                    break
                                except ValueError:
                                    continue
                        except Exception as date_error:
                            print(f"日期解析错误: {date_error}")
                    
                    # 计算热度得分（根据发布时间计算）
                    time_diff = QDateTime.currentDateTime().secsTo(publish_time) * -1
                    hot_score = max(0, 100 - min(time_diff // 3600, 100))
                    
                    # 清理标题和描述中的多余空白字符
                    clean_title = " ".join(title.split()) if title else "无标题"
                    clean_description = " ".join(description.split()) if description else "无摘要"
                    
                    news_item = {
                        "title": clean_title,
                        "category": self._categorize_news(clean_title, clean_description),
                        "summary": clean_description,
                        "content": clean_description,
                        "source": source_name,
                        "time": publish_time,
                        "hot_score": hot_score,
                        "url": link,
                        "country": "cn"  # 所有RSS源都是国内媒体
                    }
                    
                    news_list.append(news_item)
                    successful_items += 1
                    
                except Exception as item_error:
                    print(f"解析RSS项时出错: {str(item_error)}")
                    continue
            
            print(f"成功解析 {source_name} 的 {successful_items} 条新闻")
            return news_list
            
        except requests.RequestException as e:
            raise Exception(f"网络请求错误 [{rss_url}]: {str(e)}")
        except ET.ParseError as e:
            raise Exception(f"XML解析错误 [{rss_url}]: {str(e)}")
        except Exception as e:
            raise Exception(f"获取RSS新闻时出错 [{rss_url}]: {str(e)}")

    def _categorize_news(self, title, description):
        """根据标题和描述对新闻进行分类"""
        content = (title + description).lower()
        
        if any(word in content for word in ['科技', '技术', '互联网', '手机', '电脑', '软件', '硬件', '数码']):
            return "科技"
        elif any(word in content for word in ['经济', '财经', '股市', '投资', '金融', '银行', '货币', '财政', '商业']):
            return "财经"
        elif any(word in content for word in ['体育', '足球', '篮球', '比赛', '运动员', '奥运', '联赛', '冠军']):
            return "体育"
        elif any(word in content for word in ['娱乐', '明星', '电影', '音乐', '电视剧', '综艺']):
            return "娱乐"
        elif any(word in content for word in ['健康', '医疗', '疾病', '医生', '药物', '疫情', '疫苗']):
            return "健康"
        elif any(word in content for word in ['教育', '学校', '学生', '考试', '大学', '学习']):
            return "教育"
        elif any(word in content for word in ['国际', '国外', '美国', '欧洲', '亚洲', '联合国']):
            return "国际"
        else:
            return "综合"

    def _check_response(self, response):
        """检查API响应是否正常"""
        pass  # RSS不需要此方法

    def _parse_news(self, raw_data):
        """解析API返回的原始数据为程序内部格式"""
        pass  # RSS不需要此方法

# ---------------------- 任务编辑对话框 ----------------------
class TaskEditDialog(QDialog):
    """任务编辑对话框，允许设置提醒时间和备注"""
    def __init__(self, task_name="", parent=None):
        super().__init__(None)
        self.setWindowTitle("任务设置")
        self.setFixedSize(400, 300)
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        layout = QVBoxLayout()
        
        # 任务名称
        layout.addWidget(QLabel("任务名称:"))
        self.task_name_edit = QLineEdit(task_name)
        layout.addWidget(self.task_name_edit)
        
        # 备注
        layout.addWidget(QLabel("备注:"))
        self.task_note_edit = QTextEdit()
        self.task_note_edit.setMaximumHeight(100)
        layout.addWidget(self.task_note_edit)
        
        # 提醒时间设置
        layout.addWidget(QLabel("提醒时间 (可选):"))
        self.reminder_time = QDateTimeEdit()
        self.reminder_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.reminder_time.setMinimumDateTime(QDateTime.currentDateTime())
        self.reminder_time.setSpecialValueText("不设置提醒")
        self.no_reminder_checkbox = QCheckBox("不设置提醒")
        self.no_reminder_checkbox.setChecked(True)
        self.reminder_time.setEnabled(False)
        layout.addWidget(self.no_reminder_checkbox)
        layout.addWidget(self.reminder_time)
        
        # 连接信号
        self.no_reminder_checkbox.stateChanged.connect(self.toggle_reminder)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def toggle_reminder(self, state):
        self.reminder_time.setEnabled(state == 0)
    
    def get_task_info(self):
        return {
            "name": self.task_name_edit.text().strip(),
            "note": self.task_note_edit.toPlainText().strip(),
            "reminder_time": self.reminder_time.dateTime() if not self.no_reminder_checkbox.isChecked() else None
        }

# ---------------------- 基础对话框基类 ----------------------
class BaseIndependentDialog(QDialog):
    """独立对话框基类：支持独立运行、置顶、最小化"""
    def __init__(self, title, parent_ref=None):
        super().__init__(None)
        self.parent_ref = parent_ref  # 主窗口引用（非父对象）
        self.setWindowTitle(title)
        self.on_top = False  # 置顶状态
        self.is_closed = False  # 关闭状态
        
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题栏（含置顶/最小化/关闭按钮）
        self._init_title_bar()
        
        self.setLayout(self.main_layout)
    
    def _init_title_bar(self):
        """初始化标题栏：标题 + 窗口控制按钮"""
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel(self.windowTitle()))
        title_layout.addStretch()
        
        # 控制按钮
        self.min_btn = QPushButton("—")
        self.top_btn = QPushButton("□")  # 置顶按钮（□=未置顶，▣=已置顶）
        self.close_btn = QPushButton("×")
        
        # 按钮样式
        for btn in [self.min_btn, self.top_btn, self.close_btn]:
            btn.setFixedSize(25, 25)
            btn.setStyleSheet("""
                QPushButton { background: transparent; border: none; font-weight: bold; }
                QPushButton:hover { background: #d0d0d0; border-radius: 3px; }
            """)
        
        # 绑定事件
        self.min_btn.clicked.connect(self.showMinimized)
        self.top_btn.clicked.connect(self._toggle_stay_on_top)
        self.close_btn.clicked.connect(self.close)
        
        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.top_btn)
        title_layout.addWidget(self.close_btn)
        self.main_layout.addLayout(title_layout)
    
    def _toggle_stay_on_top(self):
        """切换置顶状态"""
        if self.on_top:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            self.top_btn.setText("□")
            self.top_btn.setToolTip("设置窗口置顶")
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.top_btn.setText("▣")
            self.top_btn.setToolTip("取消窗口置顶")
        
        self.on_top = not self.on_top
        self.show()
        self.activateWindow()
    
    def closeEvent(self, event):
        """对话框关闭时处理"""
        self.is_closed = True
        if self.parent_ref and hasattr(self.parent_ref, 'open_dialogs'):
            if self in self.parent_ref.open_dialogs:
                self.parent_ref.open_dialogs.remove(self)
            if not self.parent_ref.open_dialogs and not self.parent_ref.isVisible():
                QApplication.instance().quit()
        event.accept()

# ---------------------- 有道翻译API处理器 ----------------------
class YoudaoTranslateAPI:
    """有道灵动翻译API处理器（修复类型错误）"""
    def __init__(self, app_key, app_secret):
        self.app_key = app_key  # 替换为你的有道应用ID
        self.app_secret = app_secret  # 替换为你的有道应用密钥
        self.url = "https://openapi.youdao.com/api"
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}

    def _truncate(self, text):
        """截断文本（符合有道API要求）"""
        if len(text) > 20:
            return text[:10] + str(len(text)) + text[-10:]
        return text

    def _get_error_message(self, error_code):
        """有道翻译错误码对应消息"""
        error_map = {
            "0": "成功",
            "101": "缺少必填参数",
            "102": "不支持的语言类型",
            "103": "翻译文本过长",
            "104": "应用ID或密钥错误（未授权）",
            "105": "签名错误",
            "106": "无权限使用该服务",
            "107": "服务器繁忙",
            "108": "应用已过期",
            "109": "访问频率受限",
            "110": "账户余额不足"
        }
        return error_map.get(error_code, f"未知错误({error_code})")

    def translate(self, text, from_lang="auto", to_lang="zh-CHS"):
        """调用有道翻译API（修复类型错误）"""
        if not text.strip():
            return "请输入需要翻译的文本"

        # 生成签名参数
        import time
        import uuid
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        sign_str = self.app_key + self._truncate(text) + salt + curtime + self.app_secret
        sign = hashlib.sha256(sign_str.encode()).hexdigest()

        params = {
            "q": text,
            "from": from_lang,
            "to": to_lang,
            "appKey": self.app_key,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime
        }

        try:
            response = requests.post(self.url, data=params, headers=self.headers, timeout=10)
            result = response.json()
            # 打印API原始返回（调试用，可注释）
            print("有道API原始返回:", json.dumps(result, ensure_ascii=False))

            # 处理API错误
            if result.get("errorCode") != "0":
                return f"翻译失败: {self._get_error_message(result['errorCode'])}"

            # 修复核心：兼容返回结构
            translations = []
            translation_data = result.get("translation")
            if not translation_data:
                return "翻译失败: 未获取到有效结果"

            # 兼容"字符串列表"或"字典列表"
            if isinstance(translation_data, list):
                for item in translation_data:
                    if isinstance(item, dict) and "tgt" in item:
                        translations.append(item["tgt"])
                    elif isinstance(item, str):
                        translations.append(item)
            elif isinstance(translation_data, str):
                translations.append(translation_data)

            if not translations:
                return "翻译失败: 未解析到有效内容"
            return "\n".join(translations)

        except requests.exceptions.Timeout:
            return "翻译请求超时，请检查网络"
        except Exception as e:
            print(f"翻译异常: {str(e)}")
            return f"翻译出错: {str(e)}"

    def _mock_translate(self, text):
        """翻译新闻内容（使用有道翻译API）"""
        content = self.news['content']
        if not content:
            QMessageBox.warning(self, "提示", "没有可翻译的内容")
            return
            
        # 检查是否已经是中文
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
        if has_chinese:
            reply = QMessageBox.question(self, "确认", "内容似乎包含中文，是否仍要翻译？", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 显示翻译中状态
        self.translate_btn.setText("翻译中...")
        self.translate_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            # 调用有道翻译API
            translated_text = self.translator.translate(content)
            if "翻译失败" not in translated_text and "翻译出错" not in translated_text:
                # 显示翻译区域
                self.translation_label.show()
                self.translation_text.show()
                self.translation_text.setPlainText(translated_text)
                
                # 调整窗口大小
                self.resize(700, 700)
            else:
                QMessageBox.warning(self, "翻译失败", translated_text)
        except Exception as e:
            QMessageBox.critical(self, "翻译错误", f"翻译过程中发生错误：{str(e)}")
        finally:
            # 恢复按钮状态
            self.translate_btn.setText("翻译")
            self.translate_btn.setEnabled(True)
    
    def _mock_translate(self, text):
        """保留原有的模拟翻译功能作为备用"""
        # 这里只是一个示例翻译，实际应该调用翻译API如有道翻译、谷歌翻译等
        translations = {
            "The": "这",
            "a": "一个",
            "an": "一个",
            "and": "和",
            "of": "的",
            "to": "到",
            "in": "在",
            "is": "是",
            "are": "是",
            "was": "曾经是",
            "were": "曾经是",
            "be": "是",
            "been": "被",
            "have": "有",
            "has": "有",
            "had": "有",
            "do": "做",
            "does": "做",
            "did": "做",
            "will": "将",
            "would": "将",
            "could": "可以",
            "should": "应该",
            "may": "可能",
            "might": "可能",
            "must": "必须",
            "can": "可以",
            "new": "新的",
            "latest": "最新的",
            "recent": "最近的",
            "today": "今天",
            "yesterday": "昨天",
            "report": "报告",
            "research": "研究",
            "study": "研究",
            "findings": "发现",
            "results": "结果",
            "show": "显示",
            "indicate": "表明",
            "suggest": "建议",
            "reveal": "揭示",
            "discover": "发现",
            "announce": "宣布",
            "say": "说",
            "tell": "告诉",
            "according": "根据",
            "scientists": "科学家",
            "researchers": "研究人员",
            "experts": "专家",
            "officials": "官员",
            "government": "政府",
            "company": "公司",
            "people": "人们",
            "world": "世界",
            "global": "全球",
            "international": "国际",
            "national": "国家",
            "local": "当地",
            "market": "市场",
            "economy": "经济",
            "financial": "金融",
            "economic": "经济",
            "political": "政治",
            "social": "社会",
            "environmental": "环境",
            "health": "健康",
            "technology": "技术",
            "science": "科学",
            "sports": "体育",
            "entertainment": "娱乐",
            "culture": "文化"
        }
        
        # 简单的单词替换翻译（仅为演示）
        words = text.split()
        translated_words = []
        for word in words:
            # 移除标点符号进行匹配
            clean_word = ''.join(c for c in word if c.isalnum())
            translated_word = translations.get(clean_word.lower(), word)
            translated_words.append(translated_word)
            
        translated_text = ' '.join(translated_words)
        
        # 添加说明文字表示这是模拟翻译
        final_translation = (
            "[注意：这是模拟翻译结果，仅作演示用途]\n\n" +
            translated_text + "\n\n" +
            "[在实际应用中，这里应该接入真实的翻译API，如有道翻译、谷歌翻译等]"
        )
        
        return final_translation
    
    def copy_content(self):
        clipboard = QApplication.clipboard()
        content = f"""标题: {self.news['title']}
分类: {self.news['category']}
来源: {self.news['source']}
时间: {self.news['time'].toString('yyyy-MM-dd HH:mm')}

摘要:
{self.news['summary']}

详细内容:
{self.news['content']}"""
        
        clipboard.setText(content)
        QMessageBox.information(self, "提示", "新闻内容已复制到剪贴板")

# ---------------------- 每日任务对话框 ----------------------
class DailyTaskDialog(BaseIndependentDialog):
    """每日任务对话框"""
    def __init__(self, parent_ref=None):
        super().__init__("每日任务", parent_ref)
        self.setFixedSize(450, 480)
        self.setModal(False)
        
        # 标题
        title_label = QLabel("任务列表")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0; color: #333;")
        self.main_layout.addWidget(title_label)
        
        # 任务列表
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fff;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        self.task_list.itemDoubleClicked.connect(self.toggle_task_completion)
        self.main_layout.addWidget(self.task_list)
        
        # 添加任务区域
        add_group_box = QLabel("添加新任务:")
        add_group_box.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(add_group_box)
        
        add_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("输入新任务...")
        self.task_input.returnPressed.connect(self.add_task)
        self.task_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.add_btn = QPushButton("添加任务")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.add_btn.clicked.connect(self.add_task)
        add_layout.addWidget(self.task_input)
        add_layout.addWidget(self.add_btn)
        self.main_layout.addLayout(add_layout)
        
        # 虚化度控制
        blur_group_box = QLabel("背景虚化度:")
        blur_group_box.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(blur_group_box)
        
        blur_layout = QHBoxLayout()
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(0, 200)
        # 从数据库加载虚化度设置，默认为100
        default_blur = 100
        if self.parent_ref:
            default_blur = self.parent_ref.db_handler.get_setting("task_window_blur", 100)
        self.blur_slider.setValue(default_blur)
        self.blur_slider.valueChanged.connect(self.change_blur)
        self.blur_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #ddd;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 4px;
            }
        """)
        
        self.blur_label = QLabel(f"{default_blur}%")
        self.blur_label.setStyleSheet("min-width: 40px; font-weight: bold;")
        blur_layout.addWidget(self.blur_slider)
        blur_layout.addWidget(self.blur_label)
        self.main_layout.addLayout(blur_layout)
        
        # 任务操作按钮
        btn_group_box = QLabel("任务操作:")
        btn_group_box.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(btn_group_box)
        
        btn_layout = QHBoxLayout()
        self.edit_btn = QPushButton("编辑任务")
        self.complete_btn = QPushButton("完成/取消完成")
        self.delete_btn = QPushButton("删除任务")
        
        for btn in [self.edit_btn, self.complete_btn, self.delete_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333;
                    border: 1px solid #ccc;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
        
        self.edit_btn.clicked.connect(self.edit_task)
        self.complete_btn.clicked.connect(self.toggle_task_completion)
        self.delete_btn.clicked.connect(self.delete_task)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.complete_btn)
        btn_layout.addWidget(self.delete_btn)
        self.main_layout.addLayout(btn_layout)
        
        # 初始化
        self.load_tasks()
        self.change_blur(default_blur)
        self._toggle_stay_on_top()  # 默认置顶
    
    def change_blur(self, value):
        self.blur_label.setText(f"{value}%")
        opacity = 0.1 + (200 - value)/200 * 0.9 if value >=100 else 1.0 - value/200
        self.setWindowOpacity(opacity)
        # 保存虚化度设置到数据库
        if self.parent_ref:
            self.parent_ref.db_handler.set_setting("task_window_blur", value)
    
    def load_tasks(self):
        # 从数据库加载任务而不是使用示例任务
        tasks = self.parent_ref.db_handler.get_all_tasks() if self.parent_ref else []
        for task in tasks:
            item_text = task["name"]
            if task["note"]:
                item_text += f" [备注: {task['note'][:20]}...]"
            item = QListWidgetItem(item_text)
            item.setCheckState(Qt.CheckState.Checked if task["is_completed"] else Qt.CheckState.Unchecked)
            if task["is_completed"]:
                item.setText(f"✓ {item_text}")
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.task_list.addItem(item)
            # 如果任务有提醒时间，则添加到主窗口的闹钟列表中
            if task["reminder_time"] and self.parent_ref:
                # 确保parent_ref有alarms属性
                if not hasattr(self.parent_ref, 'alarms'):
                    self.parent_ref.alarms = []
                self.parent_ref.alarms.append({
                    "time": task["reminder_time"], "repeat": "不重复", 
                    "ringtone": "默认铃声", "triggered": False, "task": task["name"]
                })
        if self.parent_ref and hasattr(self.parent_ref, 'update_alarms_list'):
            self.parent_ref.update_alarms_list()
    
    def add_task(self):
        dialog = TaskEditDialog("", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_info = dialog.get_task_info()
            if task_info["name"]:
                # 保存到数据库
                task_id = None
                if self.parent_ref and hasattr(self.parent_ref, 'db_handler'):
                    task_id = self.parent_ref.db_handler.add_task(task_info)
                
                item_text = task_info["name"]
                if task_info["note"]:
                    item_text += f" [备注: {task_info['note'][:20]}...]"
                item = QListWidgetItem(item_text)
                item.setCheckState(Qt.CheckState.Unchecked)
                # 添加任务ID到任务信息中
                if task_id:
                    task_info["id"] = task_id
                item.setData(Qt.ItemDataRole.UserRole, task_info)
                self.task_list.addItem(item)
                if task_info["reminder_time"] and self.parent_ref:
                    # 确保parent_ref有alarms属性
                    if not hasattr(self.parent_ref, 'alarms'):
                        self.parent_ref.alarms = []
                    self.parent_ref.alarms.append({
                        "time": task_info["reminder_time"], "repeat": "不重复", 
                        "ringtone": "默认铃声", "triggered": False, "task": task_info["name"]
                    })
                    if hasattr(self.parent_ref, 'update_alarms_list'):
                        self.parent_ref.update_alarms_list()
    
    def edit_task(self):
        current = self.task_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择任务")
            return
        task_info = current.data(Qt.ItemDataRole.UserRole) or {"name": current.text(), "note": ""}
        dialog = TaskEditDialog(task_info["name"], self)
        dialog.task_note_edit.setPlainText(task_info["note"])
        if task_info.get("reminder_time"):
            dialog.no_reminder_checkbox.setChecked(False)
            dialog.reminder_time.setEnabled(True)
            dialog.reminder_time.setDateTime(task_info["reminder_time"])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_info = dialog.get_task_info()
            if new_info["name"]:
                # 更新数据库中的任务
                if self.parent_ref and hasattr(self.parent_ref, 'db_handler') and "id" in task_info:
                    self.parent_ref.db_handler.update_task(task_info["id"], new_info)
                
                item_text = new_info["name"]
                if new_info["note"]:
                    item_text += f" [备注: {new_info['note'][:20]}...]"
                current.setText(item_text)
                current.setData(Qt.ItemDataRole.UserRole, new_info)
                if new_info["reminder_time"] and self.parent_ref:
                    # 确保parent_ref有alarms属性
                    if not hasattr(self.parent_ref, 'alarms'):
                        self.parent_ref.alarms = []
                    # 更新闹钟列表
                    self.parent_ref.alarms = [a for a in self.parent_ref.alarms if a.get("task") != new_info["name"]]
                    self.parent_ref.alarms.append({
                        "time": new_info["reminder_time"], "repeat": "不重复", 
                        "ringtone": "默认铃声", "triggered": False, "task": new_info["name"]
                    })
                    if hasattr(self.parent_ref, 'update_alarms_list'):
                        self.parent_ref.update_alarms_list()
    
    def toggle_task_completion(self):
        current = self.task_list.currentItem()
        if current:
            task_info = current.data(Qt.ItemDataRole.UserRole)
            is_completed = current.checkState() == Qt.CheckState.Unchecked
            
            # 更新数据库中的任务完成状态
            if self.parent_ref and hasattr(self.parent_ref, 'db_handler') and task_info and "id" in task_info:
                self.parent_ref.db_handler.toggle_task_completion(task_info["id"], is_completed)
            
            if is_completed:
                current.setCheckState(Qt.CheckState.Checked)
                current.setText(f"✓ {current.text()}")
            else:
                current.setCheckState(Qt.CheckState.Unchecked)
                current.setText(current.text()[2:] if current.text().startswith("✓ ") else current.text())
    
    def delete_task(self):
        current = self.task_list.currentItem()
        if not current:
            return
            
        task_info = current.data(Qt.ItemDataRole.UserRole)
        row = self.task_list.row(current)
        if row >= 0:
            if QMessageBox.question(self, "确认", "确定删除？") == QMessageBox.StandardButton.Yes:
                # 从数据库删除任务
                if self.parent_ref and hasattr(self.parent_ref, 'db_handler') and task_info and "id" in task_info:
                    self.parent_ref.db_handler.delete_task(task_info["id"])
                
                self.task_list.takeItem(row)

# ---------------------- 笔记管理对话框 ----------------------
class NotesDialog(BaseIndependentDialog):
    """笔记管理对话框"""
    def __init__(self, parent_ref=None):
        super().__init__("笔记管理", parent_ref)
        self.setFixedSize(600, 500)
        self.setModal(False)
        
        # 左右分栏（列表+编辑区）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：笔记列表+搜索
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索笔记:")
        search_label.setStyleSheet("font-weight: bold; color: #555;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索笔记...")
        self.search_input.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        list_layout.addLayout(search_layout)
        
        # 笔记列表
        notes_label = QLabel("笔记列表:")
        notes_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        list_layout.addWidget(notes_label)
        
        self.notes_list = QListWidget()
        self.notes_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fff;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        list_layout.addWidget(self.notes_list)
        splitter.addWidget(list_widget)
        
        # 右侧：编辑区
        edit_widget = QWidget()
        edit_layout = QVBoxLayout(edit_widget)
        
        # 标题输入
        title_label = QLabel("笔记标题:")
        title_label.setStyleSheet("font-weight: bold; color: #555;")
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("笔记标题")
        self.note_title.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        edit_layout.addWidget(title_label)
        edit_layout.addWidget(self.note_title)
        
        # 内容编辑
        content_label = QLabel("笔记内容:")
        content_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.note_content = QTextEdit()
        self.note_content.setStyleSheet("padding: 8px; background-color: #fff; border: 1px solid #ddd; border-radius: 5px;")
        edit_layout.addWidget(content_label)
        edit_layout.addWidget(self.note_content)
        
        # 标签输入
        tags_label = QLabel("标签（用逗号分隔）:")
        tags_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.note_tags = QLineEdit()
        self.note_tags.setPlaceholderText("标签（用逗号分隔）")
        self.note_tags.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px;")
        edit_layout.addWidget(tags_label)
        edit_layout.addWidget(self.note_tags)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存笔记")
        self.delete_btn = QPushButton("删除笔记")
        
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        self.save_btn.clicked.connect(self.save_note)
        self.delete_btn.clicked.connect(self.delete_note)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.delete_btn)
        edit_layout.addLayout(btn_layout)
        splitter.addWidget(edit_widget)
        
        splitter.setSizes([200, 400])
        self.main_layout.addWidget(splitter)
        self._toggle_stay_on_top()  # 默认置顶
    
    def save_note(self):
        title = self.note_title.text().strip()
        content = self.note_content.toPlainText().strip()
        if not title and not content:
            QMessageBox.warning(self, "错误", "标题和内容不能同时为空")
            return
        
        # 选择保存路径
        default_name = title if title else f"未命名_{QDateTime.currentDateTime().toString('yyyyMMddHHmmss')}"
        file_path, _ = QFileDialog.getSaveFileName(self, "保存笔记", default_name, "文本文件 (*.txt);;所有文件 (*)")
        if not file_path:
            return
        
        # 写入文件
        try:
            note_data = []
            if title:
                note_data.append(f"标题：{title}")
            if self.note_tags.text().strip():
                note_data.append(f"标签：{self.note_tags.text().strip()}")
            note_data.append("-"*50)
            note_data.append(content)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(note_data))
            self.notes_list.addItem(title if title else "未命名笔记")
            QMessageBox.information(self, "成功", f"已保存到：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"保存出错：{str(e)}")
    
    def delete_note(self):
        current = self.notes_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择笔记")
            return
        if QMessageBox.question(self, "确认", "确定删除？") == QMessageBox.StandardButton.Yes:
            self.notes_list.takeItem(self.notes_list.row(current))
            self.note_title.clear()
            self.note_content.clear()
            self.note_tags.clear()

# ---------------------- 新闻推送对话框 ----------------------

class NewsDetailDialog(BaseIndependentDialog):
    """显示新闻详情的对话框（提供打开原文、翻译、复制等操作）"""
    def __init__(self, news, parent_ref=None):
        super().__init__("新闻详情", parent_ref)
        self.news = news or {}
        self.setFixedSize(720, 600)
        self.setModal(True)

        # 将新闻保存到数据库
        if self.parent_ref and hasattr(self.parent_ref, 'db_handler'):
            self.parent_ref.db_handler.save_news_record(self.news)

        # 主显示区域
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # 标题
        title_label = QLabel(self.news.get("title", "无标题"))
        title_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #333;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # 元数据行（来源、分类、时间）
        meta_layout = QHBoxLayout()
        
        source_label = QLabel(f"来源: {self.news.get('source', '未知来源')}")
        source_label.setStyleSheet("color: #666; font-size: 14px;")
        
        category_label = QLabel(f"分类: {self.news.get('category', '未分类')}")
        category_label.setStyleSheet("color: #666; font-size: 14px;")
        
        time_str = "未知时间"
        try:
            if "time" in self.news and self.news["time"]:
                time_str = self.news["time"].toString("yyyy-MM-dd HH:mm")
        except Exception:
            pass
        time_label = QLabel(f"时间: {time_str}")
        time_label.setStyleSheet("color: #666; font-size: 14px;")
        
        meta_layout.addWidget(source_label)
        meta_layout.addWidget(category_label)
        meta_layout.addWidget(time_label)
        meta_layout.addStretch()
        
        layout.addLayout(meta_layout)

        # 摘要部分
        summary_header = QLabel("摘要:")
        summary_header.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px;")
        layout.addWidget(summary_header)
        
        summary_edit = QTextEdit(self.news.get("summary", "无摘要"))
        summary_edit.setReadOnly(True)
        summary_edit.setMaximumHeight(100)
        summary_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                background-color: #f9f9f9;
                color: #333;
            }
        """)
        layout.addWidget(summary_edit)

        # 详细内容部分
        content_header = QLabel("详细内容:")
        content_header.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px;")
        layout.addWidget(content_header)
        
        self.content_edit = QTextEdit(self.news.get("content", "无详细内容"))
        self.content_edit.setReadOnly(True)
        self.content_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                background-color: #fff;
                color: #333;
            }
        """)
        layout.addWidget(self.content_edit)

        # 翻译内容区域（默认隐藏）
        self.translation_label = QLabel("翻译内容:")
        self.translation_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px;")
        self.translation_label.hide()
        layout.addWidget(self.translation_label)
        
        self.translation_text = QTextEdit()
        self.translation_text.setReadOnly(True)
        self.translation_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                background-color: #f0f8ff;
                color: #333;
            }
        """)
        self.translation_text.hide()
        layout.addWidget(self.translation_text)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.open_btn = QPushButton("打开原文")
        self.translate_btn = QPushButton("翻译")
        copy_btn = QPushButton("复制内容")
        close_btn = QPushButton("关闭")

        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #ddd;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)

        def _open_url():
            url = self.news.get("url", "")
            if url:
                QDesktopServices.openUrl(QUrl(url))
            else:
                QMessageBox.warning(self, "提示", "该新闻没有提供原文链接")

        def _copy():
            content = f"""标题: {self.news.get('title', '无标题')}
来源: {self.news.get('source', '未知来源')}
分类: {self.news.get('category', '未分类')}
时间: {time_str}

摘要:
{self.news.get('summary', '无摘要')}

详细内容:
{self.news.get('content', '无详细内容')}"""
            
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            QMessageBox.information(self, "提示", "新闻内容已复制到剪贴板")

        def _translate():
            content = self.news.get('content', '')
            if not content:
                QMessageBox.warning(self, "提示", "没有可翻译的内容")
                return
                
            # 检查是否已经是中文
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
            if has_chinese:
                reply = QMessageBox.question(self, "确认", "内容似乎包含中文，是否仍要翻译？", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # 显示翻译中状态
            self.translate_btn.setText("翻译中...")
            self.translate_btn.setEnabled(False)
            QApplication.processEvents()
            
            try:
                # 初始化翻译器（如果还没有）
                if not hasattr(self, 'translator'):
                    self.translator = YoudaoTranslateAPI(
                        app_key="2b25cfef11d3a298",
                        app_secret="sfOKZO3046bZxfTUiwgIRtew3yfnJI87"
                    )
                
                # 调用翻译API
                translated_text = self.translator.translate(content)
                if "翻译失败" not in translated_text and "翻译出错" not in translated_text:
                    # 显示翻译区域
                    self.translation_label.show()
                    self.translation_text.show()
                    self.translation_text.setPlainText(translated_text)
                    
                    # 调整窗口大小以适应翻译内容
                    self.resize(720, 700)
                else:
                    QMessageBox.warning(self, "翻译失败", translated_text)
            except Exception as e:
                QMessageBox.critical(self, "翻译错误", f"翻译过程中发生错误：{str(e)}")
            finally:
                # 恢复按钮状态
                self.translate_btn.setText("翻译")
                self.translate_btn.setEnabled(True)

        self.open_btn.clicked.connect(_open_url)
        self.translate_btn.clicked.connect(_translate)
        copy_btn.clicked.connect(_copy)
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.translate_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.main_layout.addLayout(layout)
        self._toggle_stay_on_top()  # 默认置顶

# ---------------------- 新闻推送对话框 ----------------------
class NewsDialog(BaseIndependentDialog):
    """新闻推送对话框（支持实时新闻获取）"""
    def __init__(self, parent_ref=None):
        super().__init__("新闻推送", parent_ref)
        self.setFixedSize(800, 600)
        self.setModal(False)
        self.api_handler = NewsAPIHandler()  # 实例化API处理器
        
        # 新闻数据存储
        self.news_data = []
        self.filtered_news = []
        
        self.init_search_ui()  # 初始化搜索UI
        self.init_category_filter()
        self.init_sort_controls()
        self.init_news_list()
        self.init_action_buttons()
        
        self.load_top_headlines()  # 加载真实头条新闻（替换模拟数据）
        self._toggle_stay_on_top()  # 默认置顶
    
    def init_search_ui(self):
        """初始化检索控件"""
        # 搜索栏标题
        search_title = QLabel("新闻搜索:")

        search_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(search_title)
        
        # 搜索栏（关键词+时间筛选）
        search_layout = QHBoxLayout()
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入关键词搜索...")
        self.keyword_input.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.start_date = QDateTimeEdit()
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addDays(-7))  # 默认近7天
        self.start_date.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.end_date = QDateTimeEdit(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.search_btn.clicked.connect(self.do_search)
        
        search_layout.addWidget(QLabel("关键词:"))
        search_layout.addWidget(self.keyword_input)
        search_layout.addWidget(QLabel("从:"))
        search_layout.addWidget(self.start_date)
        search_layout.addWidget(QLabel("到:"))
        search_layout.addWidget(self.end_date)
        search_layout.addWidget(self.search_btn)
        self.main_layout.addLayout(search_layout)

        # 热门标签（快速筛选）
        hot_tags_title = QLabel("热门话题:")
        hot_tags_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(hot_tags_title)
        
        hot_tags = ["科技突破", "财经热点", "国际大事", "体育赛事"]
        tag_layout = QHBoxLayout()
        tag_layout.addWidget(QLabel("快速选择:"))
        for tag in hot_tags:
            btn = QPushButton(tag)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333;
                    border: 1px solid #ccc;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            btn.clicked.connect(lambda checked, t=tag: self.keyword_input.setText(t))
            tag_layout.addWidget(btn)
        tag_layout.addStretch()
        self.main_layout.addLayout(tag_layout)
    
    def init_category_filter(self):
        """初始化分类筛选"""
        filter_title = QLabel("筛选条件:")
        filter_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(filter_title)
        
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "科技", "财经", "体育", "娱乐", "国际", "教育", "健康", "综合"])
        self.category_combo.currentTextChanged.connect(self.filter_news)
        self.category_combo.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        category_layout.addWidget(self.category_combo)
        
        # 来源筛选
        category_layout.addWidget(QLabel("来源:"))
        self.country_combo = QComboBox()
        self.country_combo.addItems(["全部", "央视新闻", "人民日报", "澎湃新闻"])
        self.country_combo.currentTextChanged.connect(self.filter_news)
        self.country_combo.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        category_layout.addWidget(self.country_combo)
        
        self.main_layout.addLayout(category_layout)
    
    def init_sort_controls(self):
        """初始化排序控件"""
        sort_title = QLabel("排序方式:")
        sort_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(sort_title)
        
        sort_layout = QHBoxLayout()
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["默认排序", "按热度降序", "按时间最新"])
        self.sort_combo.currentTextChanged.connect(self.sort_news)
        self.sort_combo.setStyleSheet("padding: 6px; border: 1px solid #ccc; border-radius: 4px;")
        sort_layout.addWidget(QLabel("排序:"))
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        self.main_layout.addLayout(sort_layout)
    
    def init_news_list(self):
        """初始化新闻列表"""
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新新闻")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFA000;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_news)
        self.main_layout.addWidget(self.refresh_btn)
        
        # 新闻列表标题
        news_list_title = QLabel("新闻列表:")
        news_list_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(news_list_title)
        
        # 新闻列表
        self.news_list = QListWidget()
        self.news_list.itemDoubleClicked.connect(self.show_news_detail)
        self.news_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fff;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        self.main_layout.addWidget(self.news_list)
    
    def init_action_buttons(self):
        """初始化操作按钮"""
        # 操作按钮标题
        action_title = QLabel("操作:")
        action_title.setStyleSheet("font-weight: bold; margin-top: 10px; color: #555;")
        self.main_layout.addWidget(action_title)
        
        btn_layout = QHBoxLayout()
        self.detail_btn = QPushButton("查看详情")
        self.save_btn = QPushButton("收藏到笔记")
        self.test_rss_btn = QPushButton("测试RSS源")
        
        self.detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.test_rss_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        self.detail_btn.clicked.connect(self.show_news_detail)
        self.save_btn.clicked.connect(self.save_news)
        self.test_rss_btn.clicked.connect(self.test_rss_feeds)
        btn_layout.addWidget(self.detail_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.test_rss_btn)
        btn_layout.addStretch()
        self.main_layout.addLayout(btn_layout)
    
    def test_rss_feeds(self):
        """测试RSS源功能"""
        try:
            results = self.api_handler.test_rss_feeds()
            msg = "RSS源测试结果:\n\n"
            for source, result in results.items():
                if result['status'] == 'success':
                    msg += f"✓ {source}: 成功 (长度: {result['content_length']})\n"
                else:
                    msg += f"✗ {source}: 失败 ({result['error']})\n"
            
            QMessageBox.information(self, "RSS源测试", msg)
        except Exception as e:
            QMessageBox.critical(self, "测试错误", f"测试过程中发生错误: {str(e)}")

    def load_top_headlines(self):
        """加载国内外头条新闻"""
        try:
            loading_label = QLabel("加载头条新闻中...")
            self.main_layout.addWidget(loading_label)
            QApplication.processEvents()
            
            # 加载所有RSS源的新闻
            print("开始加载RSS新闻...")
            all_news = self.api_handler.get_top_headlines()
            print(f"总共获取到 {len(all_news)} 条新闻")
                
            self.news_data = all_news
            self.filtered_news = self.news_data
            self.sort_news()
            self.update_news_list()
            
            self.main_layout.removeWidget(loading_label)
            loading_label.deleteLater()
            
            # 如果没有获取到新闻，给出提示
            if len(all_news) == 0:
                QMessageBox.warning(self, "提示", "未能获取到新闻，请检查网络连接或稍后重试")
        except Exception as e:
            error_msg = f"头条新闻加载失败: {str(e)}"
            print(error_msg)  # 控制台输出详细错误
            QMessageBox.critical(self, "加载失败", error_msg)
            self._add_sample_news()  # 加载失败时使用模拟数据
    
    def do_search(self):
        """执行搜索逻辑"""
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        try:
            loading_label = QLabel("搜索中...")
            self.main_layout.addWidget(loading_label)
            QApplication.processEvents()
            
            # 调用API检索
            self.news_data = self.api_handler.search_news(
                keyword=keyword,
                start_date=self.start_date.dateTime(),
                end_date=self.end_date.dateTime()
            )
            
            # 默认搜索结果标记为中国新闻（因为RSS源都是中国的）
            for news in self.news_data:
                if not news.get("country"):
                    news["country"] = "cn"
                    
            self.filtered_news = self.news_data
            self.sort_news()
            self.update_news_list()
            
            self.main_layout.removeWidget(loading_label)
            loading_label.deleteLater()
            
            # 提示搜索结果
            if len(self.news_data) == 0:
                QMessageBox.information(self, "搜索完成", "未找到匹配的新闻")
            else:
                QMessageBox.information(self, "搜索完成", f"找到 {len(self.news_data)} 条相关新闻")
        except Exception as e:
            error_msg = f"搜索失败: {str(e)}"
            print(error_msg)  # 控制台输出详细错误
            QMessageBox.critical(self, "错误", error_msg)

    def sort_news(self):
        """根据选择排序新闻列表"""
        if self.sort_combo.currentText() == "按热度降序":
            self.filtered_news.sort(key=lambda x: x.get("hot_score", 0), reverse=True)
        elif self.sort_combo.currentText() == "按时间最新":
            self.filtered_news.sort(key=lambda x: x["time"].toSecsSinceEpoch(), reverse=True)
        self.update_news_list()
    
    def _add_sample_news(self):
        """API调用失败时使用的模拟数据"""
        self.news_data = [
            {"title": "神舟十五号载人飞船发射成功", 
             "category": "科技", 
             "summary": "北京时间11月29日，神舟十五号载人飞船在酒泉卫星发射中心发射升空，飞行乘组状态良好，发射取得圆满成功。",
             "content": "北京时间11月29日23时08分，搭载神舟十五号载人飞船的长征二号F遥十五运载火箭在酒泉卫星发射中心点火发射。约10分钟后，神舟十五号载人飞船与火箭成功分离，进入预定轨道，航天员乘组状态良好，发射取得圆满成功。",
             "source": "央视新闻",
             "time": QDateTime.currentDateTime().addDays(-1),
             "hot_score": 95,
             "url": "https://news.cctv.com/2022/11/29/ARTI2VJNjgRrZ0FDzZp2KlO6221129.shtml",
             "country": "cn"},
            {"title": "全国多地优化疫情防控措施", 
             "category": "综合", 
             "summary": "为进一步科学精准做好疫情防控工作，国务院联防联控机制综合组公布进一步优化疫情防控工作的二十条措施。",
             "content": "为指导各地各部门进一步优化疫情防控措施，国务院联防联控机制综合组制定了进一步优化疫情防控工作的二十条措施，包括科学精准划分风险区域、进一步优化核酸检测等措施。",
             "source": "人民日报",
             "time": QDateTime.currentDateTime().addDays(-2),
             "hot_score": 87,
             "url": "https://www.people.com.cn/n1/2022/1129/c323627-32576545.html",
             "country": "cn"},
            {"title": "卡塔尔世界杯：阿根廷击败墨西哥", 
             "category": "体育", 
             "summary": "在卡塔尔世界杯小组赛C组第二轮比赛中，阿根廷队凭借梅西的进球1比0战胜墨西哥队，重新燃起晋级希望。",
             "content": "在26日进行的卡塔尔世界杯小组赛C组第二轮比赛中，阿根廷队凭借梅西在第64分钟的进球，1比0击败墨西哥队。这场胜利让阿根廷队重燃晋级希望。",
             "source": "澎湃新闻",
             "time": QDateTime.currentDateTime().addDays(-1),
             "hot_score": 92,
             "url": "https://www.thepaper.cn/newsDetail_forward_12345678",
             "country": "cn"}
        ]
        self.filtered_news = self.news_data.copy()
        self.sort_news()
        self.update_news_list()
    
    def update_news_list(self):
        self.news_list.clear()
        for news in self.filtered_news:
            hot_tag = "🔥 " if news.get("hot_score", 0) > 80 else ""
            source_tag = f"[{news['source']}] " if news.get('source') else ""
            category_tag = f"[{news['category']}] "
            
            item_text = f"{hot_tag}{source_tag}{category_tag} {news['title']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, news)
            self.news_list.addItem(item)
    
    def filter_news(self):
        category = self.category_combo.currentText()
        source = self.country_combo.currentText()
        
        # 先按分类筛选
        if category == "全部":
            filtered_by_category = self.news_data.copy()
        else:
            filtered_by_category = [news for news in self.news_data if news['category'] == category]
        
        # 再按来源筛选
        if source == "全部":
            self.filtered_news = filtered_by_category
        else:
            self.filtered_news = [news for news in filtered_by_category if news.get('source') == source]
            
        self.sort_news()
    
    def refresh_news(self):
        """刷新新闻列表"""
        self.load_top_headlines()
        QMessageBox.information(self, "提示", "新闻已刷新")
    
    def show_news_detail(self):
        current = self.news_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择一条新闻")
            return
            
        news = current.data(Qt.ItemDataRole.UserRole)
        detail_dialog = NewsDetailDialog(news, self)
        detail_dialog.exec()
    
    def save_news(self):
        current = self.news_list.currentItem()
        if not current:
            QMessageBox.warning(self, "提示", "请先选择新闻")
            return
        
        news = current.data(Qt.ItemDataRole.UserRole)
        news_title = news['title']
        news_content = f"""新闻收藏
====================

标题：{news['title']}
分类：{news['category']}
来源：{news['source']}
时间：{news['time'].toString('yyyy-MM-dd HH:mm')}

摘要：
{news['summary']}

详细内容：
{news['content']}

收藏时间：{QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm')}
"""
        
        # 收藏到笔记
        if self.parent_ref and hasattr(self.parent_ref, 'open_dialogs'):
            for dialog in self.parent_ref.open_dialogs:
                if isinstance(dialog, NotesDialog):
                    dialog.note_title.setText(f"新闻收藏: {news_title}")
                    dialog.note_content.setText(news_content)
                    dialog.note_tags.setText(f"新闻收藏,{news['category']}")
                    dialog.show()
                    dialog.activateWindow()
                    break
            else:
                note_dialog = NotesDialog(self.parent_ref)
                note_dialog.note_title.setText(f"新闻收藏: {news_title}")
                note_dialog.note_content.setText(news_content)
                note_dialog.note_tags.setText(f"新闻收藏,{news['category']}")
                note_dialog.show()
                self.parent_ref.open_dialogs.append(note_dialog)
        QMessageBox.information(self, "成功", "新闻已收藏到笔记")

# ---------------------- 闹钟提醒对话框 ----------------------
class AlarmDialog(BaseIndependentDialog):
    """闹钟提醒对话框"""
    def __init__(self, parent_ref=None):
        super().__init__("闹钟提醒", parent_ref)
        self.setFixedSize(400, 500)
        self.setModal(False)
        
        # 时间选择
        self.main_layout.addWidget(QLabel("设置提醒时间："))
        self.alarm_time = QDateTimeEdit(QDateTime.currentDateTime())
        self.alarm_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.main_layout.addWidget(self.alarm_time)
        
        # 重复选项
        self.main_layout.addWidget(QLabel("重复频率："))
        self.alarm_repeat = QComboBox()
        self.alarm_repeat.addItems(["不重复", "每天", "每周", "每月"])
        self.main_layout.addWidget(self.alarm_repeat)
        
        # 铃声选择
        self.main_layout.addWidget(QLabel("提醒铃声："))
        self.alarm_ringtone = QComboBox()
        self.alarm_ringtone.addItems(["默认铃声", "自定义铃声..."])
        self.main_layout.addWidget(self.alarm_ringtone)
        
        # 设置按钮
        self.set_btn = QPushButton("设置闹钟")
        self.set_btn.clicked.connect(self.set_alarm)
        self.main_layout.addWidget(self.set_btn)
        
        # 已设置闹钟列表
        self.main_layout.addWidget(QLabel("已设置的闹钟："))
        self.alarms_list = QListWidget()
        self.main_layout.addWidget(self.alarms_list)
        
        self._toggle_stay_on_top()  # 默认置顶
        self.update_alarms_list()
    
    def set_alarm(self):
        # 简化实现：实际项目中需添加闹钟存储和触发逻辑
        alarm_time = self.alarm_time.dateTime()
        if alarm_time < QDateTime.currentDateTime():
            QMessageBox.warning(self, "错误", "提醒时间不能早于当前时间")
            return
        
        alarm_info = {
            "time": alarm_time,
            "repeat": self.alarm_repeat.currentText(),
            "ringtone": self.alarm_ringtone.currentText(),
            "triggered": False
        }
        
        if self.parent_ref and hasattr(self.parent_ref, 'alarms'):
            self.parent_ref.alarms.append(alarm_info)
            self.update_alarms_list()
            QMessageBox.information(self, "成功", "闹钟设置完成")
    
    def update_alarms_list(self):
        self.alarms_list.clear()
        if self.parent_ref and hasattr(self.parent_ref, 'alarms'):
            for i, alarm in enumerate(self.parent_ref.alarms):
                time_str = alarm["time"].toString("yyyy-MM-dd HH:mm")
                item_text = f"{time_str}（{alarm['repeat']}）"
                self.alarms_list.addItem(item_text)

# ---------------------- 翻译对话框（修复版） ----------------------
class TranslateDialog(BaseIndependentDialog):
    def __init__(self, parent_ref=None):
        super().__init__("翻译工具", parent_ref)
        self.setFixedSize(600, 400)
        # 已替换为提供的有道翻译API密钥
        self.translator = YoudaoTranslateAPI(
            app_key="2b25cfef11d3a298",
            app_secret="sfOKZO3046bZxfTUiwgIRtew3yfnJI87"
        )
        self.init_ui()
        self._toggle_stay_on_top()

    def init_ui(self):
        # 语言选择
        lang_layout = QHBoxLayout()
        self.from_lang = QComboBox()
        self.from_lang.addItems(["自动检测", "中文", "英文", "日语", "韩语"])
        self.swap_btn = QPushButton("↔")
        self.swap_btn.setFixedSize(30, 30)
        self.swap_btn.clicked.connect(self.swap_languages)
        self.to_lang = QComboBox()
        self.to_lang.addItems(["中文", "英文", "日语", "韩语"])
        lang_layout.addWidget(QLabel("源语言:"))
        lang_layout.addWidget(self.from_lang)
        lang_layout.addWidget(self.swap_btn)
        lang_layout.addWidget(QLabel("目标语言:"))
        lang_layout.addWidget(self.to_lang)
        self.main_layout.addLayout(lang_layout)

        # 输入输出
        input_output_layout = QVBoxLayout()
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入需要翻译的文本...")
        input_output_layout.addWidget(QLabel("输入:"))
        input_output_layout.addWidget(self.input_text)
        self.translate_btn = QPushButton("翻译")
        self.translate_btn.clicked.connect(self.do_translate)
        input_output_layout.addWidget(self.translate_btn)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        input_output_layout.addWidget(QLabel("结果:"))
        input_output_layout.addWidget(self.output_text)
        self.main_layout.addLayout(input_output_layout)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton("复制结果")
        self.clear_btn = QPushButton("清空输入")
        self.history_btn = QPushButton("翻译历史")
        self.copy_btn.clicked.connect(self.copy_result)
        self.clear_btn.clicked.connect(self.clear_input)
        self.history_btn.clicked.connect(self.show_history)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.history_btn)
        self.main_layout.addLayout(btn_layout)

    def _get_lang_code(self, lang_name):
        lang_map = {
            "自动检测": "auto", "中文": "zh-CHS", "英文": "en",
            "日语": "ja", "韩语": "ko"
        }
        return lang_map.get(lang_name, "auto")

    def swap_languages(self):
        from_lang = self.from_lang.currentText()
        to_lang = self.to_lang.currentText()
        if from_lang != "自动检测":
            self.from_lang.setCurrentText(to_lang)
            self.to_lang.setCurrentText(from_lang)

    def do_translate(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入文本")
            return
        from_code = self._get_lang_code(self.from_lang.currentText())
        to_code = self._get_lang_code(self.to_lang.currentText())
        self.output_text.setText("翻译中...")
        QApplication.processEvents()
        result = self.translator.translate(text, from_code, to_code)
        self.output_text.setText(result)
        
        # 保存翻译记录到数据库
        if self.parent_ref and hasattr(self.parent_ref, 'db_handler') and result and not ("翻译失败" in result or "翻译出错" in result):
            self.parent_ref.db_handler.add_translation_record(text, result, from_code, to_code)

    def copy_result(self):
        result = self.output_text.toPlainText()
        if result:
            QApplication.clipboard().setText(result)
            QMessageBox.information(self, "提示", "结果已复制")

    def clear_input(self):
        self.input_text.clear()
        self.output_text.clear()
        
    def show_history(self):
        if not self.parent_ref or not hasattr(self.parent_ref, 'db_handler'):
            return
            
        history = self.parent_ref.db_handler.get_translation_history()
        if not history:
            QMessageBox.information(self, "翻译历史", "暂无翻译历史")
            return
            
        # 创建历史记录对话框
        history_dialog = QDialog(self)
        history_dialog.setWindowTitle("翻译历史")
        history_dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        
        history_list = QListWidget()
        for record in history:
            item_text = f"{record['source_text'][:30]}... -> {record['translated_text'][:30]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, record)
            history_list.addItem(item)
            
        history_list.itemDoubleClicked.connect(lambda item: self.load_history_item(item))
        layout.addWidget(history_list)
        
        btn_layout = QHBoxLayout()
        load_btn = QPushButton("加载选中记录")
        close_btn = QPushButton("关闭")
        load_btn.clicked.connect(lambda: self.load_history_item(history_list.currentItem()))
        close_btn.clicked.connect(history_dialog.close)
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        history_dialog.setLayout(layout)
        history_dialog.exec()
        
    def load_history_item(self, item):
        if not item:
            return
        record = item.data(Qt.ItemDataRole.UserRole)
        self.input_text.setPlainText(record['source_text'])
        self.output_text.setPlainText(record['translated_text'])
        
        # 设置语言选项
        reverse_lang_map = {
            "auto": "自动检测", "zh-CHS": "中文", "en": "英文",
            "ja": "日语", "ko": "韩语"
        }
        self.from_lang.setCurrentText(reverse_lang_map.get(record['from_lang'], "自动检测"))
        self.to_lang.setCurrentText(reverse_lang_map.get(record['to_lang'], "中文"))

# ---------------------- 主窗口 ----------------------
class MainWindow(QMainWindow):
    """主窗口：整合所有功能入口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("思忆集 - 个人助手")
        self.setFixedSize(600, 400)
        self.open_dialogs = []  # 存储打开的对话框
        self.alarms = []  # 存储所有闹钟
        
        # 初始化数据库处理器
        try:
            self.db_handler = DatabaseHandler()
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            self.db_handler = None
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border: 1px solid #999999;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        
        # 标题
        title_label = QLabel("思忆集 - 个人助手")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333333;
            margin-bottom: 20px;
        """)
        main_layout.addWidget(title_label)
        
        # 功能按钮
        function_layout = QVBoxLayout()
        function_layout.setSpacing(15)
        
        self.news_btn = QPushButton("📰 新闻推送")
        self.tasks_btn = QPushButton("✅ 每日任务")
        self.notes_btn = QPushButton("📝 笔记管理")
        self.alarm_btn = QPushButton("⏰ 闹钟提醒")
        self.translate_btn = QPushButton("🌐 翻译工具")  # 新增翻译按钮
        
        # 为每个按钮设置图标样式
        buttons = [
            (self.news_btn, "#2196F3"),
            (self.tasks_btn, "#4CAF50"),
            (self.notes_btn, "#FF9800"),
            (self.alarm_btn, "#F44336"),
            (self.translate_btn, "#9C27B0")
        ]
        
        for btn, color in buttons:
            btn.setMinimumHeight(50)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: left;
                    padding-left: 20px;
                }}
                QPushButton:hover {{
                    background-color: {color[:-2] + "70" if color.startswith("#") else color};
                }}
            """)
            function_layout.addWidget(btn)
        
        function_layout.addStretch()
        main_layout.addLayout(function_layout)
        
        # 绑定事件
        self.news_btn.clicked.connect(self.open_news_dialog)
        self.tasks_btn.clicked.connect(self.open_tasks_dialog)
        self.notes_btn.clicked.connect(self.open_notes_dialog)
        self.alarm_btn.clicked.connect(self.open_alarm_dialog)
        self.translate_btn.clicked.connect(self.open_translate_dialog)  # 绑定翻译功能事件
    
    def open_news_dialog(self):
        """打开新闻对话框"""
        for dialog in self.open_dialogs:
            if isinstance(dialog, NewsDialog):
                dialog.show()
                dialog.activateWindow()
                return
        news_dialog = NewsDialog(self)
        news_dialog.show()
        self.open_dialogs.append(news_dialog)
    
    def open_tasks_dialog(self):
        """打开任务对话框"""
        for dialog in self.open_dialogs:
            if isinstance(dialog, DailyTaskDialog):
                dialog.show()
                dialog.activateWindow()
                return
        task_dialog = DailyTaskDialog(self)
        task_dialog.show()
        self.open_dialogs.append(task_dialog)
    
    def open_notes_dialog(self):
        """打开笔记对话框"""
        for dialog in self.open_dialogs:
            if isinstance(dialog, NotesDialog):
                dialog.show()
                dialog.activateWindow()
                return
        note_dialog = NotesDialog(self)
        note_dialog.show()
        self.open_dialogs.append(note_dialog)
    
    def open_alarm_dialog(self):
        """打开闹钟对话框"""
        for dialog in self.open_dialogs:
            if isinstance(dialog, AlarmDialog):
                dialog.show()
                dialog.activateWindow()
                return
        alarm_dialog = AlarmDialog(self)
        alarm_dialog.show()
        self.open_dialogs.append(alarm_dialog)
    
    def open_translate_dialog(self):
        """打开翻译对话框"""
        for dialog in self.open_dialogs:
            if isinstance(dialog, TranslateDialog):
                dialog.show()
                dialog.activateWindow()
                return
        translate_dialog = TranslateDialog(self)
        translate_dialog.show()
        self.open_dialogs.append(translate_dialog)
    
    def update_alarms_list(self):
        """更新所有闹钟列表（供子窗口调用）"""
        for dialog in self.open_dialogs:
            if isinstance(dialog, AlarmDialog):
                dialog.update_alarms_list()

# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())