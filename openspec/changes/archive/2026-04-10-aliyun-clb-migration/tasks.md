## 1. 项目初始化

- [x] 1.1 初始化 Python 后端项目（venv + requirements.txt），创建 app/ 目录结构（routes/services/models/utils），编写 server.py 入口和 Flask 应用工厂
- [x] 1.2 初始化前端目录 public/（原生 JS + Materialize CSS），创建 index.html、css/、js/modules/ 结构；初始化 frontend/（Vite + package.json）
- [x] 1.3 编写 start.sh 启动脚本（开发模式 Gunicorn --reload / 生产模式），配置 .env.example、.gitignore
- [x] 1.4 编写 Dockerfile（多阶段构建：前端 Vite build + 后端 Flask 运行）和 docker-compose.yml（Flask 应用 + MySQL 8.0 容器编排）

## 2. 后端基础设施

- [x] 2.1 搭建 Flask + Blueprint 模块化路由框架，配置中间件（Flask-CORS、日志、全局异常处理、统一响应格式）
- [x] 2.2 集成 WebSocket 支持（flask-sock），实现连接管理和客户端自动重连机制
- [x] 2.3 集成 MySQL 8.0 + SQLAlchemy ORM + Flask-Migrate（Alembic），创建数据库模型基类（Base、TimestampMixin、SoftDeleteMixin），初始化数据库迁移
- [x] 2.4 创建 SQLAlchemy 模型：migration_task、instance_mapping、source_clb_snapshot、source_listener、source_forwarding_rule、source_health_check、source_acl_policy
- [x] 2.5 创建 SQLAlchemy 模型：mapping_result、incompatible_item、migration_plan_item、execution_log、migration_report、report_detail、enum_mapping_rule
- [x] 2.6 编写数据库初始化脚本（init.sql），插入 enum_mapping_rule 枚举值映射初始数据
- [x] 2.7 实现 Flask 会话管理模块，凭证运行时存于内存会话中，支持超时清理，日志脱敏

## 3. 云平台凭证管理（cloud-credentials）

- [x] 3.1 后端：实现阿里云凭证验证 Blueprint 路由（调用 aliyun-python-sdk-slb DescribeRegions 验证有效性）
- [x] 3.2 后端：实现腾讯云凭证验证 Blueprint 路由（调用 tencentcloud-sdk-python CLB DescribeRegions 验证有效性）
- [x] 3.3 后端：实现阿里云和腾讯云可用地域列表接口（仅中国大陆地域）
- [x] 3.4 前端：实现凭证输入表单页面（原生 JS + Materialize 表单，AK/SK 掩码输入、连接测试按钮、地域 Select 下拉框、.env 加载/保存）

## 4. 阿里云 CLB 配置读取（aliyun-clb-reader）

- [x] 4.1 后端：封装阿里云 SLB Python SDK（aliyun-python-sdk-slb），实现只读 API 调用（DescribeLoadBalancers、DescribeLoadBalancerListeners、DescribeRules、DescribeAccessControlLists 等）
- [x] 4.2 后端：实现 CLB 实例列表查询接口（返回实例ID、名称、状态、网络类型、VIP）
- [x] 4.3 后端：实现监听器配置查询接口（协议、端口、调度算法、高级参数、会话保持、带宽）
- [x] 4.4 后端：实现健康检查配置、转发规则、ACL 策略查询接口
- [x] 4.5 前端：实现源端实例选择页面（Table 多选、配置 Collapsible 树形预览、全选）

## 5. 配置映射引擎（config-mapping-engine）

- [x] 5.1 后端：定义统一的配置数据模型（中间格式），阿里云和腾讯云配置均转换为此格式
- [x] 5.2 后端：实现监听器协议类型映射规则（TCP/UDP/HTTP/HTTPS）
- [x] 5.3 后端：实现调度算法映射规则（wrr↔WRR、wlc↔LEAST_CONN 等）及枚举值转换表
- [x] 5.4 后端：实现健康检查配置映射（字段映射 + 取值范围校验）
- [x] 5.5 后端：实现转发规则映射（域名、URL 路径）
- [x] 5.6 后端：实现不兼容配置检测，生成不兼容项清单（配置项名称、阿里云值、原因）
- [x] 5.7 后端：实现实例映射关系管理（一对一/多对一），含端口冲突检测
- [x] 5.8 前端：实现配置映射页面（统计卡片、Collapsible 源→目标对比、不兼容项红色表格）
- [x] 5.9 前端：实现多对一端口冲突处理 UI（冲突列表展示，每项提供覆盖/跳过/重命名端口三种选择）

