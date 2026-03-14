const fs = require('fs');
const path = require('path');

// 读取采集的数据
const jsonPath = './data/anhui_audit_latest.json';
const jsonData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));

// 读取模板和样式
const templatePath = './src/template.html';
const template = fs.readFileSync(templatePath, 'utf8');
const styles = fs.readFileSync('./src/styles.css', 'utf8');

// 生成HTML
const html = generateHTML(jsonData, template, styles);

// 写入index.html
fs.writeFileSync('./index.html', html, 'utf8');
console.log('✅ index.html 生成成功');
console.log(`📊 共生成 ${jsonData.projects.length} 个项目 + Top 3 推荐`);

function generateHTML(data, template, styles) {
  let projects = data.projects;
  const meta = data.meta;
  
  // 为每个项目计算评分
  projects = projects.map(p => ({
    ...p,
    score: calculateScore(p),
    scoreDetails: calculateScoreDetails(p)
  }));
  
  // 按评分排序
  projects.sort((a, b) => b.score - a.score);
  
  // 获取Top 3
  const top3 = projects.slice(0, 3);
  
  // 统计数据
  const stats = calculateStats(projects);
  
  // 生成Top 3推荐卡片
  const topRecommendations = top3.map((p, index) => 
    generateTopRecommendationCard(p, index + 1)
  ).join('\n');
  
  // 生成所有项目卡片（按截止日期排序）
  const sortedProjects = [...projects].sort((a, b) => {
    const dateA = new Date(a.bid_deadline || '2099-12-31');
    const dateB = new Date(b.bid_deadline || '2099-12-31');
    return dateA - dateB;
  });
  
  const projectCards = sortedProjects.map((p, index) => 
    generateProjectCard(p, index)
  ).join('\n');
  
  // 替换模板变量
  let html = template;
  html = html.replace('{{styles}}', styles);
  html = html.replace('{{title}}', '安徽审计招标信息仪表板 - 专业版');
  html = html.replace(/{{siteName}}/g, '安徽审计招标信息仪表板');
  html = html.replace(/{{subtitle}}/g, `合信招标网安徽地区审计项目 | 共${meta.keywords.length}类关键词 | 实时更新`);
  html = html.replace(/{{updateTime}}/g, meta.generated_at);
  html = html.replace(/{{totalProjects}}/g, projects.length);
  html = html.replace(/{{highAmountCount}}/g, stats.highAmount);
  html = html.replace(/{{midAmountCount}}/g, stats.midAmount);
  html = html.replace(/{{unknownAmountCount}}/g, stats.unknownAmount);
  html = html.replace('{{topRecommendations}}', topRecommendations);
  html = html.replace('{{projectCards}}', projectCards);
  
  return html;
}

function calculateScore(project) {
  const amount = parseAmount(project.budget_amount);
  const deadlineDays = getDaysUntilDeadline(project.bid_deadline);
  
  // 1. 金额匹配度 (0-20分)
  let amountScore = 10;
  if (amount >= 10 && amount <= 50) amountScore = 18;
  else if (amount > 0 && amount < 10) amountScore = 12;
  else if (amount > 50 && amount <= 100) amountScore = 15;
  else if (amount > 100) amountScore = 8;
  
  // 2. 时间窗口 (0-20分)
  let timeScore = 10;
  if (deadlineDays >= 10 && deadlineDays <= 20) timeScore = 18;
  else if (deadlineDays >= 5 && deadlineDays < 10) timeScore = 15;
  else if (deadlineDays >= 20 && deadlineDays <= 30) timeScore = 12;
  else if (deadlineDays > 30) timeScore = 8;
  else if (deadlineDays >= 0 && deadlineDays < 5) timeScore = 5;
  
  // 3. 资质匹配 (0-20分)
  let qualificationScore = 18;
  
  // 4. 客户价值 (0-20分)
  let clientScore = 10;
  const name = project.project_name || '';
  if (name.includes('股份') || name.includes('集团') || name.includes('能源') || name.includes('水务')) {
    clientScore = 18;
  } else if (name.includes('公司') || name.includes('小学')) {
    clientScore = 14;
  }
  
  // 5. 历史中标率 (10分) - 简单判断
  let historyScore = 10;
  if (project.budget_amount && project.budget_amount.includes('成交')) {
    historyScore = 15;
  }
  
  // 6. 竞争程度 (10分) - 金额越大竞争越大
  let competitionScore = 10;
  if (amount > 1000) competitionScore = 5;
  else if (amount > 100) competitionScore = 7;
  else if (amount >= 10 && amount <= 50) competitionScore = 12;
  
  return amountScore + timeScore + qualificationScore + clientScore + historyScore + competitionScore;
}

