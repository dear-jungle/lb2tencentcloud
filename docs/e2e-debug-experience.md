# 端到端调试经验总结

## 调试历程

### 问题清单与修复

| # | 问题 | 根因 | 修复方案 |
|---|------|------|---------|
| 1 | 凭证页面显示"功能开发中" | ES6 模块 `import()` 使用相对路径，Flask 静态服务下解析失败 | 所有 `import` 改为绝对路径 `/js/modules/...` |
| 2 | "加载中..."永远不消失 | `app.js` 中 `await api.get('/api/health')` 阻塞了向导初始化 | 改为非阻塞 `.then()` |
| 3 | `Unexpected token '}' at step-navigator.js:111` | 手动编辑时引入多余的 `}` | 移除多余花括号 |
| 4 | `Cannot read properties of null (reading 'addEventListener')` | `getElementById()` 返回 null 后直接调用 `.addEventListener()` | 所有事件绑定加 `?.` 可选链 |
| 5 | Materialize Select DOM 替换 | `M.FormSelect.init()` 会替换原始 `<select>` 元素，导致后续 `getElementById` 找不到 | 改用 `class="browser-default"` 原生 select |
| 6 | `navigator` 变量名冲突 | 函数参数名 `navigator` 遮蔽 `window.navigator`，某些环境下引发异常 | 全部改为 `nav` / `stepNav` |
| 7 | 数据流断裂 | 步骤间依赖 `taskId`（后端任务 ID），但创建任务的 API 未实现，`taskId` 永远为 null | 改为 StateManager 内存直传，不依赖后端 taskId |
| 8 | `.env` 加载不填充表单 | 后端出于安全考虑不返回凭证明文，前端无法填充输入框 | 单用户工具场景下返回凭证值 |
| 9 | 浏览器缓存旧 JS | Gunicorn reload 只重启 worker，不清浏览器缓存 | 添加 `Cache-Control: no-cache` 响应头 + `?v=N` 版本参数 |
| 10 | 未选地域也能点下一步 | `checkNext()` 只检查凭证验证状态，不检查地域 | 增加地域非空校验 + 地域 change 事件触发 checkNext |
| 11 | 阿里云 SDK `set_queryParams` 不存在 | SDK 方法名是 `set_query_params`（下划线分隔） | 修正方法名 |
| 12 | Material Icons 字体不加载 | CSS 指向 Google CDN（`fonts.gstatic.com`） | 下载字体到本地 `/fonts/` |

### 关键经验

#### 1. ES6 Module 在 Flask 静态服务下的坑

Flask 的 `static_url_path` + `static_folder` 可以正确提供 JS 文件（`Content-Type: text/javascript`），但动态 `import()` 的相对路径解析依赖当前模块的 URL 路径。**始终使用绝对路径**（如 `/js/modules/xxx/index.js`）可以避免此问题。

#### 2. Materialize CSS 组件与动态 DOM 的冲突

Materialize 的 `FormSelect.init()` 会用自定义 HTML 替换原始 `<select>` 元素。如果之后用 `getElementById` 获取原始 `<select>`，会返回 null。

**解决方案**：
- 使用 `class="browser-default"` 禁用 Materialize 的 select 美化
- 或者在 `M.FormSelect.init()` 后使用 `M.FormSelect.getInstance(el).getSelectedValues()` 获取值

#### 3. 单页应用的数据流设计

对于分步向导类应用，数据流有两种模式：

| 模式 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| 后端驱动（taskId） | 服务端持久化，刷新不丢失 | 需要完整的 CRUD API | 生产级应用 |
| 前端内存（StateManager） | 实现简单，无 API 依赖 | 刷新丢失状态 | 内部工具、MVP |

当前项目使用前端内存模式，后续可升级为后端驱动。

#### 4. 自动化测试策略

| 层级 | 工具 | 覆盖范围 |
|------|------|---------|
| 单元测试 | pytest | 映射引擎、SDK 调用 |
| API 测试 | requests | 路由、错误处理 |
| E2E 测试 | Playwright | 完整用户流程 |
| 边界测试 | Playwright | 空输入、无效凭证、未选项 |

#### 5. 防御性编程清单

- [ ] 所有 `getElementById()` 后加 `?.` 可选链
- [ ] 所有 `await` 的 API 调用加 try/catch
- [ ] 所有动态 HTML 内容用 `esc()` 转义防 XSS
- [ ] 所有按钮操作中禁用按钮防重复点击
- [ ] 表单验证在前端和后端都做（双重校验）

## 测试覆盖

### 主流程测试 (e2e_flow_test.py)
- ✅ 凭证配置：.env 加载 → 地域选择 → 验证 → 下一步
- ✅ 实例选择：列表加载 → 全选 → 下一步
- ✅ 配置映射：自动映射 → 统计展示 → 下一步
- ✅ 迁移计划：计划项列表 → 确认执行
- ✅ 迁移执行：开始执行 → 进度 → 完成
- ✅ 迁移报告：统计卡片 → 详情列表 → 导出

### 边界测试 (e2e_boundary_test.py)
- ✅ 空凭证：前端拦截，下一步禁用
- ✅ 无效凭证：后端返回错误，前端显示红色状态
- ✅ 未选地域：下一步禁用（BUG 已修复）
- ✅ 未选实例：下一步禁用
- ✅ 计划全取消：0 项进入执行
- ✅ 响应式布局：桌面/平板/小屏截图
- ✅ API 错误处理：无效 JSON、缺参数、404

### 待补充测试
- [ ] WebSocket 断连重连
- [ ] 大量实例（>50个）性能
- [ ] 并发请求处理
- [ ] 会话超时后的行为
- [ ] 断点续传流程
