# 配置映射改版 — 设计文档

## Goals

- 实现实例维度的源端↔目标端关联，让用户清晰看到"哪些配置迁到哪个实例"
- 提供两层可视化对比（实例总览 → 监听器字段级），JSON 对比作为辅助手段
- 不兼容项自动推荐替代方案，减少用户手动查阅文档的成本
- 多对一场景接入端口冲突检测和处理

**Non-Goals:**
- 本次不做"创建新实例"功能，目标端只支持选择已有实例
- 不做一对多（拆分）场景
- 不做字段级 diff（第三层），两层足够

## 架构决策

### 决策 1：步骤2 实例关联 — 同页双栏

**选择**：左右两栏在同一页面完成源端选择和目标端关联

**理由**：
- 一步到位，减少页面跳转
- 左栏勾选源端后，右栏即时出现对应的目标端下拉，关联关系直观
- 实现方式：左栏复用现有阿里云实例表格（增加列），右栏用 `<select>` 下拉框

### 决策 2：目标端下拉内容

**选择**：只展示实例ID和名称

**理由**：
- 简洁，避免下拉框过长
- 目标端实例详情可以通过 hover 或 tooltip 补充

### 决策 3：数据流重构 — 实例维度传递

**选择**：映射引擎接口改为按实例分组传参，返回结果也按实例分组

**现有数据流**：
```
allListeners[] → engine.map_full_config() → MappingItem[]（扁平）
```

**新数据流**：
```
{
  instanceMappings: [
    { sourceId: "lb-xxx", targetId: "lb-yyy", listeners: [...] },
    { sourceId: "lb-aaa", targetId: "lb-yyy", listeners: [...] }  // 多对一
  ]
} → engine.map_by_instance() → { instanceId: MappingItem[] }（分组）
```

### 决策 4：配置对比 — 两层展示

**选择**：实例总览 → 监听器对比，JSON 放侧边抽屉

**Layer 1 — 实例总览（Collapsible header）**：
- 标题：`源端实例A (lb-xxx) → 目标端实例X (lb-yyy)`
- 统计 badge：`3项✓  1项⚠  0项✗`
- [JSON] 按钮（触发侧边抽屉）

**Layer 2 — 监听器对比（Collapsible body）**：
- 每个监听器一个卡片
- 卡片内：表格形式，每行一个配置字段
- 列：字段名 | 阿里云值 | → | 腾讯云值 | 状态
- 转发规则平铺在监听器卡片下方

### 决策 5：不兼容项推荐逻辑 — 功能最接近优先

**选择**：优先推荐功能最接近的替代方案

**推荐映射表**：
```
sch (源地址哈希) → WRR (加权轮询)     # 腾讯云 CLB 不支持 IP_HASH
tch (四元组哈希) → WRR
qch (五元组哈希) → LEAST_CONN (最小连接数)
```

**实现方式**：`IncompatibleDetail` 增加 `recommendation` 和 `alternatives` 字段
- `recommendation`: 自动推荐的值
- `alternatives`: 所有可选替代方案列表（供下拉框使用）

### 决策 6：端口冲突检测时机

**选择**：用户在步骤2关联目标端时实时检测

**触发条件**：两个或以上源端实例关联到同一个目标端
**检测方式**：前端收集这些源端的监听器列表，调用 `POST /api/mapping/conflict-detect`
**展示方式**：页面底部冲突面板，每项提供 4 个选项（保留A/保留B/跳过/改端口）

### 决策 7：JSON 抽屉组件

**选择**：右侧滑出面板（Materialize Sidenav 或自定义 CSS）

**实现**：
- 宽度 40%，带遮罩
- 上下分栏：阿里云原始 JSON + 腾讯云映射后 JSON
- `<pre>` 标签 + `JSON.stringify(data, null, 2)` 格式化

## 项目结构变更

```
public/js/modules/
├── aliyun/index.js        ← 重写为"实例关联"
├── mapping/index.js       ← 重写为"配置对比"
├── plan/index.js          ← 小改：按实例分组展示
├── components/
│   └── json-drawer.js     ← 新增：JSON 侧边抽屉组件
app/
├── routes/mapping_routes.py    ← 改：按实例分组接口
├── routes/tencent_routes.py    ← 增：目标端实例列表
├── services/mapper/engine.py   ← 改：按实例分组 + 推荐逻辑
├── services/mapper/models.py   ← 改：IncompatibleDetail 增加字段
```

## Risks

- **[风险] 目标端实例列表可能很多** → 下拉框只展示 ID+名称，后续可加搜索过滤
- **[风险] 实时冲突检测增加交互延迟** → 冲突检测用纯前端逻辑（对比 protocol+port），不走后端 API
- **[取舍] 不做字段级 diff（第三层）** → 两层已足够，字段级差异通过监听器卡片内的表格行展示