function calculateScoreDetails(project) {
  const amount = parseAmount(project.budget_amount);
  const deadlineDays = getDaysUntilDeadline(project.bid_deadline);
  const name = project.project_name || '';
  
  return {
    '金额匹配度': amount >= 10 && amount <= 50 ? 18 : (amount > 0 ? 12 : 10),
    '时间窗口': deadlineDays >= 10 && deadlineDays <= 20 ? 18 : (deadlineDays >= 5 ? 15 : 10),
    '资质匹配': 18,
    '客户价值': (name.includes('股份') || name.includes('集团') || name.includes('能源')) ? 18 : 14,
    '历史中标率': project.budget_amount?.includes('成交') ? 15 : 10,
    '竞争程度': amount > 1000 ? 5 : (amount >= 10 && amount <= 50 ? 12 : 10)
  };
}

function getDaysUntilDeadline(deadlineStr) {
  if (!deadlineStr) return 999;
  try {
    const deadline = new Date(deadlineStr);
    const now = new Date();
    const diffTime = deadline - now;
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  } catch (e) {
    return 999;
  }
}

function calculateStats(projects) {
  let highAmount = 0;
  let midAmount = 0;
  let unknownAmount = 0;
  
  projects.forEach(p => {
    const amount = parseAmount(p.budget_amount);
    if (amount >= 30) highAmount++;
    else if (amount >= 10) midAmount++;
    else if (amount === 0) unknownAmount++;
  });
  
  return { highAmount, midAmount, unknownAmount };
}

function parseAmount(amountStr) {
  if (!amountStr || amountStr.includes('标项名称') || amountStr === '') return 0;
  
  const match = amountStr.match(/(\d+\.?\d*)/);
  if (!match) return 0;
  
  let value = parseFloat(match[1]);
  
  if (amountStr.includes('万元')) return value;
  else if (amountStr.includes('元')) return value / 10000;
  
  return value;
}

function formatAmount(amountStr) {
  const value = parseAmount(amountStr);
  if (value === 0) return '待查';
  if (value >= 10000) return `${(value / 10000).toFixed(2)}亿元`;
  return `${value.toFixed(2)}万元`;
}

function getAmountClass(amountStr) {
  const value = parseAmount(amountStr);
  if (value >= 30) return 'amount-high';
  if (value >= 10) return 'amount-mid';
  if (value > 0) return 'amount-low';
  return 'amount-unknown';
}

