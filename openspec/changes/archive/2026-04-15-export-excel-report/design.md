# 导出 Excel 报告 — 设计文档

## Goals

- 生成面向业务人员可读的 Excel 报告（5 个 Sheet，中文字段名，颜色区分状态）
- 保留 JSON 导出作为技术辅助
- 纯前端生成，无需后端改造

**Non-Goals:**
- 不修改报告页面的展示逻辑（只改导出）
- 不支持服务端生成 Excel（纯浏览器端）

## 架构决策

### 决策 1：使用 SheetJS (xlsx) 库

**选择**：`xlsx` npm 包（SheetJS Community Edition）

**理由**：
- 纯浏览器端运行，无需后端
- 支持样式（通过 `xlsx-js-style` 扩展）
- 体积约 800KB，可接受
- CDN 或本地均可引入
- 免费开源（MIT）

**引入方式**：下载到 `public/js/` 本地（不引用公网 CDN，与项目规范一致）

### 决策 2：5 个 Sheet 的数据来源

| Sheet | 数据来源 |
|-------|---------|
| 封面·迁移摘要 | `state.credentials` + `state.executionStatus` |
| 实例迁移概览 | `state.instanceMappings` + `state.executionStatus.items` |
| 监听器配置明细 | `state.planItems` + `state.executionStatus.items` |
| 不兼容项说明 | `state.mappingResults`（各组的 incompatible_items） |
| 操作日志 | `state.executionStatus.items`（包含 error 信息） |

### 决策 3：颜色方案

| 状态 | 背景色（hex） | 前景色 |
|------|-------------|-------|
| 标题行 | `#1565C0`（深蓝） | `#FFFFFF` |
| 成功 | `#E8F5E9`（浅绿） | `#000000` |
| 失败 | `#FFEBEE`（浅红） | `#000000` |
| 跳过 | `#F5F5F5`（浅灰） | `#000000` |
| 不兼容 | `#FFF3E0`（浅橙） | `#000000` |

### 决策 4：封面设计

封面 Sheet 不用表格，用"标签-值"对的形式：

```
迁移报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
迁移时间        2026-04-15 12:00:00
源端账号        阿里云（cn-guangzhou）
目标端账号      腾讯云（ap-guangzhou）
迁移实例数      2 个
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
整体结论        ✓ 全部迁移成功
成功率          100%（6/6 项）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 决策 5：字段名映射（中英对照）

| 英文原始 | Excel 中文列名 |
|---------|--------------|
| `listener_protocol` | 监听协议 |
| `listener_port` | 监听端口 |
| `scheduler` | 调度算法 |
| `health_check` | 健康检查 |
| `sticky_session` | 会话保持 |
| `bandwidth` | 带宽限制 |
| `success` | 成功 |
| `failed` | 失败 |
| `skipped` | 跳过 |
| `incompatible` | 不兼容 |
| `source_description` | 配置项 |
| `reason` | 不兼容原因 |
| `suggestion` | 建议处理方式 |
| `recommendation` | 推荐替代方案 |

## 实现方案

```
report/index.js
  └── exportExcel()
       ├── Sheet1: buildCoverSheet(state)
       ├── Sheet2: buildInstanceSheet(state)
       ├── Sheet3: buildListenerSheet(state)
       ├── Sheet4: buildIncompatibleSheet(state)
       └── Sheet5: buildLogSheet(state)
       └── xlsx.writeFile(wb, filename)
```

## 引入 SheetJS

下载 `xlsx.full.min.js`（约 800KB）到 `public/js/xlsx.full.min.js`，在 `report/index.js` 中通过动态 `<script>` 标签加载（避免影响其他步骤的加载速度）。
