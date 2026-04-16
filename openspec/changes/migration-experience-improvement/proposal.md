## Why

当前 CLB 迁移工具存在 5 个用户体验痛点：(1) 配置对比阶段缺少源端与目标端已有监听器的冲突检测，可能导致迁移失败；(2) 步骤3（配置对比）和步骤4（迁移计划）功能高度重叠，增加用户操作负担；(3) 凭证每次使用都需要重新输入，缺乏持久化存储；(4) 地域选择固定在步骤1，后续无法灵活调整；(5) 迁移报告仅在内存中生成，刷新页面后丢失，无法历史回溯。本次变更旨在系统性优化用户体验、提升工具易用性。

## What Changes

- **合并步骤3和步骤4**：将"配置对比"与"迁移计划确认"合并为一步"配置映射与计划"，减少一个步骤，降低用户心智负担。向导从6步变为5步。
- **增强监听器冲突检测**：在配置映射阶段，除现有的多对一端口冲突外，新增源端监听器与目标端实例已有监听器的协议+端口冲突检测，提前预警避免写入失败。
- **凭证 Cookie 持久化**：用户填写的阿里云/腾讯云凭证（AccessKey/SKey 等）保存到浏览器 Cookie（加密存储），下次访问自动填充，有效期7天。敏感信息仅前端使用，不传输到服务端存储。
- **地域选择下沉至实例关联步骤**：将地域选择从凭证步骤移至实例关联步骤（步骤2），允许用户在该步骤随时修改地域。修改地域后自动清空后续步骤状态并重新加载实例列表。
- **迁移报告数据库持久化**：新增 `migration_report` 数据库表，每次迁移完成后报告自动入库；支持报告列表查看、单个/批量下载 Excel、删除报告。

## Capabilities

### New Capabilities

- `credential-persistence`：浏览器端凭证 Cookie 持久化，支持自动填充和安全过期机制
- `region-flexible-selection`：实例关联步骤中的动态地域选择与状态重置逻辑
- `listener-conflict-detection`：源端-目标端监听器冲突检测，包含后端检测 API 和前端展示
- `report-persistence`：迁移报告的数据库 CRUD 操作、Excel 批量下载、报告生命周期管理
- `merged-mapping-plan`：合并后的配置映射与计划步骤，整合原有两步的核心功能

### Modified Capabilities

（无现有 spec 级别的需求变更）

## Impact

**前端改动**：
- `public/index.html` — 步骤导航条从6步改为5步
- `public/js/modules/credential/index.js` — 移除地域选择，精简为纯凭证填写 + Cookie 读写
- `public/js/modules/aliyun/index.js` — 新增地域选择器，地域变更时触发级联清空
- `public/js/modules/mapping/index.js` — 合并 plan/index.js 的勾选/统计/二次确认功能，新增冲突检测结果渲染
- `public/js/modules/plan/index.js` — 删除（功能并入 mapping）
- `public/js/modules/report/index.js` — 改为从后端 API 加载报告数据，新增批量操作 UI
- `public/js/modules/core/state-manager.js` — 新增 credentials 持久化相关状态字段
- `public/js/app.js` — 更新步骤注册映射

**后端改动**：
- 新增 `app/services/migration/report_service.py` — 报告 CRUD 服务
- 新增 `app/models/report.py` — MigrationReport 数据库模型
- 新增 `migrations/` — 报告表迁移脚本
- 修改或新增 `app/routes/report_routes.py` — 报告 RESTful API（列表/详情/下载/删除）
- 修改 `app/services/tencent/clb_writer.py` 或新建 `app/services/migration/conflict_detector.py` — 目标端监听器冲突检测方法
- 修改 `app/routes/mapping_routes.py` — 映射接口返回值增加冲突检测结果

**数据库**：
- 新增 `migration_report` 表