## 6. 迁移计划（migration-plan）

- [x] 6.1 后端：实现迁移计划生成接口（基于映射结果，生成有序操作项列表）
- [x] 6.2 后端：实现腾讯云目标 CLB 已有配置拉取（检测冲突）
- [x] 6.3 前端：实现迁移计划预览页面（源→目标配置对比表、不兼容醒目标记、可勾选跳过）
- [x] 6.4 前端：实现迁移计划确认交互（确认执行/取消按钮）

## 7. 腾讯云 CLB 受控写入（tencent-clb-writer）

- [x] 7.1 后端：封装腾讯云 CLB Python SDK（tencentcloud-sdk-python），实现写入 API（CreateListener、CreateRule、ModifyListener 等）
- [x] 7.2 后端：实现高级参数写入（连接超时、空闲超时、会话保持等）和策略配置写入（带宽限制、访问控制）
- [x] 7.3 后端：实现写操作前的冲突检测逻辑（端口占用、规则已存在）
- [x] 7.4 后端：实现写操作确认机制（通过 WebSocket 通知前端，等待用户确认后执行）
- [x] 7.5 前端：实现二次确认 Materialize Modal 弹窗组件（展示操作详情、当前值 vs 新值对比、确认/取消按钮）
- [x] 7.6 前端：实现批量确认模式（一次确认同类操作列表）

## 8. 迁移执行引擎（migration-execution）

- [x] 8.1 后端：实现迁移任务队列和逐项执行引擎（状态机：pending→running→success/failed/skipped）
- [x] 8.2 后端：实现每步执行后状态持久化到 MySQL（事务保证，支持断点续传）
- [x] 8.3 后端：实现 WebSocket 实时推送（进度百分比、当前执行项、操作日志）
- [x] 8.4 后端：实现断点续传接口（检测未完成任务，从第一个非 success 项继续）
- [x] 8.5 后端：实现暂停/继续控制接口
- [x] 8.6 后端：实现失败处理模式（"失败继续"/"失败暂停"）
- [x] 8.7 前端：实现迁移执行页面（Materialize Progress 进度条、Monospace 日志面板、暂停/继续按钮）
- [x] 8.8 前端：实现失败处理模式选择（执行前提供"失败继续"/"失败暂停"切换，默认"失败暂停"）
- [x] 8.9 前端：实现失败暂停弹窗（单项失败时弹窗提示"重试/跳过/终止"三个选项）
- [x] 8.10 前端：实现断点续传提示（检测到未完成任务时，弹窗提示"从断点继续"或"重新开始"）

## 9. 迁移报告（migration-report）

- [x] 9.1 后端：实现迁移报告生成接口（汇总成功/失败/跳过/不兼容项，统计摘要）
- [x] 9.2 后端：实现报告导出接口（JSON 和 CSV 格式）
- [x] 9.3 前端：实现迁移报告页面（统计卡片、分类标签页、详情展开、导出按钮）

## 10. 分步向导 UI 框架（step-wizard）

- [x] 10.1 前端：实现分步向导主框架（原生 JS 自定义 Step 导航条 + Materialize CSS 样式、ES6 模块化步骤状态管理、步骤间数据传递）
- [x] 10.2 前端：实现步骤导航逻辑（已完成步骤可回看、未完成步骤不可跳过）
- [x] 10.3 前端：实现响应式布局适配（桌面端 ≥ 1024px、平板端 768px-1023px）
- [x] 10.4 前端：集成各步骤页面到向导框架（凭证→选择实例→配置映射→迁移计划→执行→报告）
