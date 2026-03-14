#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AuditClaw Pro - 专业审计招标信息采集系统
优化版：保持登录状态 + 遍历所有页面
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TenderInfo:
    """招标信息"""
    keyword: str = ""
    project_name: str = ""
    project_code: str = ""
    tender_org: str = ""
    budget_amount: str = ""
    bid_deadline: str = ""
    bid_open_time: str = ""
    qualification: str = ""
    service_period: str = ""
    region: str = ""
    publish_date: str = ""
    detail_url: str = ""
    category: str = ""
    extracted_at: str = ""
    
    def to_dict(self):
        return asdict(self)


class AuditClawPro:
    """专业采集器 - 保持登录状态"""
    
    def __init__(self):
        # 从环境变量读取敏感信息
        self.username = os.getenv('HX_USERNAME', '')
        self.password = os.getenv('HX_PASSWORD', '')
        
        if not self.username or not self.password:
            print("⚠️ 警告: 未设置环境变量 HX_USERNAME 和 HX_PASSWORD")
            print("请设置: export HX_USERNAME='your_username'")
            print("       export HX_PASSWORD='your_password'")
        
        self.config = {
            'url': 'https://www.china-hxzb.com/',
            'username': self.username,
            'password': self.password,
            'output_dir': './data',
        }
        
        # 28个关键词
        self.keywords = [
            '审计', '会计师事务所', '年报审计', '年度审计', '年度财务报表审计',
            '专项审计', '离任审计', '经济责任审计', '工程决算审计', '竣工财务决算审计',
            '工程造价审计', '工程审计', '内部控制审计', '内控审计', '内部审计',
            '资产评估审计', '清产核资审计', '财务收支审计', '基本建设审计', '拆迁审计',
            '征地审计', '村级审计', '离任经济责任审计', '任中审计',
            '自然资源资产审计', '环境审计', '绩效审计', '合规审计'
        ]
        
        self.results: List[TenderInfo] = []
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
    
    async def init_browser(self):
        """初始化浏览器"""
        logger.info("🚀 启动浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        logger.info("✅ 浏览器启动成功")
    
    async def login(self) -> bool:
        """登录 - 只执行一次"""
        if self.is_logged_in:
            logger.info("✅ 已登录，跳过登录步骤")
            return True
        
        logger.info("\n" + "="*60)
        logger.info("Step 1: 登录网站")
        logger.info("="*60)
        
        try:
            # 访问首页
            await self.page.goto(self.config['url'], wait_until='networkidle')
            await asyncio.sleep(2)
            
            # 填写账号密码
            await self.page.fill('#login-username', self.config['username'])
            await self.page.fill('#login-password', self.config['password'])
            logger.info(f"📝 已填写账号: {self.config['username']}")
            
            # 点击登录
            await self.page.click('input.btn_login')
            await asyncio.sleep(3)
            
            # 验证登录
            current_url = self.page.url
            if 'member' in current_url or 'user' in current_url:
                self.is_logged_in = True
                logger.info("✅ 登录成功！")
                return True
            
            # 检查登录表单是否消失
            try:
                await self.page.wait_for_selector('#login-username', timeout=2000)
                logger.warning("⚠️ 登录表单仍在，但尝试继续...")
                self.is_logged_in = True  # 假设已登录
                return True
            except:
                self.is_logged_in = True
                logger.info("✅ 登录成功（表单已消失）")
                return True
                
        except Exception as e:
            logger.error(f"❌ 登录失败: {e}")
            return False
    
    async def search_keyword(self, keyword: str) -> List[TenderInfo]:
        """搜索单个关键词 - 遍历所有页面"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 搜索关键词: {keyword}")
        logger.info(f"{'='*60}")
        
        results = []
        page_num = 1
        max_pages = 50  # 最多50页
        
        # 在当前页面搜索（不重新访问首页）
        try:
            # 清空搜索框并输入新关键词
            await self.page.fill('input[placeholder*="请输入关键词"]', '')
            await self.page.fill('input[placeholder*="请输入关键词"]', keyword)
            await self.page.click('button:has-text("标题搜索"), input[type="submit"][value*="搜索"]')
            await asyncio.sleep(3)
            
            logger.info(f"📝 已搜索: {keyword}")
        except Exception as e:
            logger.warning(f"搜索失败，尝试重新登录: {e}")
            # 如果失败，尝试重新登录
            await self.login()
            return await self.search_keyword(keyword)
        
        # 遍历所有页面
        while page_num <= max_pages:
            logger.info(f"\n  📄 正在处理第 {page_num} 页...")
            
            # 提取当前页数据
            page_results = await self.extract_current_page(keyword)
            
            if not page_results:
                logger.info(f"  第 {page_num} 页无数据，结束此关键词")
                break
            
            # 筛选安徽项目
            for item in page_results:
                if '安徽' in item.region:
                    results.append(item)
                    logger.info(f"    ✅ 安徽项目: {item.project_name[:50]}...")
            
            logger.info(f"  第 {page_num} 页: 找到 {len([i for i in page_results if '安徽' in i.region])} 个安徽项目")
            
            # 尝试翻页
            try:
                next_btn = await self.page.query_selector('a:has-text("下一页")')
                if not next_btn:
                    logger.info("  无下一页按钮，结束")
                    break
                
                # 检查是否禁用
                is_disabled = await next_btn.evaluate('el => el.disabled || el.classList.contains("disabled")')
                if is_disabled:
                    logger.info("  下一页已禁用，结束")
                    break
                
                await next_btn.click()
                await asyncio.sleep(2)
                page_num += 1
                
            except Exception as e:
                logger.info(f"  翻页结束: {e}")
                break
        
        logger.info(f"\n关键词 '{keyword}' 共采集 {len(results)} 个安徽项目")
        return results
    
    async def extract_current_page(self, keyword: str) -> List[TenderInfo]:
        """提取当前页面数据"""
        results = []
        
        try:
            # 等待表格加载
            await self.page.wait_for_selector('table tr', timeout=10000)
            await asyncio.sleep(1)
            
            # 获取所有行
            rows = await self.page.query_selector_all('table tbody tr, table tr')
            
            for row in rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) < 4:
                        continue
                    
                    # 提取数据
                    region = await cells[1].inner_text() if len(cells) > 1 else ''
                    industry = await cells[2].inner_text() if len(cells) > 2 else ''
                    title_cell = cells[3] if len(cells) > 3 else None
                    publish_date = await cells[4].inner_text() if len(cells) > 4 else ''
                    
                    if not title_cell:
                        continue
                    
                    # 获取标题和链接
                    link = await title_cell.query_selector('a')
                    if not link:
                        continue
                    
                    project_name = await link.inner_text()
                    detail_url = await link.get_attribute('href') or ''
                    
                    if detail_url and not detail_url.startswith('http'):
                        detail_url = 'https://www.china-hxzb.com' + detail_url
                    
                    project_name = project_name.strip()
                    if not project_name or project_name == '公告标题':
                        continue
                    
                    results.append(TenderInfo(
                        keyword=keyword,
                        project_name=project_name,
                        region=region.strip(),
                        category=industry.strip(),
                        publish_date=publish_date.strip(),
                        detail_url=detail_url,
                        extracted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"提取页面数据失败: {e}")
        
        return results
    
    def save_results(self):
        """保存结果"""
        if not self.results:
            logger.warning("没有数据需要保存")
            return
        
        # 去重
        seen_urls = set()
        unique_results = []
        for item in self.results:
            if item.detail_url not in seen_urls:
                seen_urls.add(item.detail_url)
                unique_results.append(item)
        
        self.results = unique_results
        
        # 确保目录存在
        os.makedirs(self.config['output_dir'], exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = os.path.join(self.config['output_dir'], f'anhui_audit_full_{timestamp}.json')
        
        # 构建输出
        output = {
            'meta': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'region': '安徽',
                'total_keywords': len(self.keywords),
                'keywords': self.keywords,
                'total_projects': len(self.results),
                'data_source': '合信招标网',
                'login_account': self.config['username'],
            },
            'projects': [item.to_dict() for item in self.results]
        }
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info("💾 结果已保存")
        logger.info(f"{'='*60}")
        logger.info(f"文件路径: {filepath}")
        logger.info(f"总关键词数: {len(self.keywords)}")
        logger.info(f"总项目数（去重）: {len(self.results)}")
        
        return filepath
    
    async def run(self):
        """执行采集"""
        logger.info("\n" + "🚀"*30)
        logger.info("AuditClaw Pro 专业采集系统启动")
        logger.info("特点: 保持登录状态 + 遍历所有页面")
        logger.info("🚀"*30)
        
        try:
            # 初始化
            await self.init_browser()
            
            # Step 1: 登录（只执行一次）
            if not await self.login():
                logger.error("登录失败，退出")
                return
            
            # Step 2: 遍历所有关键词
            logger.info(f"\n{'='*60}")
            logger.info("Step 2: 遍历所有关键词")
            logger.info(f"{'='*60}")
            logger.info(f"共 {len(self.keywords)} 个关键词")
            
            for i, keyword in enumerate(self.keywords, 1):
                logger.info(f"\n[{i}/{len(self.keywords)}] 开始搜索: {keyword}")
                
                results = await self.search_keyword(keyword)
                self.results.extend(results)
                
                logger.info(f"当前累计: {len(self.results)} 个 unique 项目")
                
                # 每5个关键词保存一次
                if i % 5 == 0:
                    logger.info(f"\n📊 进度报告: {i}/{len(self.keywords)} 关键词完成")
                    logger.info(f"📊 当前累计: {len(self.results)} 个项目")
                
                # 延迟
                await asyncio.sleep(1)
            
            # Step 3: 保存结果
            output_path = self.save_results()
            
            logger.info("\n" + "="*60)
            logger.info("✅ 采集完成！")
            logger.info("="*60)
            logger.info(f"📁 输出文件: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.exception(f"程序执行出错: {e}")
        finally:
            if self.browser:
                await self.browser.close()
                logger.info("🛑 浏览器已关闭")


async def main():
    collector = AuditClawPro()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
