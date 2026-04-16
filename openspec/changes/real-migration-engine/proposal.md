# 真实迁移执行引擎

## Problem

当前迁移执行步骤是**纯前端模拟**：点击"开始执行"后只是 `sleep(300ms)` 假装成功，配置并没有真正写入腾讯云 CLB。具体缺失：

1. **腾讯云写入 API 封装**：`clb_service.py` 仅有只读方法（Describe），无 `CreateListener`、`CreateRule`、`ModifyListener` 等写入方法
2. **迁移执行引擎**：`app/services/migration/__init__.py` 是空文件，无编排调度逻辑
3. **后端执行路由**：`migration_routes.py` 全部路由返回硬编码 `{success: true}`，无任何业务逻辑
4. **前端执行步骤**：`execute/index.js` 不调用后端 API，纯前端循环 + sleep
5. **二次确认弹窗**：规格要求每个写操作需用户确认，完全未实现
6. **状态持久化**：`MigrationPlanItem` 数据模型设计完善但从未被使用

## Solution

实现真实的迁移执行流程，核心原则：**所有写操作必须经用户确认，绝不静默改动**。

### 执行流程
```
前端点击"开始执行"
  → 后端逐项处理 planItems
    → 对每项：拉取目标端已有配置 → 检测冲突 → 弹窗确认 → 调用腾讯云 API → 记录结果
  → 前端实时展示进度和日志
```

### 本次范围（MVP）
- 创建监听器（CreateListener）— TCP/UDP/HTTP/HTTPS 四种协议
- 创建转发规则（CreateRule）— HTTP/HTTPS 七层规则
- 写前冲突检测（DescribeListeners 检查端口占用）
- 二次确认弹窗（逐项确认 + 批量确认模式）
- 失败处理（重试/跳过/终止）
- 后端执行引擎 + 状态持久化到 MySQL

### 本次不做
- 修改已有监听器（ModifyListener）— 风险高，暂不做
- 健康检查/会话保持/ACL 高级参数写入 — 后续迭代
- WebSocket 实时推送 — 先用轮询，后续升级
- 创建 CLB 实例 — 上次迭代已决定本期不做

## Scope

### Modified Capabilities
- `tencent-clb-writer`: 实现 CreateListener / CreateRule 写入方法，冲突检测，二次确认
- `migration-execution`: 实现后端执行引擎，状态持久化，前端对接后端 API

## Impact

- 后端新增：`app/services/tencent/clb_writer.py`（写入服务），`app/services/migration/engine.py`（执行引擎）
- 后端改造：`migration_routes.py` 实现真实路由逻辑
- 前端改造：`execute/index.js` 对接后端 API，实现二次确认弹窗
- 数据库：激活 `migration_plan_item` 表的读写
