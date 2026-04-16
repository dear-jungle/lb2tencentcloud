## Context

CLB 迁移工具当前为 6 步向导流程（凭证配置 → 实例关联 → 配置对比 → 迁移计划 → 执行迁移 → 迁移报告），基于 Flask + Materialize CSS + SQLAlchemy 技术栈。现有功能已完成映射引擎、迁移执行引擎等核心能力，但用户体验层面存在以下问题：

1. **步骤冗余**：步骤3（配置对比）和步骤4（迁移计划）展示内容高度重叠，用户需在两步间反复切换
2. **冲突检测不完整**：仅检测多对一源端端口冲突，缺少与目标端已有监听器的冲突检查
3. **凭证无持久化**：每次使用都需重新输入阿里云/腾讯云凭证
4. **地域锁定**：地域选择在步骤1固定后无法调整
5. **报告易失**：迁移报告仅存内存，刷新即丢失

**约束**：
- 前端使用原生 ES Module + Materialize CSS，不引入 React/Vue 等框架
- 后端 Flask + SQLAlchemy，数据库 SQLite（开发）/ MySQL（生产）
- 凭证不得明文存储到服务端

## Goals / Non-Goals

**Goals:**
- 向导从 6 步精简为 5 步，合并配置对比与迁移计划
- 实现完整的源端→目标端监听器冲突检测链路
- 凭证浏览器 Cookie 持久化（7天有效期），自动填充
- 地域选择下沉至实例关联步骤，支持动态修改和级联重置
- 迁移报告数据库持久化，支持 CRUD 和批量导出

**Non-Goals:**
- 不做用户认证系统（单工具场景）
- 不做报告定时清理/归档策略（本次不涉及）
- 不引入新的前端框架
- 不改变核心映射引擎和迁移执行引擎的逻辑

## Decisions

### 决策1：合并步骤3+4为"配置映射与计划"

**方案**：将 `mapping/index.js` 和 `plan/index.js` 合并为一个模块 `mapping/index.js`（重写），在映射结果下方直接嵌入勾选框、统计摘要和"确认执行"按钮。

**理由**：原步骤3展示字段级对比+替代方案选择，原步骤4展示项目级列表+勾选+确认执行。两者数据同源（mappingResults），拆分反而增加状态传递复杂度。

**替代方案考虑**：
- 保留两步但共享数据 → 仍需额外一次页面跳转，体验改善有限 ❌
- 合并为一步但用 Tab 切换对比/计划视图 → 增加交互复杂度 ❌
- 直接合并，映射结果上方统计卡片，下方表格带勾选，底部操作栏 ✅

### 决策2：凭证 Cookie 持久化方案

**方案**：使用浏览器 `document.cookie` 存储加密后的凭证 JSON。加密方式：Base64 编码 + 简单 XOR 混淆（非安全加密，防肉眼识别）。Cookie 属性：`SameSite=Strict; HttpOnly=false; Max-Age=604800`（7天）。

**理由**：
- 服务端不存储凭证，符合最小权限原则
- 无需引入 IndexedDB 或 LocalStorage 的额外复杂度
- HttpOnly=false 因为前端 JS 需要读取填充表单

**替代方案考虑**：
- LocalStorage 存储 → 更大容量但同样非加密，与 Cookie 安全性同级，且 Cookie 更符合"会话凭证"语义 ✅
- 服务端 Session 存储 → 引入 Session 管理复杂度，且服务端不应接触明文凭证 ❌

**安全注意**：Cookie 中存储的混淆凭证并非真正加密，仅防止意外泄露。生产环境应通过 HTTPS 传输。

### 决策3：地域选择位置调整

**方案**：从 `credential/index.js` 移除地域 `<select>` 控件，将其添加到 `aliyun/index.js`（实例关联步骤）的顶部区域。源端和目标端地域并排显示，变更时触发以下逻辑：
1. 清空 StateManager 中 instanceMappings、sourceConfigs、mappingResults、planItems、executionStatus
2. 重新调用 `/api/aliyun/clb/instances` 和 `/api/tencent/clb/instances` 加载新地域实例
3. 重置左侧选中状态和右侧关联状态

**理由**：地域本质是"查询实例的参数"，放在实例选择步骤更符合用户心智模型。

### 决策4：目标端冲突检测架构

**方案**：新增后端接口 `POST /api/mapping/detect-target-conflicts`，接收 `{ targetInstanceId, listeners }`，调用腾讯云 `DescribeListeners` API 获取目标实例已有监听器，比对 protocol+port 返回冲突列表。前端在用户完成目标端选择后、点击"下一步前"自动调用该接口。

**理由**：目标端监听器是动态数据（可能被其他操作变更），必须实时查询而非缓存。

### 决策5：迁移报告持久化

**方案**：`MigrationReport` 和 `ReportDetail` 模型已存在（见 `app/models/report.py`），补全 `report_routes.py` 中的 TODO 实现，并在迁移执行完成后由 engine 自动写入报告。

**新增 API**：
- `GET /api/reports` — 分页查询报告列表
- `GET /api/reports/<id>` — 获取单个报告详情
- `GET /api/reports/<id>/download?format=excel` — 下载 Excel
- `POST /api/reports/batch-download` — 批量下载（ZIP 打包）
- `DELETE /api/reports/<id>` — 删除报告

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Cookie 凭证被 XSS 攻击窃取 | 高 | 确保 DOM 输出正确转义（esc()函数），生产环境 CSP 策略 |
| 地域变更导致中间状态丢失 | 中 | 变更前弹出确认提示"修改地域将清空后续步骤数据" |
| 目标端冲突检测增加请求延迟 | 低 | 并行检测多个目标实例，前端 loading 状态反馈 |
| 报告数据量大影响查询性能 | 低 | 列表页仅返回摘要，详情按需加载；必要时加分页 |
| 合并步骤导致单页面内容过多 | 中 | 使用 Collapsible 折叠面板组织内容 |

## Migration Plan

1. 数据库：`migration_report` 表已存在，无需额外迁移
2. 后端：按 capability 逐步新增/修改路由和服务
3. 前端：先改步骤导航和 state-manager，再逐模块改造
4. 向导顺序变更：凭证(1) → 实例关联(2) → 配置映射与计划(3) → 执行(4) → 报告(5)

**回滚策略**：Git 分支回退即可，无不可逆的数据迁移。

## Open Questions

（暂无）
