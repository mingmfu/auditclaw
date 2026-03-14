#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合信招标网 - 审计招标信息自动采集脚本
使用 Playwright 实现自动化登录、搜索、数据采集
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import csv

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# ==================== 配置区域 ====================

@dataclass
class Config:
    """爬虫配置"""
    # 登录信息
    LOGIN_URL: str = "https://www.china-hxzb.com/"  # 首页
    USERNAME: str = "13167733815"
    PASSWORD: str = "dx13167733815"
    
    # 搜索配置 - 扩展关键词列表，确保搜索完所有审计相关项目
    SEARCH_KEYWORDS: List[str] = None
    MAX_PAGES: int = 50  # 每个关键词最大翻页数（增加以遍历所有页面）
    DELAY_BETWEEN_PAGES: float = 2.0  # 翻页间隔（秒）
    DELAY_AFTER_LOGIN: float = 3.0  # 登录后等待时间
    
    # 输出配置
    OUTPUT_DIR: str = "./output"
    OUTPUT_FILENAME: str = None  # 自动生成：hxzb_audit_YYYYMMDD_HHMMSS.csv
    
    # 浏览器配置
    HEADLESS: bool = False  # True=无头模式，False=可见窗口（调试用）
    BROWSER_TIMEOUT: int = 30000  # 页面加载超时（毫秒）
    
    def __post_init__(self):
        if self.SEARCH_KEYWORDS is None:
            # 扩展关键词列表 - 覆盖所有审计相关搜索
            self.SEARCH_KEYWORDS = [
                # 核心审计关键词
                "审计",
                "会计师事务所", 
                "年报审计",
                "年度审计",
                "年度财务报表审计",
                "专项审计",
                "离任审计",
                "经济责任审计",
                # 工程审计
                "工程决算审计",
                "竣工财务决算审计",
                "工程造价审计",
                "工程审计",
                # 内部审计
                "内部控制审计",
                "内控审计",
                "内部审计",
                # 其他审计
                "资产评估审计",
                "清产核资审计",
                "财务收支审计",
                "基本建设审计",
                "拆迁审计",
                "征地审计",
                "村级审计",
                "离任经济责任审计",
                "任中审计",
                "自然资源资产审计",
                "环境审计",
                "绩效审计",
                "合规审计",
            ]
        if self.OUTPUT_FILENAME is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.OUTPUT_FILENAME = f"anhui_audit_full_{timestamp}.json"


# ==================== 数据模型 ====================