function generateTopRecommendationCard(project, rank) {
  const amount = formatAmount(project.budget_amount);
  const amountClass = getAmountClass(project.budget_amount);
  const score = project.score;
  const scoreDetails = project.scoreDetails;
  
  const scoreBreakdown = Object.entries(scoreDetails)
    .map(([key, value]) => {
      const percentage = (value / 20) * 100;
      return `
        <div class="score-item">
          <span>${key}</span>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="color: #60a5fa; font-weight: 600;">${value}</span>
            <div class="score-bar">
              <div class="score-fill" style="width: ${percentage}%"></div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  
  const reasons = [];
  if (parseAmount(project.budget_amount) >= 10 && parseAmount(project.budget_amount) <= 100) {
    reasons.push('✓ 金额适中，工作量和收益平衡');
  }
  const daysLeft = getDaysUntilDeadline(project.bid_deadline);
  if (daysLeft >= 5 && daysLeft <= 30) {
    reasons.push(`✓ 投标时间合理（剩余${daysLeft}天）`);
  }
  if (project.project_name?.includes('股份') || project.project_name?.includes('集团')) {
    reasons.push('✓ 大型企业/上市公司，信誉良好');
  }
  if (project.category?.includes('审计')) {
    reasons.push('✓ 符合资质要求的审计项目');
  }
  
  const reasonsHtml = reasons.map(r => `<div style="margin-bottom: 0.25rem;">${r}</div>`).join('');
  
  return `
    <div class="rec-card rank-${rank}">
      <div class="rank-badge">${rank}</div>
      <h3 class="project-title" style="padding-right: 3rem;">${project.project_name}</h3>
      
      <div class="meta-item" style="margin: 0.5rem 0;">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/>
          <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/>
          <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/>
        </svg>
        ${project.category || '审计服务'}
      </div>
      
      <div style="margin: 1rem 0;">
        <span class="amount-badge ${amountClass}">${amount}</span>
      </div>
      
      <div class="score-display">
        ${score}
        <span class="score-label">/ 100分</span>
      </div>
      
      <div class="score-breakdown">
        ${scoreBreakdown}
      </div>
      
      <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
        <div style="font-size: 0.75rem; color: #34d399; margin-bottom: 0.5rem; font-weight: 600;">推荐理由</div>
        <div style="font-size: 0.75rem; color: #cbd5e1; line-height: 1.5;">${reasonsHtml}</div>
      </div>
      
      <a href="${project.detail_url}" target="_blank" class="btn-primary" style="margin-top: 1rem;" onclick="showLoginHelp(event)">
        查看详情
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
          <polyline points="15 3 21 3 21 9"/>
          <line x1="10" y1="14" x2="21" y2="3"/>
        </svg>
      </a>
    </div>
  `;
}

function generateProjectCard(project, index) {
  const amount = formatAmount(project.budget_amount);
  const amountClass = getAmountClass(project.budget_amount);
  const projectId = `project-${index}`;
  
  const detailFields = [];
  
  if (project.qualification?.trim()) {
    detailFields.push(`<div class="detail-field"><strong>资质要求：</strong>${project.qualification}</div>`);
  }
  if (project.service_period?.trim()) {
    detailFields.push(`<div class="detail-field"><strong>服务期限：</strong>${project.service_period}</div>`);
  }
  if (project.category?.trim()) {
    detailFields.push(`<div class="detail-field"><strong>项目类别：</strong>${project.category}</div>`);
  }
  if (project.keyword?.trim()) {
    detailFields.push(`<div class="detail-field"><strong>匹配关键词：</strong>${project.keyword}</div>`);
  }
  if (project.score) {
    detailFields.push(`<div class="detail-field"><strong>推荐指数：</strong><span style="color: #fbbf24; font-weight: 600;">${project.score}分</span></div>`);
  }
  
  const detailsHtml = detailFields.length > 0 
    ? detailFields.join('') 
    : '<div class="detail-field" style="color: #64748b;">暂无详细信息，请查看招标原文</div>';
  
  const isUrgent = isDeadlineUrgent(project.bid_deadline);
  const deadlineClass = isUrgent ? 'style="color: #ef4444; font-weight: 600;"' : '';
  const deadlineIcon = isUrgent ? '⚠️ ' : '';
  
  return `
    <div class="project-card" id="${projectId}">
      <div class="card-header">
        <span class="amount-badge ${amountClass}">${amount}</span>
        <span class="tag" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa;">${project.region}</span>
      </div>
      
      <h3 class="project-title">${project.project_name}</h3>
      
      <div class="tags">
        ${project.category ? `<span class="tag">${project.category}</span>` : ''}
        ${project.keyword ? `<span class="tag" style="background: rgba(139, 92, 246, 0.2); color: #a78bfa;">${project.keyword}</span>` : ''}
        ${project.publish_date ? `<span class="tag" style="background: rgba(16, 185, 129, 0.2); color: #34d399;">发布：${project.publish_date}</span>` : ''}
      </div>
      
      <div class="project-meta">
        <div class="meta-item" ${deadlineClass}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          ${deadlineIcon}截止：${project.bid_deadline || '待定'}
        </div>
      </div>
      
      <div class="details-section" id="details-${projectId}" style="display: none; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
        <h4 style="font-size: 0.875rem; color: #60a5fa; margin-bottom: 0.75rem; font-weight: 600;">📋 详细信息</h4>
        <div style="font-size: 0.8125rem; line-height: 1.6; color: #cbd5e1;">${detailsHtml}</div>
      </div>
      
      <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
        <button onclick="toggleDetails('${projectId}')" class="btn-primary" style="flex: 1; background: #334155;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span id="btn-text-${projectId}">查看详情</span>
        </button>
        
        <a href="${project.detail_url}" target="_blank" class="btn-primary" style="flex: 1;" onclick="showLoginHelp(event)">
          招标原文
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
        </a>
      </div>
    </div>
  `;
}

function isDeadlineUrgent(deadlineStr) {
  if (!deadlineStr) return false;
  
  try {
    const deadline = new Date(deadlineStr);
    const now = new Date();
    const diffTime = deadline - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return diffDays >= 0 && diffDays <= 3;
  } catch (e) {
    return false;
  }
}
