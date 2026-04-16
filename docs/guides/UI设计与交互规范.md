# UI 设计规范、交互规范与 UI 测试规范

## 一、视觉设计规范

### 1.1 设计体系

采用 **Google Material Design** 设计规范，使用 **Materialize CSS 1.0.0** 框架，所有静态资源（CSS、字体、图标）本地化部署，不依赖 CDN。

### 1.2 色彩规范

| 用途 | 色值 | 说明 |
|------|------|------|
| **主色调** | `#1976d2` / `#2196f3` | 品牌蓝，导航栏、主要按钮、链接 |
| **强调色** | `#ff9800` / `#f57c00` | 橙色，警告提示、HTTPS 配置提醒、SSL 相关 |
| **成功色** | `#4caf50` / `#388e3c` | 绿色，成功提示、已完成状态、确认操作 |
| **错误色** | `#f44336` | 红色，错误提示、失败状态、删除操作 |
| **背景灰** | `#f5f5f5` | 页面背景色 |
| **步骤渐变** | `#667eea → #764ba2` | 步骤进度条背景 |
| **阿里云主题** | `#2196f3`（蓝色系） | 阿里云相关 UI 区域 |
| **腾讯云主题** | `#009688`（青色系） | 腾讯云相关 UI 区域 |
| **不兼容项** | `#f44336` 背景 `#fbe9e7` | 不兼容/无法迁移的配置标记 |
| **需适配项** | `#ff9800` 背景 `#fff3e0` | 需要适配/降级的配置标记 |

### 1.3 字体规范

| 用途 | 字体 |
|------|------|
| 正文 | 系统默认字体（`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`） |
| 图标 | Material Icons（本地化 woff2，`font-display: swap`） |
| 代码/日志 | `Consolas, Monaco, monospace` |

### 1.4 间距与尺寸

| 元素 | 规范 |
|------|------|
| 页面容器 | `width: 90%; max-width: 1600px; margin: 0 auto` |
| 卡片内边距 | `padding: 24px`（Materialize 默认） |
| 组件间距 | `margin-bottom: 15px ~ 20px` |
| 按钮大小 | 标准 `btn`（高 36px）/ 小号 `btn-small`（高 32px） |
| 图标大小 | 标准 24px / 小号 `tiny` 18px / 大号 `medium` 42px |
| 圆角 | 卡片 4px / 徽章 20px / 步骤圆 50% / 输入框 4px |

### 1.5 CSS 模块化规范

**架构模式**：`@import` 层级管理，主入口文件聚合所有模块

```
public/css/
├── style.css           # 主入口（@import 导入所有模块）
├── base.css            # 基础样式（字体、布局、导航）
├── components.css      # 通用组件入口
│   ├── basic-components.css    # 基础 UI 组件
│   └── ...
├── wizard.css          # 分步向导样式
├── mapping.css         # 配置映射展示样式
├── migration.css       # 迁移执行样式（进度、日志）
├── report.css          # 迁移报告样式
├── forms.css           # 表单和输入控件
├── modals.css          # 模态框样式
└── responsive.css      # 响应式样式（最后加载）
```

**规则**：
- 每个 CSS 文件 **< 200 行**
- 每个文件顶部注释说明职责
- 新增功能创建新模块文件 + 在入口文件添加 `@import`
- 遵循**单一职责原则**：修改某功能只编辑对应模块

---

## 二、组件规范

### 2.1 分步向导 (Step Wizard)

本项目核心交互组件，6 步流程：

```
[凭证配置] → [选择源端实例] → [配置映射] → [迁移计划确认] → [执行迁移] → [迁移报告]
```

**步骤导航条**：
- 顶部渐变背景（`#667eea → #764ba2`）
- 步骤圆圈：未到达灰色半透明 / 当前步骤白色放大 / 已完成绿色
- 步骤间用 `→` 连接线
- 每步显示名称 + 简短描述

**步骤卡片徽章**：
- 悬浮在卡片左上角（`position: absolute; top: -12px`）
- 不同步骤用不同颜色渐变：蓝→橙→青→绿
- 圆形数字 + 动作文字

### 2.2 Toast 通知

| 类型 | 颜色 | 图标 | 持续时间 | 使用场景 |
|------|------|------|---------|---------|
| `success` | 绿色 `green` | `check_circle` | 3 秒 | 操作成功 |
| `error` | 红色 `red` | `error` | 4 秒 | 操作失败 |
| `warning` | 橙色 `orange` | `warning` | 3 秒 | 警告提示 |
| `info` | 蓝色 `blue` | `info` | 3 秒 | 普通信息 |

**使用方式**（统一接口）：
```javascript
UIUtils.Toast.success('操作成功');
UIUtils.Toast.error('操作失败');
UIUtils.Toast.warning('请注意');
UIUtils.Toast.info('提示信息');
```

### 2.3 Modal 弹窗

