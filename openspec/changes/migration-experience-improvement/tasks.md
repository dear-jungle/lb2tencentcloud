# 迁移体验改进 — 任务清单

## 1. 凭证 Cookie 持久化

- [x] 1.1 新建 `public/js/modules/core/cookie-helper.js` — 封装 Cookie 读写工具类，含 `set(name, value, options)` / `get(name)` / `remove(name)` 方法，支持混淆编解码（Base64 + XOR）
- [x] 1.2 修改 `credential/index.js` — 移除地域选择 `<select>` 控件（保留源端/目标端密钥输入框和验证按钮），精简布局为纯凭证填写
- [x] 1.3 在 `credential/index.js` 中集成 Cookie 持久化 — 验证成功后调用 cookieHelper 保存凭证；页面加载时读取并自动填充输入框
- [x] 1.4 在 `credential/index.js` 中添加"清除已保存凭证"按钮及对应逻辑

## 2. 地域选择下沉至实例关联步骤

- [x] 2.1 修改 `aliyun/index.js` 页面顶部新增地域选择区域 — 左右两栏分别展示"源端地域"和"目标地域"下拉框，预选 state 中的当前值
- [x] 2.2 实现地域变更确认弹窗 — 用户修改任意地域时弹出 Modal 提示"修改地域将清空后续步骤数据，是否继续？"
- [x] 2.3 实现级联重置逻辑 — 确认后清空 instanceMappings/sourceConfigs/mappingResults/planItems/executionStatus，重新调用 API 加载新地域的实例列表，重置所有选中/关联状态
- [x] 2.4 更新 `state-manager.js` 的 credentials 初始状态 — region 字段改为可选默认空值，由步骤2设置

## 3. 目标端监听器冲突检测

- [x] 3.1 后端：在 `mapping_routes.py` 或新建 `app/services/migration/conflict_detector.py` 实现 `POST /api/mapping/detect-target-conflicts` 接口 — 接收 targetInstanceId + listeners，调用腾讯云 DescribeListeners 比对 protocol+port，返回冲突列表
- [x] 3.2 前端：在映射结果展示完成后自动并行调用目标端冲突检测 API（按目标实例分组检测）
- [x] 3.3 冲突警告 UI — 映射页面顶部或底部展示红色冲突面板（协议:端口 / 源实例 / 目标已有监听器），存在未解决冲突时禁用"下一步"按钮
- [x] 3.4 与现有多对一端口冲突检测共存 — 两套检测结果合并展示在同一面板中，来源区分标识

## 4. 合并配置对比与迁移计划步骤

- [x] 4.1 修改 `index.html` 步骤导航条 — 从6步改为5步（移除"迁移计划"，将"配置对比"改名为"配置映射与计划"），步骤序号重排
- [x] 4.2 重写 `mapping/index.js` — 整合原 mapping 的字段对比展示 + 原 plan 的项目勾选表格，上下结构：上方统计卡片+分组Collapsible对比表格，下方计划表格（含复选框+状态列）
- [x] 4.3 整合二次确认弹窗 — "确认并开始执行"按钮触发 Modal 展示统计摘要 + 逐项确认选项，确认后写入 planItems 并跳转到 execute 步骤
- [x] 4.4 修改 `public/js/modules/wizard/step-navigator.js` 步骤路由注册 — 移除 'plan' 步骤映射，mapping 步骤完成后的 next 跳转到 'execute'
- [x] 4.5 删除或归档 `plan/index.js` 文件（功能完全并入 mapping）

## 5. 迁移报告持久化与报告管理页

- [x] 5.1 后端：补全 `report_routes.py` 的所有 TODO 实现 — `GET /api/reports` 分页列表、`GET /api/reports/<id>` 详情、`GET /api/reports/<id>/download?format=excel` Excel下载、`POST /api/reports/batch-download` ZIP批量、`DELETE /api/reports/<id>`
- [x] 5.2 后端：新建 `app/services/migration/report_service.py` — 实现报告创建（从 execution_log/plan_item 汇总）、查询、删除服务方法
- [x] 5.3 后端：修改 `migration/engine.py` 执行完成后自动调用 report_service 创建 MigrationReport + ReportDetail 记录
- [x] 5.4 重写 `report/index.js` 为报告管理页 — 顶部统计卡片 + 报告列表表格（时间/摘要/操作列），支持查看详情弹窗、单个下载、批量选择+ZIP下载、单条删除
- [x] 5.5 报告详情弹窗 — 展示完整明细（Tabs 切换 全部/成功/失败/跳过），内嵌导出按钮

## 6. 测试用例

- [x] 6.1 编写凭证 Cookie 持久化测试 — 验证保存/读取/过期/清除逻辑
- [x] 6.2 编写目标端冲突检测测试 — mock 腾讯云 API 验证冲突/无冲突场景
- [x] 6.3 编写报告 CRUD 测试 — 创建/查询/下载/删除报告的接口测试
- [x] 6.4 编写地域变更级联重置测试 — 验证状态清空和数据重载逻辑
