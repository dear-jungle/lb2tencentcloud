# 配置映射改版 — 任务清单

## 1. 后端改造

- [x] 1.1 映射引擎增加按实例分组映射方法 `map_by_instance(instance_mappings)` — 接收 `[{sourceId, targetId, listeners}]`，返回 `{sourceId: MappingItem[]}`
- [x] 1.2 `IncompatibleDetail` 模型增加 `recommendation`（推荐值）和 `alternatives`（可选列表）字段
- [x] 1.3 映射引擎推荐逻辑：为不兼容的调度算法/会话保持等字段填充 `recommendation` 和 `alternatives`（功能最接近优先）
- [x] 1.4 `mapping_routes.py` 新增 `POST /api/mapping/execute-by-instance` 接口 — 接收按实例分组的数据，返回按实例分组的映射结果
- [x] 1.5 `tencent_routes.py` 新增 `GET /api/tencent/clb/instances` 接口 — 返回目标地域下的 CLB 实例列表（ID + 名称）

## 2. 步骤2 — 实例关联页面（重写 aliyun/index.js）

- [x] 2.1 页面布局：左右两栏（Materialize `col s6`），左栏源端实例列表（复选框 + 实例信息），右栏对应的目标端下拉选择器
- [x] 2.2 左栏：加载阿里云实例列表，展示实例ID、名称、VIP、监听器摘要，支持全选
- [x] 2.3 右栏：勾选源端后出现目标端下拉框（`<select>` browser-default），选项从腾讯云实例列表 API 获取，展示 ID+名称
- [x] 2.4 多对一端口冲突检测：前端纯逻辑，当多个源端选同一目标端时，收集所有监听器比对 `(protocol, port)`，冲突时底部展示冲突面板
- [x] 2.5 冲突处理 UI：每个冲突项提供下拉选择（保留A / 保留B / 跳过）
- [x] 2.6 下一步校验：所有选中源端必须关联目标端
- [x] 2.7 数据输出：保存 `state.instanceMappings` 到 StateManager

## 3. 步骤3 — 配置对比页面（重写 mapping/index.js）

- [x] 3.1 调用 `POST /api/mapping/execute-by-instance` 传入 `state.instanceMappings`，获取按实例分组的映射结果
- [x] 3.2 顶部统计卡片：总项、完全映射、需确认、不兼容（跨所有实例汇总）
- [x] 3.3 Layer1 — 实例总览：Materialize Collapsible，header 展示"源端A → 目标X"+ 统计 badge + [JSON] 按钮
- [x] 3.4 Layer2 — 监听器对比卡片：展开后每个监听器一个卡片，卡片内表格（字段名 | 源值 | → | 目标值 | 状态图标），转发规则平铺在监听器卡片下方
- [x] 3.5 不兼容项交互：`recommendation` 有值时展示为 `<select>` 下拉框（默认选推荐值，options 来自 `alternatives`），无值时展示红色"不兼容"文本
- [x] 3.6 用户修改推荐值后，更新 `state.mappingResults` 中对应项的 `target_config`
- [x] 3.7 映射结果保存：`state.mappingResults` 按实例分组存储，传递给步骤4

## 4. JSON 侧边抽屉组件

- [x] 4.1 新建 `public/js/modules/components/json-drawer.js` — 右侧滑出面板，宽度 40%，带遮罩
- [x] 4.2 面板内上下分栏：阿里云原始 JSON（`<pre>` 格式化）+ 腾讯云映射后 JSON
- [x] 4.3 点击 [JSON] 按钮打开，点击关闭按钮或遮罩关闭

## 5. 向导和样式更新

- [x] 5.1 `step-navigator.js` 步骤名称通过 index.html 导航条控制（无需改 JS）
- [x] 5.2 `index.html` 更新步骤导航条文字
- [x] 5.3 `app.css` 新增样式：字段对比表格行（✓绿/⚠橙/✗红）、抽屉动画、冲突面板
- [x] 5.4 `state-manager.js` 增加 `instanceMappings` 初始状态

## 6. 步骤4 小改

- [x] 6.1 `plan/index.js` 改为按实例分组展示迁移计划（分组 header + 组内项目列表）
