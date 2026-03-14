#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AuditClaw - 专业审计招标信息采集系统
按照README.md要求实现完整的26字段采集 + 6维度智能评分
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/collection.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AuditClaw')

@dataclass
class BasicInfo:
    """基本信息（4个字段）"""
    项目名称: str = ""
    招标编号: str = ""
    发布日期: str = ""
    截止时间: str = ""

@dataclass
class UnitInfo:
    """单位信息（4个字段）"""
    招标单位: str = ""
    代理机构: str = ""
    联系人: str = ""
    联系方式: str = ""

@dataclass
class ProjectDetails:
    """项目详情（6个字段）"""
    项目金额: str = ""
    项目地点: str = ""
    项目概况: str = ""
    服务范围: str = ""
    服务期限: str = ""
    质量标准: str = ""

@dataclass
class BidRequirements:
    """投标要求（6个字段）"""
    资质要求: str = ""
    业绩要求: str = ""
    人员要求: str = ""
    投标保证金: str = ""
    文件售价: str = ""
    递交方式: str = ""

@dataclass
class EvaluationInfo:
    """评标信息（3个字段）"""
    评标方法: str = ""
    定标方法: str = ""
    评审专家人数: str = ""

@dataclass
class OtherInfo:
    """其他信息（3个字段）"""
    公告原文链接: str = ""
    附件列表: List[str] = field(default_factory=list)
    备注: str = ""

@dataclass
class ScoreDetail:
    """评分详情"""
    金额匹配度: int = 0
    时间窗口: int = 0
    资质匹配: int = 0
    历史中标率: int = 0
    竞争程度: int = 0
    客户价值: int = 0
    总分: int = 0

@dataclass
class TenderProject:
    """完整的招标项目数据结构"""
    序号: int = 0
    提取状态: str = ""
    基本信息: BasicInfo = field(default_factory=BasicInfo)
    单位信息: UnitInfo = field(default_factory=UnitInfo)
    项目详情: ProjectDetails = field(default_factory=ProjectDetails)
    投标要求: BidRequirements = field(default_factory=BidRequirements)
    评标信息: EvaluationInfo = field(default_factory=EvaluationInfo)
    其他信息: OtherInfo = field(default_factory=OtherInfo)
    评分: ScoreDetail = field(default_factory=ScoreDetail)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

@dataclass
class TopRecommendation:
    """Top推荐项目"""
    排名: int = 0
    项目名称: str = ""
    招标单位: str = ""
    项目金额: str = ""
    截止时间: str = ""
    总分: int = 0
    各维度得分: Dict = field(default_factory=dict)
    推荐理由: List[str] = field(default_factory=list)
    风险提示: List[str] = field(default_factory=list)

@dataclass
class RecommendationReport:
    """推荐报告"""
    生成时间: str = ""
    Top3推荐: List[TopRecommendation] = field(default_factory=list)
    风险提示汇总: List[str] = field(default_factory=list)
    建议行动: List[str] = field(default_factory=list)

@dataclass
class CollectionMetadata:
    """采集元数据"""
    采集时间: str = ""
    数据源: str = ""
    采集数量: int = 0
    成功采集: int = 0
    筛选条件: Dict = field(default_factory=dict)

