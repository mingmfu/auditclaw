# 招标信息采集专家Skill实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建一个完整的README.md技能文档，作为专业招标信息采集员的AI提示词，可直接投喂给Browser-use AI Agent使用。

**架构:** 基于之前的设计文档 (`docs/plans/2026-03-14-tender-collection-prompt-design.md`)，创建一个精简但完整的README.md技能文件，包含角色定义、任务步骤、数据字段、评分逻辑和输出格式。

**技术栈:** Markdown文档，无需编程，直接可用的Prompt Engineering产物

---

## 背景

设计文档已完成并保存至 `docs/plans/2026-03-14-tender-collection-prompt-design.md`。本实施计划将基于该设计创建最终的README.md技能文件。

---

## Task 1: 创建README.md技能文件

**文件:**
- 创建: `README.md` (根目录)

**步骤1: 创建完整的README.md文件**

内容应包含：
1. **角色定义** (Role) - 专业招标信息采集专家
2. **上下文** (Context) - 目标网站、登录凭证、筛选条件
3. **任务流程** (Task) - 5个步骤：访问登录、筛选项目、遍历采集、数据结构化、智能推荐
4. **数据字段** (Data Fields) - 26个关键字段的提取指引
5. **评估标准** (Evaluation Criteria) - 6维度评分算法
6. **输出格式** (Output Format) - JSON和文本报告格式
7. **约束条件** (Constraints) - 执行约束、超时处理、错误处理
8. **使用示例** (Examples) - 实际使用场景

**步骤2: 验证文件结构**

检查README.md是否包含所有必要章节：
- [ ] Role部分
- [ ] Context部分  
- [ ] Task部分（Step 1-5）
- [ ] Data Fields部分
- [ ] Evaluation Criteria部分
- [ ] Output Format部分
- [ ] Constraints部分
- [ ] Examples部分

**步骤3: 提交**

```bash
git add README.md
git commit -m "feat: 添加招标信息采集专家Skill文档

- 完整的AI Agent提示词，可直接投喂给Browser-use工具
- 包含5步采集流程、26个数据字段、6维度评分算法
- 提供JSON输出格式和智能推荐报告模板
- 详细的错误处理和约束条件"
```

**验证:**

README.md应满足：
1. 可直接复制投喂给AI使用
2. 包含所有必要的操作指令
3. JSON示例完整且可解析
4. 评分逻辑清晰可执行

---

## Task 2: 可选 - 创建快速启动指南

**文件:**
- 创建: `QUICKSTART.md` (根目录)

**步骤1: 创建快速启动指南**

包含：
1. 如何使用本Skill（3步）
2. 配合的工具推荐（browser-use, Playwright, etc.）
3. 常见问题和解决
4. 自定义配置说明（如何修改筛选条件、评分权重）

**步骤2: 提交**

```bash
git add QUICKSTART.md
git commit -m "docs: 添加快速启动指南

- 3步使用说明
- 工具推荐
- 常见问题解答
- 自定义配置方法"
```

---

## Task 3: 可选 - 创建示例输出文件

**文件:**
- 创建: `examples/sample-output.json` (examples目录)

**步骤1: 创建示例JSON输出**

基于设计文档中的示例，创建一个完整的、格式正确的JSON文件，展示预期的输出格式。

**步骤2: 提交**

```bash
mkdir -p examples
git add examples/sample-output.json
git commit -m "docs: 添加示例输出文件

- 展示完整的采集结果JSON格式
- 包含Top3推荐报告示例
- 便于用户理解预期输出"
```

---

## 完成标准

1. ✅ README.md已创建并提交
2. ✅ README.md包含所有必要章节
3. ✅ 文件可直接投喂给AI使用
4. ✅ 提供了JSON和文本两种输出格式
5. ✅ 包含完整的错误处理说明

---

## 后续行动

**如果只需要README.md（必需）：**
- 执行Task 1
- 完成！

**如果需要完整文档套件（可选）：**
- 执行Task 1 + Task 2 + Task 3
- 完成！

---

**计划完成！**

本实施计划已保存至 `docs/plans/2026-03-14-tender-collection-skill-implementation.md`

**执行选项：**

**1. Subagent-Driven（本会话）** - 我调度子代理按任务执行，任务间审查
**2. Parallel Session（新会话）** - 在新会话中打开并批量执行

**请选择执行方式？** (回复 1 或 2)
