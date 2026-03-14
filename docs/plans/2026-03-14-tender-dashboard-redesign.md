# 招标信息仪表板重新设计实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于JSON数据重新设计招标信息仪表板，采用专业商务风格（深色主题），突出Top 3推荐项目，使用Node.js静态生成，部署到GitHub Pages

**架构:** 创建Node.js脚本读取JSON文件，生成静态HTML文件。使用深色主题、卡片式布局，突出显示评分数据和推荐报告。最终推送到GitHub Pages进行部署。

**Tech Stack:** Node.js (v18+), Vanilla CSS, 无框架依赖

---

## Task 1: 创建项目结构和Node.js构建脚本

**文件:**
- 创建: package.json
- 创建: build.js
- 创建: src/template.html
- 创建: src/styles.css

**步骤1: 创建package.json**

内容包含项目信息、scripts（build/serve/deploy）

**步骤2: 创建build.js基础结构**

读取JSON、读取模板、生成HTML

**步骤3: 创建目录结构**

mkdir -p src

**步骤4: 提交**

git add package.json build.js src/
git commit -m "chore: 初始化构建脚本和项目结构"

---

## Task 2: 创建深色主题CSS样式

**文件:**
- 创建: src/styles.css

**步骤1: 创建深色主题CSS**

包含CSS变量、Header样式、统计卡片、Top 3推荐卡片样式、项目卡片样式、响应式布局

**步骤2: 提交**

git add src/styles.css
git commit -m "feat: 添加深色主题CSS样式"

---

## Task 3: 创建HTML模板

**文件:**
- 创建: src/template.html

**步骤1: 创建HTML模板**

使用占位符{{variable}}，包含Header、Top 3推荐、项目列表、Footer

**步骤2: 提交**

git add src/template.html
git commit -m "feat: 添加HTML模板"

---

## Task 4: 实现build.js数据转换逻辑

**文件:**
- 修改: build.js

**步骤1: 实现完整的生成逻辑**

- 读取JSON数据
- 计算统计数据
- 排序获取Top 3
- 生成所有项目卡片
- 生成Top 3卡片（含评分详情和进度条）
- 替换模板变量

**步骤2: 测试构建**

node build.js

**步骤3: 验证生成的HTML**

检查文件、本地预览

**步骤4: 提交**

git add build.js index.html
git commit -m "feat: 实现Node.js构建脚本和完整HTML生成"

---

## Task 5: 配置GitHub Pages部署

**文件:**
- 修改: package.json
- 创建: .github/workflows/deploy.yml

**步骤1: 更新package.json**

添加homepage字段

**步骤2: 创建GitHub Actions工作流**

mkdir -p .github/workflows
创建deploy.yml

**步骤3: 提交并推送到远端**

git add package.json .github/workflows/deploy.yml
git commit -m "chore: 配置GitHub Pages自动部署"
git push origin main

**步骤4: 在GitHub上启用Pages**

Settings → Pages → Source: GitHub Actions

**步骤5: 验证部署**

访问部署URL

---

## 完成标准

1. build.js能成功读取JSON并生成HTML
2. index.html使用深色主题和专业商务风格
3. Top 3推荐项目突出显示，含评分详情
4. 所有项目卡片展示完整信息
5. GitHub Actions配置完成
6. 代码已推送到远端
7. GitHub Pages部署成功并可访问

---

**执行选项：**

**1. Subagent-Driven（本会话）** - 按任务逐步执行，任务间审查
**2. Parallel Session（新会话）** - 在新会话中批量执行