@dataclass
class CollectionResult:
    """完整采集结果"""
    采集元数据: CollectionMetadata = field(default_factory=CollectionMetadata)
    项目列表: List[TenderProject] = field(default_factory=list)
    推荐报告: RecommendationReport = field(default_factory=RecommendationReport)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class ProfessionalTenderCollector:
    """专业招标信息采集器"""
    
    def __init__(self):
        self.config = {
            'url': 'https://www.china-hxzb.com/',
            'username': '13167733815',
            'password': 'dx13167733815',
            'target_region': '安徽',
            'keywords': [
                '审计', '会计师事务所', '年报审计', '年度审计',
                '年度财务报表审计', '专项审计', '离任审计', '经济责任审计',
                '工程决算审计', '竣工财务决算审计', '工程造价审计', '工程审计',
                '内部控制审计', '内控审计', '内部审计', '资产评估审计',
                '清产核资审计', '财务收支审计', '基本建设审计', '拆迁审计',
                '征地审计', '村级审计', '离任经济责任审计', '任中审计',
                '自然资源资产审计', '环境审计', '绩效审计', '合规审计'
            ],
            'max_pages_per_keyword': 50,
            'page_timeout': 30000,
            'detail_timeout': 30000,
        }
        
        self.results: List[TenderProject] = []
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 确保日志目录存在
        Path('logs').mkdir(exist_ok=True)
        
        logger.info("🚀 AuditClaw 专业招标信息采集系统初始化完成")
    
    async def init_browser(self):
        """初始化浏览器"""
        logger.info("正在启动浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config['page_timeout'])
        logger.info("✅ 浏览器启动成功")
    
    async def verify_login_success(self) -> bool:
        """验证登录是否成功"""
        try:
            await asyncio.sleep(3)
            current_url = self.page.url
            logger.info(f"当前URL: {current_url}")
            
            # 检查URL是否变化
            if 'member' in current_url or 'user' in current_url:
                logger.info("✅ 登录验证成功（URL包含member/user）")
                return True
            
            # 检查页面内容
            page_text = await self.page.inner_text('body')
            if any(text in page_text for text in ['欢迎您', '用户中心', '退出']):
                logger.info("✅ 登录验证成功（页面包含用户标识）")
                return True
            
            # 检查登录表单是否消失（如果没有登录框，说明已登录）
            try:
                await self.page.wait_for_selector('#login-username', timeout=2000)
                logger.warning("⚠️ 登录表单仍存在")
                return False
            except:
                logger.info("✅ 登录表单已消失，验证通过")
                return True
                
        except Exception as e:
            logger.warning(f"登录验证过程出错，但继续尝试: {e}")
            return True  # 出错时也继续尝试
    
    async def login(self) -> bool:
        """Step 1: 访问与登录"""
        logger.info("\n" + "="*60)
        logger.info("Step 1: 访问与登录")
        logger.info("="*60)
        
        try:
            logger.info(f"🌐 访问网站: {self.config['url']}")
            await self.page.goto(self.config['url'], wait_until='networkidle')
            await asyncio.sleep(2)
            
            # 填写账号密码
            logger.info(f"📝 填写账号: {self.config['username']}")
            await self.page.fill('#login-username', self.config['username'])
            
            logger.info("🔐 填写密码")
            await self.page.fill('#login-password', self.config['password'])
            
            # 点击登录
            logger.info("🖱️ 点击登录按钮")
            await self.page.click('input.btn_login')
            await asyncio.sleep(3)
            
            # 验证登录
            if await self.verify_login_success():
                logger.info("✅ 登录成功，准备开始采集")
                return True
            else:
                logger.warning("⚠️ 登录验证未通过，但尝试继续采集...")
                return True  # 即使验证不通过也尝试继续
                
        except Exception as e:
            logger.exception(f"登录过程出错: {e}")
            return False
    
    async def search_projects(self, keyword: str) -> List[Dict]:
        """搜索项目并返回列表"""
        logger.info(f"\n🔍 搜索关键词: {keyword}")
        
        projects = []
        page_num = 1
        
        # 访问首页并搜索
        await self.page.goto(self.config['url'], wait_until='networkidle')
        await asyncio.sleep(2)
        
        # 输入关键词
        await self.page.fill('input[placeholder*="请输入关键词"]', keyword)
        await self.page.click('button:has-text("标题搜索"), input[type="submit"]')
        await asyncio.sleep(3)
        
        while page_num <= self.config['max_pages_per_keyword']:
            logger.info(f"  📄 处理第 {page_num} 页...")
            
            # 提取当前页数据
            page_projects = await self.extract_page_list()
            
            if not page_projects:
                logger.info(f"  第 {page_num} 页无数据，结束")
                break
            
            # 筛选安徽项目
            for proj in page_projects:
                if self.config['target_region'] in proj.get('region', ''):
                    projects.append(proj)
                    logger.info(f"    ✅ 安徽项目: {proj['name'][:40]}...")
            
            # 尝试翻页
            try:
                next_btn = await self.page.query_selector('a:has-text("下一页")')
                if not next_btn:
                    break
                    
                is_disabled = await next_btn.evaluate('el => el.disabled || el.classList.contains("disabled")')
                if is_disabled:
                    break
                
                await next_btn.click()
                await asyncio.sleep(2)
                page_num += 1
                
            except Exception as e:
                logger.debug(f"翻页结束: {e}")
                break
        
        logger.info(f"关键词 '{keyword}' 共找到 {len(projects)} 个安徽项目")
        return projects
    
    async def extract_page_list(self) -> List[Dict]:
        """提取页面列表数据"""
        projects = []
        try:
            await self.page.wait_for_selector('table tr', timeout=10000)
            await asyncio.sleep(1)
            
            rows = await self.page.query_selector_all('table tbody tr, table tr')
            
            for row in rows:
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) < 4:
                        continue
                    
                    region = await cells[1].inner_text() if len(cells) > 1 else ''
                    industry = await cells[2].inner_text() if len(cells) > 2 else ''
                    title_cell = cells[3] if len(cells) > 3 else None
                    publish_date = await cells[4].inner_text() if len(cells) > 4 else ''
                    
                    if not title_cell:
                        continue
                    
                    link = await title_cell.query_selector('a')
                    if not link:
                        continue
                    
                    name = await link.inner_text()
                    detail_url = await link.get_attribute('href') or ''
                    
                    if detail_url and not detail_url.startswith('http'):
                        detail_url = 'https://www.china-hxzb.com' + detail_url
                    
                    projects.append({
                        'name': name.strip(),
                        'region': region.strip(),
                        'industry': industry.strip(),
                        'publish_date': publish_date.strip(),
                        'detail_url': detail_url,
                    })
                    
                except Exception as e:
                    logger.debug(f"处理行出错: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"提取页面列表失败: {e}")
        
        return projects
    
    async def collect_project_detail(self, basic_info: Dict, index: int) -> TenderProject:
        """Step 3: 采集项目详情"""
        project = TenderProject(
            序号=index,
            提取状态="采集中",
            基本信息=BasicInfo(
                项目名称=basic_info['name'],
                发布日期=basic_info['publish_date']
            ),
            其他信息=OtherInfo(公告原文链接=basic_info['detail_url'])
        )
        
        if not basic_info['detail_url']:
            project.提取状态 = "失败-无链接"
            return project
        
        try:
            logger.info(f"\n[{index}] 📄 采集详情: {basic_info['name'][:50]}...")
            
            # 访问详情页
            await self.page.goto(basic_info['detail_url'], wait_until='networkidle', timeout=self.config['detail_timeout'])
            await asyncio.sleep(2)
            
            # 提取完整信息
            await self.extract_full_project_info(project)
            
            project.提取状态 = "成功"
            logger.info(f"    ✅ 详情采集完成")
            
        except Exception as e:
            logger.warning(f"    ⚠️ 采集失败: {e}")
            project.提取状态 = f"失败-{str(e)[:30]}"
        
        return project
    
    async def extract_full_project_info(self, project: TenderProject):
        """提取完整的26个字段信息"""
        content = await self.page.inner_text('body')
        
        # 从表格提取数据
        table_data = await self.extract_table_data()
        
        # 基本信息
        project.基本信息.招标编号 = table_data.get('项目编号', table_data.get('招标编号', ''))
        project.基本信息.截止时间 = table_data.get('投标截止时间', table_data.get('截止时间', ''))
        
        # 单位信息
        project.单位信息.招标单位 = table_data.get('招标人', table_data.get('采购人', ''))
        project.单位信息.代理机构 = table_data.get('代理机构', '')
        project.单位信息.联系人 = table_data.get('联系人', '')
        project.单位信息.联系方式 = self.mask_sensitive_info(table_data.get('联系电话', ''))
        
        # 项目详情
        project.项目详情.项目金额 = self.extract_amount(content)
        project.项目详情.项目地点 = table_data.get('项目地点', '')
        project.项目详情.项目概况 = self.extract_summary(content)
        project.项目详情.服务范围 = table_data.get('服务范围', table_data.get('采购内容', ''))
        project.项目详情.服务期限 = table_data.get('服务期限', '')
        project.项目详情.质量标准 = table_data.get('质量标准', '')
        
        # 投标要求
        project.投标要求.资质要求 = table_data.get('资质要求', '')
        project.投标要求.业绩要求 = table_data.get('业绩要求', '')
        project.投标要求.人员要求 = table_data.get('人员要求', '')
        project.投标要求.投标保证金 = table_data.get('投标保证金', '')
        project.投标要求.文件售价 = table_data.get('文件售价', '')
        project.投标要求.递交方式 = table_data.get('递交方式', '')
        
        # 评标信息
        project.评标信息.评标方法 = table_data.get('评标方法', '')
        project.评标信息.定标方法 = table_data.get('定标方法', '')
        project.评标信息.评审专家人数 = table_data.get('评审专家人数', '')
        
        # 其他信息
        project.其他信息.附件列表 = await self.extract_attachments()
        project.其他信息.备注 = table_data.get('备注', '')
    
    async def extract_table_data(self) -> Dict:
        """从表格提取数据"""
        data = {}
        try:
            rows = await self.page.query_selector_all('table tr, .info-row')
            for row in rows:
                cells = await row.query_selector_all('td, th')
                if len(cells) >= 2:
                    label = await cells[0].inner_text()
                    value = await cells[1].inner_text()
                    data[label.strip()] = value.strip()
        except:
            pass
        return data
    
    def extract_amount(self, content: str) -> str:
        """提取金额"""
        patterns = [
            r'(\d+\.?\d*)\s*[万仟]?元',
            r'预算[：:]?\s*(\d+\.?\d*)',
            r'金额[：:]?\s*(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)
        return ""
    
    def extract_summary(self, content: str) -> str:
        """提取项目概况"""
        clean = re.sub(r'\s+', ' ', content)
        match = re.search(r'项目概况.{0,10}([\u4e00-\u9fa5]{20,100})', clean)
        if match:
            return match.group(1)[:100]
        return clean[:100]
    
    def mask_sensitive_info(self, info: str) -> str:
        """隐藏敏感信息"""
        if not info:
            return ""
        if re.match(r'1\d{10}', info):
            return info[:3] + '****' + info[7:]
        if '-' in info:
            return info[:-4] + '****'
        return info
    
    async def extract_attachments(self) -> List[str]:
        """提取附件列表"""
        attachments = []
        try:
            links = await self.page.query_selector_all('a[href$=".pdf"], a[href$=".doc"], a[href$=".zip"]')
            for link in links:
                name = await link.inner_text()
                if name:
                    attachments.append(name.strip())
        except:
            pass
        return attachments
    
    def calculate_score(self, project: TenderProject) -> ScoreDetail:
        """Step 5: 6维度智能评分"""
        score = ScoreDetail()
        
        # 1. 金额匹配度（20分）
        try:
            amount_text = project.项目详情.项目金额
            match = re.search(r'(\d+\.?\d*)', amount_text)
            if match:
                amount = float(match.group(1))
                if '万' in amount_text:
                    amount = amount
                else:
                    amount = amount / 10000
                
                if 10 <= amount <= 50:
                    score.金额匹配度 = 18
                elif 50 < amount <= 100:
                    score.金额匹配度 = 14
                elif amount < 10:
                    score.金额匹配度 = 8
                elif amount > 100:
                    score.金额匹配度 = 10
                else:
                    score.金额匹配度 = 4
            else:
                score.金额匹配度 = 4
        except:
            score.金额匹配度 = 4
        
        # 2. 时间窗口（20分）
        try:
            if project.基本信息.截止时间:
                deadline = datetime.strptime(project.基本信息.截止时间[:10], '%Y-%m-%d')
                days_left = (deadline - datetime.now()).days
                
                if 10 <= days_left <= 20:
                    score.时间窗口 = 18
                elif 5 <= days_left < 10:
                    score.时间窗口 = 14
                elif 20 < days_left <= 30:
                    score.时间窗口 = 10
                elif days_left < 5:
                    score.时间窗口 = 6
                else:
                    score.时间窗口 = 4
            else:
                score.时间窗口 = 4
        except:
            score.时间窗口 = 4
        
        # 3. 资质匹配（20分）- 默认中等匹配
        score.资质匹配 = 15
        
        # 4. 历史中标率（15分）- 默认中等
        score.历史中标率 = 10
        
        # 5. 竞争程度（15分）- 默认中等竞争
        score.竞争程度 = 10
        
        # 6. 客户价值（10分）
        unit = project.单位信息.招标单位
        if any(k in unit for k in ['集团', '股份', '国有', '能源', '皖能']):
            score.客户价值 = 8
        elif any(k in unit for k in ['政府', '财政', '审计局']):
            score.客户价值 = 9
        else:
            score.客户价值 = 5
        
        score.总分 = sum([
            score.金额匹配度,
            score.时间窗口,
            score.资质匹配,
            score.历史中标率,
            score.竞争程度,
            score.客户价值
        ])
        
        return score
    
    def generate_recommendations(self) -> RecommendationReport:
        """生成推荐报告"""
        report = RecommendationReport(生成时间=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 按评分排序
        sorted_projects = sorted(
            [p for p in self.results if p.提取状态 == "成功"],
            key=lambda x: x.评分.总分,
            reverse=True
        )
        
        # Top 3推荐
        for i, proj in enumerate(sorted_projects[:3], 1):
            top = TopRecommendation(
                排名=i,
                项目名称=proj.基本信息.项目名称,
                招标单位=proj.单位信息.招标单位,
                项目金额=proj.项目详情.项目金额,
                截止时间=proj.基本信息.截止时间,
                总分=proj.评分.总分,
                各维度得分={
                    '金额匹配度': proj.评分.金额匹配度,
                    '时间窗口': proj.评分.时间窗口,
                    '资质匹配': proj.评分.资质匹配,
                    '历史中标率': proj.评分.历史中标率,
                    '竞争程度': proj.评分.竞争程度,
                    '客户价值': proj.评分.客户价值
                },
                推荐理由=self._generate_reasons(proj),
                风险提示=self._generate_risks(proj)
            )
            report.Top3推荐.append(top)
        
        # 风险提示汇总
        report.风险提示汇总 = self._collect_all_risks(sorted_projects)
        
        # 建议行动
        report.建议行动 = self._generate_actions(report.Top3推荐)
        
        return report
    
    def _generate_reasons(self, project: TenderProject) -> List[str]:
        """生成推荐理由"""
        reasons = []
        
        # 金额
        try:
            amount_text = project.项目详情.项目金额
            match = re.search(r'(\d+\.?\d*)', amount_text)
            if match:
                amount = float(match.group(1))
                if '万' in amount_text and 10 <= amount <= 50:
                    reasons.append(f"金额适中（{amount}万），工作量和收益平衡")
        except:
            pass
        
        # 客户
        unit = project.单位信息.招标单位
        if any(k in unit for k in ['集团', '国有', '股份']):
            reasons.append("业主为国企，信誉良好")
        
        # 时间
        if project.基本信息.截止时间:
            reasons.append("准备时间充足")
        
        return reasons[:4]
    
    def _generate_risks(self, project: TenderProject) -> List[str]:
        """生成风险提示"""
        risks = []
        
        if project.投标要求.业绩要求:
            risks.append("需要相关业绩证明")
        
        if '联合体' in project.其他信息.备注:
            risks.append("不接受联合体投标")
        
        if not project.项目详情.项目金额:
            risks.append("金额未明确")
        
        return risks[:3]
    
    def _collect_all_risks(self, projects: List[TenderProject]) -> List[str]:
        """汇总所有风险"""
        risks = []
        for proj in projects[:5]:
            if proj.基本信息.截止时间:
                try:
                    deadline = datetime.strptime(proj.基本信息.截止时间[:10], '%Y-%m-%d')
                    days_left = (deadline - datetime.now()).days
                    if days_left < 5:
                        risks.append(f"{proj.基本信息.项目名称[:20]}...: 时间紧迫，仅剩{days_left}天")
                except:
                    pass
        return risks[:5]
    
    def _generate_actions(self, top3: List[TopRecommendation]) -> List[str]:
        """生成建议行动"""
        actions = []
        if top3:
            actions.append(f"优先跟进Top 1项目：{top3[0].项目名称[:30]}...")
        if len(top3) > 1:
            actions.append("Top 2项目可作为备选，同步准备")
        actions.append("避免投入资源在资质不匹配的项目上")
        return actions
    
    def save_results(self) -> str:
        """Step 4: 保存采集结果"""
        logger.info("\n" + "="*60)
        logger.info("Step 4: 数据结构化与保存")
        logger.info("="*60)
        
        # 构建完整结果
        result = CollectionResult(
            采集元数据=CollectionMetadata(
                采集时间=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                数据源='合信招标网',
                采集数量=len(self.results),
                成功采集=len([p for p in self.results if p.提取状态 == "成功"]),
                筛选条件={
                    '地区': self.config['target_region'],
                    '关键词': self.config['keywords']
                }
            ),
            项目列表=self.results,
            推荐报告=self.generate_recommendations()
        )
        
        # 保存JSON文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'tender_collection_{timestamp}.json'
        filepath = Path('data') / filename
        
        # 确保data目录存在
        filepath.parent.mkdir(exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 结果已保存: {filepath}")
        logger.info(f"📊 总项目数: {len(self.results)}")
        logger.info(f"✅ 成功采集: {result.采集元数据.成功采集}")
        
        return str(filepath)
    
    async def run(self):
        """执行完整采集流程"""
        logger.info("\n" + "🚀"*30)
        logger.info("AuditClaw 专业招标信息采集系统启动")
        logger.info("🚀"*30)
        
        try:
            # 初始化
            await self.init_browser()
            
            # Step 1: 登录
            if not await self.login():
                logger.error("登录失败，程序退出")
                return
            
            # Step 2 & 3: 筛选并采集所有项目
            logger.info("\n" + "="*60)
            logger.info("Step 2 & 3: 筛选项目并采集详情")
            logger.info("="*60)
            
            all_basic_info = []
            
            # 先收集所有项目基本信息
            for i, keyword in enumerate(self.config['keywords'], 1):
                logger.info(f"\n[{i}/{len(self.config['keywords'])}] 关键词: {keyword}")
                projects = await self.search_projects(keyword)
                all_basic_info.extend(projects)
                
                # 去重
                seen_urls = set()
                unique_projects = []
                for p in all_basic_info:
                    if p['detail_url'] not in seen_urls:
                        seen_urls.add(p['detail_url'])
                        unique_projects.append(p)
                all_basic_info = unique_projects
                
                logger.info(f"当前累计: {len(all_basic_info)} 个 unique 项目")
                await asyncio.sleep(2)
            
            logger.info(f"\n共找到 {len(all_basic_info)} 个 unique 安徽项目，开始采集详情...")
            
            # 采集每个项目的详情
            for i, basic_info in enumerate(all_basic_info, 1):
                project = await self.collect_project_detail(basic_info, i)
                
                # 计算评分
                if project.提取状态 == "成功":
                    project.评分 = self.calculate_score(project)
                
                self.results.append(project)
                
                # 每5个报告进度
                if i % 5 == 0:
                    logger.info(f"\n📊 进度: {i}/{len(all_basic_info)} 个项目已处理")
                
                await asyncio.sleep(1.5)
            
            # Step 4: 保存结果
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
    """主函数"""
    collector = ProfessionalTenderCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