**标准弹窗结构**：
```html
<div class="modal modal-fixed-footer">
    <div class="modal-content">
        <h4><i class="material-icons left">图标</i> 标题</h4>
        <!-- 内容 -->
    </div>
    <div class="modal-footer">
        <a class="modal-close btn-flat">取消</a>
        <button class="btn green">确认</button>
    </div>
</div>
```

**二次确认弹窗**（腾讯云写操作专用）：
- 必须明确展示将要执行的操作详情
- 修改/覆盖操作必须展示"当前值 vs 新值"对比
- 确认按钮用醒目颜色，取消按钮用 `btn-flat`
- 批量确认模式：列出所有同类操作，一次确认

### 2.4 加载状态

**Materialize Spinner**（API 请求时）：
```html
<div class="preloader-wrapper big active">
    <div class="spinner-layer spinner-blue-only">...</div>
</div>
<p class="loading-text">加载中...</p>
```

**进度条**（迁移执行时）：
```html
<div class="progress" style="height: 10px; border-radius: 5px;">
    <div class="determinate" style="width: 45%; background: linear-gradient(90deg, #2196f3, #4caf50);"></div>
</div>
```

### 2.5 表单控件

- 使用 Materialize `input-field` 风格
- `<select>` 用 Materialize Select 初始化
- 必填字段实时验证，错误提示在字段下方
- 密码/密钥输入框用 `type="password"` 掩码
- 地域选择用下拉框 + 搜索过滤

### 2.6 数据展示

**表格**：使用 Materialize `striped highlight responsive-table`
**树形配置**：可折叠面板（`Collapsible` 手风琴模式）
**配置对比**：左右双栏（源 → 目标），不同项高亮
**统计卡片**：`flex` 排列，每个卡片显示数字 + 标签，不同颜色区分

---

## 三、交互规范

### 3.1 Loading 状态

- 所有 API 请求必须显示加载状态
- 按钮在请求期间禁用并显示 loading 文字
- 列表区域用 Spinner 占位
- 长时间操作（>3s）显示进度百分比

### 3.2 操作反馈

| 操作 | 反馈方式 |
|------|---------|
| 凭证验证成功 | Toast success + 显示账号信息 |
| 凭证验证失败 | Toast error + 字段下方错误提示 |
| 配置拉取完成 | Toast success + 展示配置树 |
| 不兼容项发现 | 红色/橙色标记 + 警告图标 + 原因说明 |
| 迁移项完成 | 日志追加 + 进度条更新 |
| 写操作前 | 弹窗确认（展示操作详情） |
| 写操作成功 | 日志绿色标记 |
| 写操作失败 | 日志红色标记 + 重试/跳过按钮 |

### 3.3 确认与取消

- **删除类操作**：必须弹窗确认，提示影响范围
- **腾讯云所有写操作**：必须二次确认弹窗，展示操作详情
- **批量操作**：提供"批量确认同类操作"选项
- **取消操作**：不执行任何改动，可返回上一步

### 3.4 步骤导航

- **前进**：当前步骤完成后点击"下一步"
- **后退**：可点击已完成步骤回看（只读或可修改后需重新验证）
- **跳过禁止**：未完成步骤不可跳过
- **步骤高亮**：当前步骤高亮 / 已完成绿色对勾 / 未到达灰显

### 3.5 实时更新

- 迁移执行中：WebSocket 推送进度和日志
- 日志面板自动滚动到底部（可手动暂停）
- 进度条实时更新百分比
- 断线自动重连，重连后同步最新状态

### 3.6 可访问性

- 所有按钮和链接支持键盘操作（Tab 切换、Enter 确认）
- 表单输入框支持 Tab 切换焦点
- 使用语义化 HTML 标签（`<nav>`、`<main>`、`<section>`、`<h1>`-`<h6>`）
- 图标使用 `aria-label` 或配合文字说明
- 颜色区分同时配合图标/文字（不仅靠颜色传达信息）

---

## 四、响应式规范

| 设备 | 宽度 | 适配策略 |
|------|------|---------|
| 桌面端 | ≥ 1024px | 全宽布局，多栏并排 |
| 平板端 | 768px - 1023px | 缩窄布局，部分组件堆叠 |
| 移动端 | < 768px | **不作为目标设备**（桌面端工具） |

**关键断点**：
- `@media (max-width: 992px)`：步骤条换行、列适配
- `@media (max-width: 600px)`：步骤条隐藏、徽章内嵌

---

## 五、浏览器兼容性

| 浏览器 | 最低版本 |
|--------|---------|
| Google Chrome | 90+（推荐） |
| Microsoft Edge | 90+ |
| Firefox | 88+ |
| Safari | 14+（macOS） |
| IE | **不支持** |

---

## 六、前端 JS 模块 UI 工具使用规范

### 6.1 统一接口 UIUtils（推荐）

```javascript
import { UIUtils } from './utils/ui-utils.js';

// DOM 操作
UIUtils.DOM.updateText('title', '新标题');
UIUtils.DOM.toggleVisibility('content', true);

// Toast 通知
UIUtils.Toast.success('操作成功');
UIUtils.Toast.error('操作失败');

// Modal 管理
UIUtils.Modal.init('myModal', { dismissible: false });
UIUtils.Modal.open('myModal');

// 加载状态
UIUtils.Loading.setState('submitBtn', true, '加载中...');

// HTML 工厂（链式调用）
UIUtils.HTML.checkbox('cb1', '选项').setChecked(true).build();
```