@dataclass
class TenderInfo:
    """招标信息数据模型"""
    keyword: str = ""                    # 搜索关键词
    project_name: str = ""               # 项目名称
    project_code: str = ""               # 项目编号
    tender_org: str = ""                 # 招标单位
    budget_amount: str = ""              # 预算金额
    bid_deadline: str = ""               # 投标截止时间
    bid_open_time: str = ""              # 开标时间
    qualification: str = ""              # 资质要求
    service_period: str = ""             # 服务期限
    region: str = ""                     # 地区
    publish_date: str = ""               # 发布日期
    detail_url: str = ""                 # 详情链接
    category: str = ""                   # 公告类型（招标/预审/更正）
    extracted_at: str = ""               # 提取时间
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ==================== 日志配置 ====================

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('hxzb_spider.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ==================== 核心爬虫类 ====================

class HXZBSpider:
    """合信招标网爬虫"""
    
    # 常见CSS选择器模式（用于自动探测）
    COMMON_SELECTORS = {
        "login": {
            "username_input": [
                'input[name="username"]',
                'input[name="userName"]',
                'input[name="loginName"]',
                'input[name="account"]',
                'input[type="text"][placeholder*="账号"]',
                'input[type="text"][placeholder*="用户名"]',
                '#username',
                '#loginName',
            ],
            "password_input": [
                'input[name="password"]',
                'input[name="pwd"]',
                'input[type="password"]',
                '#password',
            ],
            "login_button": [
                'button[type="submit"]',
                'input[type="submit"]',
                '.login-btn',
                '.btn-login',
                'button:has-text("登录")',
                'button:has-text("登 录")',
                'a:has-text("登录")',
            ],
        },
        "search": {
            "search_input": [
                'input[name="keyword"]',
                'input[name="keywords"]',
                'input[placeholder*="搜索"]',
                'input[placeholder*="关键词"]',
                '.search-input',
                '#keyword',
            ],
            "search_button": [
                'button[type="submit"]',
                '.search-btn',
                '.btn-search',
                'button:has-text("搜索")',
                'button:has-text("查询")',
            ],
        },
        "list": {
            "list_container": [
                '.list-container',
                '.tender-list',
                '.bid-list',
                '.result-list',
                'table',
                '.content-list',
                '#list',
            ],
            "list_items": [
                '.list-item',
                '.tender-item',
                '.bid-item',
                'tr',
                'li',
                '.item',
            ],
            "next_page": [
                'a:has-text("下一页")',
                'a:has-text("下页")',
                '.next-page',
                '.pagination .next',
                'button:has-text("下一页")',
            ],
        },
        "detail": {
            "title": [
                '.title',
                '.project-title',
                'h1',
                'h2',
                '.detail-title',
            ],
            "content": [
                '.content',
                '.detail-content',
                '.project-detail',
                '.info',
            ],
        }
    }
    
    def __init__(self, config: Config):
        self.config = config
        self.results: List[TenderInfo] = []
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def init_browser(self):
        """初始化浏览器"""
        logger.info("正在启动浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.config.HEADLESS,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3]
            });
        """)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config.BROWSER_TIMEOUT)
        logger.info("浏览器启动完成")
        
    async def find_element(self, selectors: List[str], timeout: int = 5000) -> Optional:
        """从多个选择器中查找第一个存在的元素"""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=timeout)
                if element:
                    logger.debug(f"找到元素: {selector}")
                    return element
            except:
                continue
        return None
    
    async def safe_click(self, selectors: List[str], timeout: int = 5000) -> bool:
        """安全点击元素"""
        element = await self.find_element(selectors, timeout)
        if element:
            await element.click()
            return True
        return False
    
    async def safe_fill(self, selectors: List[str], text: str, timeout: int = 5000) -> bool:
        """安全填充输入框"""
        element = await self.find_element(selectors, timeout)
        if element:
            await element.fill(text)
            return True
        return False
    
    async def login(self) -> bool:
        """执行登录 - 从首页登录框登录"""
        logger.info(f"正在访问首页: {self.config.LOGIN_URL}")
        await self.page.goto(self.config.LOGIN_URL, wait_until='networkidle')
        
        # 等待页面加载
        await asyncio.sleep(2)
        
        # 截图查看页面状态
        await self.page.screenshot(path='login_page.png')
        logger.info("已保存登录页面截图: login_page.png")
        
        # 合信招标网首页登录框选择器
        hxzb_selectors = {
            "username_input": [
                '#login-username',  # 实际ID
                'input[name="username"]',  # name属性
                'input[id="login-username"]',
                'input[placeholder*="用户名"]', 
                'input[placeholder*="账号"]',
            ],
            "password_input": [
                '#login-password',  # 实际ID
                'input[name="password"]',  # name属性
                'input[id="login-password"]',
                'input[placeholder*="密码"]',
            ],
            "login_button": [
                'input.btn_login',  # 实际的选择器
                'input[type="submit"][value*="登录"]',
                'input[type="submit"][value*="登"]',
                'input[name="submit"]',
                '#login-username ~ input[type="submit"]',  # 用户名输入框后的提交按钮
                'input[type="submit"]',
                'input[value*="登录"]',
                'input[value*="登"]',
            ],
        }
        
        # 尝试填写账号
        username_filled = False
        for selector in hxzb_selectors["username_input"]:
            try:
                if selector.startswith('//'):
                    element = await self.page.wait_for_selector(f'xpath={selector}', timeout=2000)
                else:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.fill(self.config.USERNAME)
                    logger.info(f"已填写账号 (使用选择器: {selector})")
                    username_filled = True
                    break
            except Exception as e:
                continue
        
        if not username_filled:
            logger.error("未找到账号输入框，请查看 login_page.png")
            return False
        
        # 填写密码
        password_filled = False
        for selector in hxzb_selectors["password_input"]:
            try:
                if selector.startswith('//'):
                    element = await self.page.wait_for_selector(f'xpath={selector}', timeout=2000)
                else:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    await element.fill(self.config.PASSWORD)
                    logger.info(f"已填写密码 (使用选择器: {selector})")
                    password_filled = True
                    break
            except:
                continue
        
        if not password_filled:
            logger.error("未找到密码输入框")
            return False
        
        # 点击登录按钮 - 使用更可靠的方式
        login_clicked = False
        
        # 方式1：直接执行Dlogin函数（网站内置的登录函数）
        try:
            logger.info("尝试执行页面内置登录函数...")
            result = await self.page.evaluate("""
                () => {
                    if (typeof Dlogin === 'function') {
                        return Dlogin();
                    }
                    return null;
                }
            """)
            if result is not None:
                logger.info(f"已执行Dlogin函数，返回: {result}")
                login_clicked = True
        except Exception as e:
            logger.warning(f"执行Dlogin失败: {e}")
        
        # 方式2：尝试点击登录按钮
        if not login_clicked:
            for selector in hxzb_selectors["login_button"]:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        await element.click()
                        logger.info(f"已点击登录按钮 (使用选择器: {selector})")
                        login_clicked = True
                        break
                except:
                    continue
        
        # 方式3：在密码框按回车提交
        if not login_clicked:
            try:
                password_input = await self.page.wait_for_selector('#login-password', timeout=3000)
                if password_input:
                    await password_input.press('Enter')
                    logger.info("已在密码框按回车提交表单")
                    login_clicked = True
            except Exception as e:
                logger.warning(f"回车提交失败: {e}")
        
        if not login_clicked:
            logger.error("登录提交失败")
            return False
        
        # 等待登录响应 - 关键：等待页面跳转
        logger.info("等待登录响应...")
        try:
            # 等待URL变化（登录成功后通常会跳转）
            await self.page.wait_for_url(lambda url: 'login' not in url.lower() or url != self.config.LOGIN_URL, 
                                         timeout=15000, wait_until='networkidle')
        except:
            pass
        
        # 再等待一段时间让页面完全加载
        await asyncio.sleep(self.config.DELAY_AFTER_LOGIN)
        await self.page.screenshot(path='after_login.png')
        logger.info("已保存登录后截图: after_login.png")
        
        # 检查页面HTML中是否有错误信息
        try:
            page_html = await self.page.content()
            if '错误' in page_html or '失败' in page_html or 'error' in page_html.lower():
                # 提取可能的错误信息
                error_patterns = ['错误', '失败', '密码错误', '账号错误', '用户名或密码', '登录失败']
                for pattern in error_patterns:
                    if pattern in page_html:
                        logger.warning(f"页面可能包含错误信息: {pattern}")
        except Exception as e:
            logger.warning(f"检查页面内容失败: {e}")
        
        # 检测登录是否成功 - 多种方式验证
        current_url = self.page.url
        logger.info(f"当前URL: {current_url}")
        
        login_success = False
        
        # 方式1：检查URL是否变化（离开了首页或登录页）
        if current_url != self.config.LOGIN_URL and 'login' not in current_url.lower():
            logger.info("登录成功（URL已变化）")
            login_success = True
        
        # 方式2：检查页面中是否有用户相关元素（退出按钮、用户名等）
        if not login_success:
            try:
                # 检查是否有退出链接或用户中心链接
                user_elements = await self.page.query_selector_all('a:has-text("退出"), a:has-text("注销"), a:has-text("用户中心"), a:has-text("我的")')
                if len(user_elements) > 0:
                    logger.info("检测到用户相关元素，登录成功")
                    login_success = True
            except:
                pass
        
        # 方式3：检查登录表单是否消失
        if not login_success:
            try:
                login_form = await self.page.wait_for_selector('#login-username', timeout=3000)
                if not login_form:
                    logger.info("登录表单已消失，登录成功")
                    login_success = True
            except:
                logger.info("登录表单已消失，登录成功")
                login_success = True
        
        if login_success:
            logger.info("✅ 登录成功，准备搜索招标信息...")
            return True
        
        # 检查是否有错误提示
        try:
            error_selectors = ['.error-msg', '.error', '.alert', '.tip-error', '.layui-layer-content', '.error-info']
            for err_sel in error_selectors:
                error_msg = await self.page.query_selector(err_sel)
                if error_msg:
                    error_text = await error_msg.inner_text()
                    logger.error(f"登录失败，错误提示: {error_text}")
                    return False
        except:
            pass
        
        # 如果没有明确的成功或失败标志，检查是否可以继续
        logger.warning("无法确认登录状态，尝试继续...")
        return True
    
    async def search_keyword(self, keyword: str) -> List[TenderInfo]:
        """搜索单个关键词 - 合信招标网专用"""
        logger.info(f"开始搜索关键词: {keyword}")
        results = []
        
        # 先访问首页（确保在正确页面）
        await self.page.goto(self.config.LOGIN_URL, wait_until='networkidle')
        await asyncio.sleep(2)
        
        # 找到搜索框并输入关键词
        search_input = await self.page.wait_for_selector(
            'input[placeholder*="请输入关键词"], .search-input, #keyword, input[name="kw"], input[type="text"]:nth-of-type(1)',
            timeout=5000
        )
        if not search_input:
            logger.warning(f"关键词 '{keyword}' 未找到搜索框，跳过")
            return results
        
        await search_input.fill(keyword)
        logger.info(f"已输入关键词: {keyword}")
        
        # 点击搜索按钮 - 合信招标网有"标题搜索"和"高级搜索"两个按钮
        search_btn = await self.page.wait_for_selector(
            'button:has-text("标题搜索"), .search-btn, input[value*="搜索"], button[type="submit"], a:has-text("标题搜索")',
            timeout=3000
        )
        if search_btn:
            await search_btn.click()
            logger.info("已点击搜索按钮")
        else:
            # 尝试回车提交
            await search_input.press('Enter')
            logger.info("已按回车搜索")
        
        # 等待搜索结果页面加载
        await asyncio.sleep(3)
        await self.page.screenshot(path=f'search_page_{keyword}_1.png')
        
        # 翻页采集
        page_num = 1
        while page_num <= self.config.MAX_PAGES:
            logger.info(f"正在处理第 {page_num} 页...")
            
            # 提取当前页数据
            page_results = await self.extract_list_data_hxzb(keyword)
            results.extend(page_results)
            logger.info(f"第 {page_num} 页提取到 {len(page_results)} 条数据")
            
            # 尝试翻页
            try:
                next_btn = await self.page.wait_for_selector(
                    'a:has-text("下一页"), .next-page, .pagination .next, a.next',
                    timeout=2000
                )
                if not next_btn:
                    logger.info("没有下一页了")
                    break
                    
                # 检查是否禁用
                is_disabled = await next_btn.evaluate('el => el.disabled || el.classList.contains("disabled") || el.getAttribute("disabled")')
                if is_disabled:
                    logger.info("下一页按钮已禁用")
                    break
                
                await next_btn.click()
                await asyncio.sleep(self.config.DELAY_BETWEEN_PAGES)
                page_num += 1
            except:
                logger.info("没有下一页了")
                break
        
        logger.info(f"关键词 '{keyword}' 共采集 {len(results)} 条数据")
        return results
    
    async def extract_list_data_hxzb(self, keyword: str) -> List[TenderInfo]:
        """从合信招标网搜索结果页提取数据 - 只保留安徽地区"""
        results = []
        
        try:
            # 等待搜索结果表格加载
            await asyncio.sleep(2)
            
            # 获取页面上的所有表格行
            rows = await self.page.query_selector_all('table tr, tbody tr')
            logger.info(f"找到 {len(rows)} 个表格行")
            
            for i, row in enumerate(rows):
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) < 4:
                        continue
                    
                    # 提取基本信息
                    region = await cells[1].inner_text() if len(cells) > 1 else ''
                    
                    # ===== 只保留安徽地区 =====
                    if '安徽' not in region:
                        continue
                    
                    industry = await cells[2].inner_text() if len(cells) > 2 else ''
                    title_cell = cells[3] if len(cells) > 3 else None
                    publish_date = await cells[4].inner_text() if len(cells) > 4 else ''
                    
                    # 提取标题和详情链接
                    project_name = ''
                    detail_url = ''
                    if title_cell:
                        link = await title_cell.query_selector('a')
                        if link:
                            project_name = await link.inner_text() or await title_cell.inner_text()
                            detail_url = await link.get_attribute('href') or ''
                            # 处理相对URL
                            if detail_url and not detail_url.startswith('http'):
                                detail_url = 'https://www.china-hxzb.com' + detail_url
                        else:
                            project_name = await title_cell.inner_text()
                    
                    project_name = project_name.strip()
                    if not project_name or project_name == '公告标题':
                        continue
                    
                    logger.info(f"[{i}] 🎯 安徽项目: {project_name[:40]}...")
                    
                    # 进入详情页提取详细信息
                    detail_info = await self.extract_detail_info(detail_url)
                    
                    tender = TenderInfo(
                        keyword=keyword,
                        project_name=project_name,
                        region=region.strip(),
                        category=industry.strip(),
                        publish_date=publish_date.strip(),
                        detail_url=detail_url,
                        budget_amount=detail_info.get('budget', ''),
                        bid_deadline=detail_info.get('bid_deadline', ''),
                        bid_open_time=detail_info.get('bid_open_time', ''),
                        tender_org=detail_info.get('tender_org', ''),
                        qualification=detail_info.get('qualification', ''),
                        service_period=detail_info.get('service_period', ''),
                        project_code=detail_info.get('project_code', ''),
                        extracted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    results.append(tender)
                    logger.info(f"  ✓ 已提取: {project_name[:40]}...")
                    
                    # 延迟避免请求过快
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.debug(f"处理第{i}行时出错: {e}")
                    continue
            
            logger.info(f"✅ 本页共提取 {len(results)} 个安徽项目")
            
        except Exception as e:
            logger.error(f"提取列表数据失败: {e}")
        
        return results
    
    async def extract_detail_info(self, detail_url: str) -> Dict:
        """进入详情页提取详细信息 - 使用单页跳转模式"""
        info = {
            'budget': '',
            'bid_deadline': '',
            'bid_open_time': '',
            'tender_org': '',
            'qualification': '',
            'service_period': '',
            'project_code': ''
        }
        
        if not detail_url:
            return info
        
        try:
            # 在当前页面打开详情（避免开新页导致内存问题）
            await self.page.goto(detail_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 提取详情页信息
            # 方式1：从表格中提取
            detail_rows = await self.page.query_selector_all('.detail-table tr, .info-table tr, table tr, .content tr')
            for row in detail_rows:
                try:
                    cells = await row.query_selector_all('td, th')
                    if len(cells) >= 2:
                        label = await cells[0].inner_text()
                        value = await cells[1].inner_text()
                        label = label.strip()
                        value = value.strip()
                        
                        # 匹配常见字段
                        if any(k in label for k in ['预算', '金额', '价格', '限价', '采购预算']):
                            info['budget'] = value
                        elif any(k in label for k in ['截止时间', '投标截止', '递交截止', '响应截止']):
                            info['bid_deadline'] = value
                        elif any(k in label for k in ['开标时间', '开标日期']):
                            info['bid_open_time'] = value
                        elif any(k in label for k in ['招标人', '采购人', '建设单位', '采购单位']):
                            info['tender_org'] = value
                        elif any(k in label for k in ['资质', '资格要求', '投标人资格', '供应商资格']):
                            info['qualification'] = value
                        elif any(k in label for k in ['服务期', '合同期', '工期', '服务期限']):
                            info['service_period'] = value
                        elif any(k in label for k in ['项目编号', '招标编号', '采购编号', '项目代码']):
                            info['project_code'] = value
                except:
                    continue
            
            # 方式2：从页面文本中提取（正则匹配）
            if not any(info.values()):
                page_text = await self.page.inner_text('body')
                
                # 提取预算金额
                if not info['budget']:
                    budget_match = re.search(r'(\d+\.?\d*)\s*[万仟]?元', page_text)
                    if budget_match:
                        info['budget'] = budget_match.group(0)
                
                # 提取截止日期
                if not info['bid_deadline']:
                    date_patterns = [
                        r'(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?\s*\d{1,2}:\d{2})',
                        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
                    ]
                    for pattern in date_patterns:
                        date_match = re.search(pattern, page_text)
                        if date_match:
                            info['bid_deadline'] = date_match.group(1)
                            break
            
        except Exception as e:
            logger.debug(f"获取详情页失败 {detail_url}: {e}")
        
        return info
    
    async def extract_table_data(self) -> List[Dict]:
        """提取表格数据"""
        try:
            # 获取表格所有行
            rows = await self.page.query_selector_all('table tr')
            if not rows:
                return []
            
            # 尝试获取表头
            headers = []
            header_cells = await rows[0].query_selector_all('th, td')
            for cell in header_cells:
                text = await cell.inner_text()
                headers.append(text.strip())
            
            data = []
            for row in rows[1:]:  # 跳过表头
                cells = await row.query_selector_all('td')
                if len(cells) == len(headers):
                    row_data = {}
                    for i, cell in enumerate(cells):
                        text = await cell.inner_text()
                        row_data[headers[i]] = text.strip()
                        # 尝试获取链接
                        link = await cell.query_selector('a')
                        if link:
                            href = await link.get_attribute('href')
                            if href:
                                row_data['链接'] = href
                    data.append(row_data)
            
            return data
        except Exception as e:
            logger.warning(f"提取表格数据失败: {e}")
            return []
    
    async def extract_list_items(self) -> List[Dict]:
        """提取列表项数据"""
        items = []
        try:
            # 尝试多种列表项选择器
            for selector in self.COMMON_SELECTORS["list"]["list_items"]:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    for el in elements:
                        # 尝试提取标题
                        title = await self._extract_text_by_selectors(el, [
                            '.title', 'a', 'h3', 'h4', '.name', 'td:first-child'
                        ])
                        # 尝试提取日期
                        date = await self._extract_text_by_selectors(el, [
                            '.date', '.time', '.publish-date', 'td:last-child'
                        ])
                        # 尝试提取链接
                        url = ''
                        link_el = await el.query_selector('a')
                        if link_el:
                            url = await link_el.get_attribute('href') or ''
                        
                        if title:
                            items.append({
                                'title': title,
                                'date': date,
                                'url': url
                            })
                    break
        except Exception as e:
            logger.warning(f"提取列表项失败: {e}")
        return items
    
    async def _extract_text_by_selectors(self, parent, selectors: List[str]) -> str:
        """从多个选择器中尝试提取文本"""
        for selector in selectors:
            try:
                el = await parent.query_selector(selector)
                if el:
                    text = await el.inner_text()
                    return text.strip()
            except:
                continue
        return ''
    
    def save_results(self, append=False):
        """保存结果到JSON"""
        if not self.results:
            logger.warning("没有数据需要保存")
            return
        
        # 确保输出目录存在
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(self.config.OUTPUT_DIR, self.config.OUTPUT_FILENAME.replace('.csv', '.json'))
        
        # 转换为字典列表
        data_list = [item.to_dict() for item in self.results]
        
        # 构建JSON结构
        output_data = {
            'meta': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'region': '安徽',
                'keywords': self.config.SEARCH_KEYWORDS,
                'total_projects': len(self.results)
            },
            'projects': data_list
        }
        
        # 写入JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 结果已保存到: {output_path}")
        logger.info(f"📊 共保存 {len(self.results)} 个安徽项目")
    
    async def run(self):
        """运行爬虫"""
        try:
            # 初始化浏览器
            await self.init_browser()
            
            # 登录
            if not await self.login():
                logger.error("登录失败，程序退出")
                return
            
            # 遍历关键词搜索
            for i, keyword in enumerate(self.config.SEARCH_KEYWORDS):
                logger.info(f"[进度 {i+1}/{len(self.config.SEARCH_KEYWORDS)}] 开始搜索关键词: {keyword}")
                results = await self.search_keyword(keyword)
                self.results.extend(results)
                logger.info(f"当前累计采集: {len(self.results)} 条")
                
                # 每个关键词后保存结果（断点续传）
                if self.results:
                    self.save_results(append=(i > 0))
                
                await asyncio.sleep(2)  # 关键词间隔
            
            logger.info("爬虫执行完成！")
            
        except Exception as e:
            logger.exception(f"程序执行出错: {e}")
        finally:
            # 关闭浏览器
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()


# ==================== 主函数 ====================

async def main():
    """主入口"""
    config = Config()
    
    # 可以从环境变量读取敏感信息
    config.USERNAME = os.getenv('HX_USERNAME', config.USERNAME)
    config.PASSWORD = os.getenv('HX_PASSWORD', config.PASSWORD)
    config.HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'
    
    spider = HXZBSpider(config)
    await spider.run()


if __name__ == "__main__":
    asyncio.run(main())