### 6.2 最佳实践

1. **优先使用 UIUtils 统一接口**（一次导入访问所有功能）
2. **使用状态管理**而非全局变量
3. **使用 ApiService 封装**而非直接 `fetch`
4. **链式调用创建 HTML**，避免手动拼接字符串
5. **统一错误处理**：`try/catch` 配合 `UIUtils.showError()`
6. **使用 `textContent`** 而非 `innerHTML` 设置用户输入内容（防 XSS）

---

## 七、UI 测试规范

### 7.1 测试策略

本项目采用**轻量级自定义前端测试框架** + **HTML 测试页面**方式进行 UI 测试，不引入 Jest/Cypress 等重量级框架。

### 7.2 测试类型

| 类型 | 方式 | 覆盖范围 |
|------|------|---------|
| **JS 模块单元测试** | 自定义 TestFramework + HTML 测试页面 | 状态管理、API 服务、格式化器、映射逻辑 |
| **UI 组件视觉测试** | 独立 HTML 测试页面 | Toast、Modal、进度条、表单验证 |
| **交互流程测试** | 手动功能测试 + checklist | 分步向导、确认弹窗、断点续传 |
| **后端 API 测试** | pytest + pytest-flask | 所有 REST API 端点 |

### 7.3 前端测试框架

```javascript
// 使用自定义测试框架（public/js/test/test-framework.js）
import { TestResultCollector, Asserter, TestCase } from './test-framework.js';

class MyTest extends TestCase {
    constructor() { super('映射引擎测试'); }

    run(assert) {
        assert.assertEqual(mapScheduler('wrr'), 'WRR', 'wrr 映射为 WRR');
        assert.assertEqual(mapScheduler('wlc'), 'LEAST_CONN', 'wlc 映射为 LEAST_CONN');
        assert.assertTrue(isIncompatible('ch'), 'ch 算法标记为不兼容');
    }
}
```

### 7.4 HTML 测试页面

为关键 UI 模块创建独立测试页面：

```
public/
├── test-wizard.html          # 分步向导测试
├── test-mapping-preview.html # 配置映射预览测试
├── test-migration-progress.html # 迁移进度测试
└── js/test/
    ├── test-framework.js     # 测试框架核心
    ├── test-runner.js        # 测试运行器
    └── test-cases/
        ├── test-state-manager.js  # 状态管理测试
        ├── test-api-service.js    # API 服务测试
        └── test-mapper.js         # 映射逻辑测试
```

### 7.5 UI 测试检查清单

#### 分步向导

- [ ] 步骤导航条正确显示 6 个步骤
- [ ] 当前步骤高亮，已完成步骤绿色对勾
- [ ] 未完成步骤不可跳过
- [ ] 已完成步骤可回看
- [ ] 步骤间数据正确传递

#### 凭证页面

- [ ] AK/SK 输入框掩码显示
- [ ] 连接测试按钮正常工作
- [ ] 成功/失败显示对应提示
- [ ] 地域列表正确加载

#### 配置映射页面

- [ ] 配置树形展示正确
- [ ] 不兼容项红色/橙色标记
- [ ] 实例映射关系（一对一/一对多/多对一）可配置
- [ ] 端口冲突检测提示

#### 迁移计划页面

- [ ] 源 → 目标配置对比正确
- [ ] 可勾选跳过某些迁移项
- [ ] 确认/取消按钮正常

#### 二次确认弹窗

- [ ] 创建操作弹窗展示资源详情
- [ ] 修改操作弹窗展示"当前值 vs 新值"
- [ ] 用户不确认不执行写操作
- [ ] 批量确认模式展示操作列表

#### 迁移执行页面

- [ ] 进度条实时更新
- [ ] 日志面板实时滚动
- [ ] 暂停/继续按钮有效
- [ ] 断线重连后状态同步

#### 迁移报告页面

- [ ] 统计卡片数字正确（成功/失败/跳过/不兼容）
- [ ] 分类标签页可切换
- [ ] 详情可展开
- [ ] 导出 JSON/CSV 正常

#### 响应式

- [ ] 桌面端（≥ 1024px）布局正常
- [ ] 平板端（768-1023px）布局自适应
- [ ] 无水平滚动条

#### 浏览器兼容性

- [ ] Chrome 90+ 正常
- [ ] Edge 90+ 正常
- [ ] Firefox 88+ 正常

### 7.6 视觉回归测试方法

1. 修改 CSS 后，在 Chrome DevTools 中对比前后截图
2. 检查所有颜色是否符合色彩规范
3. 检查间距、字体、圆角是否一致
4. 检查 Loading/Spinner 动画正常
5. 检查暗色区域（日志面板 `#1e1e1e`）文字可读性
