# 数据库设计文档

## 1. 概述

### 1.1 数据库选型

| 项目 | 选择 |
|------|------|
| 数据库 | MySQL 8.0 |
| 部署方式 | Docker 容器（docker-compose 编排） |
| ORM | SQLAlchemy 2.x |
| 迁移工具 | Flask-Migrate（基于 Alembic） |
| 字符集 | utf8mb4 |
| 排序规则 | utf8mb4_unicode_ci |
| 存储引擎 | InnoDB |

### 1.2 设计原则

- **范式优先**：核心表满足第三范式，减少数据冗余
- **JSON 灵活存储**：云平台原始配置等动态结构使用 MySQL 8.0 的 JSON 字段类型
- **软删除**：关键业务表使用 `is_deleted` 标记删除，保留审计痕迹
- **全量保留**：迁移历史记录全部保留，不自动清理
- **凭证不入库**：AK/SK 仅存于服务端内存和 .env 文件，数据库不存储任何凭证明文
- **时间戳统一**：所有时间字段使用 `DATETIME(3)` 精确到毫秒，存储 UTC 时间

---

## 2. ER 关系图

```
migration_task (迁移任务)
  │
  ├── 1:N ── instance_mapping (实例映射)
  │              │
  │              ├── 1:N ── source_clb_snapshot (源端配置快照)
  │              │              │
  │              │              ├── 1:N ── source_listener (源端监听器)
  │              │              │              │
  │              │              │              ├── 1:N ── source_forwarding_rule (源端转发规则)
  │              │              │              └── 1:1 ── source_health_check (源端健康检查)
  │              │              │
  │              │              └── 1:N ── source_acl_policy (源端访问控制策略)
  │              │
  │              └── N:1 ── target_clb_instance (目标端实例)
  │
  ├── 1:N ── mapping_result (映射结果)
  │              │
  │              └── 1:N ── incompatible_item (不兼容项)
  │
  ├── 1:N ── migration_plan_item (迁移计划项)
  │
  ├── 1:N ── execution_log (执行日志)
  │
  └── 1:1 ── migration_report (迁移报告)
                 │
                 └── 1:N ── report_detail (报告明细)

enum_mapping_rule (枚举值映射规则) —— 独立配置表，无外键
```

---

## 3. 表结构设计

### 3.1 迁移任务主表 `migration_task`

迁移任务是整个系统的核心实体，对应用户发起的一次完整迁移操作。

```sql
CREATE TABLE migration_task (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '任务ID',
    task_no         VARCHAR(32)     NOT NULL COMMENT '任务编号（如 MIG-20260410-001）',
    task_name       VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '任务名称（用户可自定义）',
    status          ENUM('draft','ready','running','paused','completed','failed','cancelled')
                    NOT NULL DEFAULT 'draft' COMMENT '任务状态',
    current_step    ENUM('credential','select_source','mapping','plan','execute','report')
                    NOT NULL DEFAULT 'credential' COMMENT '当前向导步骤',

    -- 源端信息
    source_cloud    VARCHAR(16)     NOT NULL DEFAULT 'aliyun' COMMENT '源端云平台',
    source_region   VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '源端地域ID（如 cn-hangzhou）',

    -- 目标端信息
    target_cloud    VARCHAR(16)     NOT NULL DEFAULT 'tencent' COMMENT '目标端云平台',
    target_region   VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '目标端地域ID（如 ap-guangzhou）',
    target_mode     ENUM('existing','create_new') NOT NULL DEFAULT 'existing'
                    COMMENT '目标实例模式：使用已有/自动创建',

    -- 统计信息
    total_items     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '总迁移项数',
    success_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '成功数',
    failed_count    INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '失败数',
    skipped_count   INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '跳过数',
    incompatible_count INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '不兼容数',
    progress        DECIMAL(5,2)    NOT NULL DEFAULT 0.00 COMMENT '进度百分比 0.00~100.00',

    -- 时间
    started_at      DATETIME(3)     NULL COMMENT '开始执行时间',
    completed_at    DATETIME(3)     NULL COMMENT '完成时间',
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                    ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',

    is_deleted      TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '软删除标记',

    UNIQUE KEY uk_task_no (task_no),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='迁移任务主表';
```

**对应 API 路由**：
- `POST /api/migration/tasks` — 创建任务
- `GET /api/migration/tasks` — 任务列表（含分页、状态筛选）
- `GET /api/migration/tasks/<id>` — 任务详情
- `PATCH /api/migration/tasks/<id>` — 更新任务（切换步骤、更新状态）
- `DELETE /api/migration/tasks/<id>` — 软删除任务

---

### 3.2 实例映射表 `instance_mapping`

记录源端阿里云 CLB 实例到目标端腾讯云 CLB 实例的映射关系（支持一对一、多对一）。

```sql
CREATE TABLE instance_mapping (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',

    -- 源端实例
    source_instance_id  VARCHAR(64)     NOT NULL COMMENT '阿里云 CLB 实例ID',
    source_instance_name VARCHAR(128)   NOT NULL DEFAULT '' COMMENT '阿里云 CLB 实例名称',
    source_vip          VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '阿里云 VIP 地址',
    source_network_type VARCHAR(16)     NOT NULL DEFAULT '' COMMENT '网络类型（classic/vpc）',
    source_status       VARCHAR(16)     NOT NULL DEFAULT '' COMMENT '实例状态',

    -- 目标端实例
    target_instance_id  VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '腾讯云 CLB 实例ID（已有或新创建）',
    target_instance_name VARCHAR(128)   NOT NULL DEFAULT '' COMMENT '腾讯云 CLB 实例名称',
    target_vip          VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '腾讯云 VIP 地址',
    target_created_by_system TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否由系统自动创建',

    mapping_type        ENUM('one_to_one','many_to_one') NOT NULL DEFAULT 'one_to_one'
                        COMMENT '映射类型',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                        ON UPDATE CURRENT_TIMESTAMP(3),

    INDEX idx_task_id (task_id),
    INDEX idx_source_instance (source_instance_id),
    INDEX idx_target_instance (target_instance_id),
    CONSTRAINT fk_im_task FOREIGN KEY (task_id) REFERENCES migration_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='实例映射关系表';
```

**对应 API 路由**：
- `POST /api/migration/tasks/<id>/mappings` — 配置实例映射
- `GET /api/migration/tasks/<id>/mappings` — 获取映射关系列表
- `PUT /api/migration/tasks/<id>/mappings/<mid>` — 更新映射关系

---

### 3.3 源端配置快照表 `source_clb_snapshot`

保存从阿里云拉取的 CLB 实例完整原始配置（JSON），用于对比和审计。

```sql
CREATE TABLE source_clb_snapshot (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    mapping_id          BIGINT UNSIGNED NOT NULL COMMENT '关联实例映射ID',
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID（冗余，便于查询）',
    instance_id         VARCHAR(64)     NOT NULL COMMENT '阿里云 CLB 实例ID',

    -- 原始配置 JSON（阿里云 API 返回的完整数据）
    raw_config          JSON            NOT NULL COMMENT '完整原始配置快照',
    listeners_config    JSON            NULL COMMENT '监听器配置列表',
    health_check_config JSON            NULL COMMENT '健康检查配置',
    forwarding_rules    JSON            NULL COMMENT '转发规则配置',
    advanced_params     JSON            NULL COMMENT '高级参数（超时、会话保持等）',
    acl_policies        JSON            NULL COMMENT '访问控制 ACL 策略',
    bandwidth_config    JSON            NULL COMMENT '带宽限制配置',

    snapshot_at         DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '快照时间',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_task_id (task_id),
    INDEX idx_mapping_id (mapping_id),
    INDEX idx_instance_id (instance_id),
    CONSTRAINT fk_snap_mapping FOREIGN KEY (mapping_id) REFERENCES instance_mapping(id) ON DELETE CASCADE,
    CONSTRAINT fk_snap_task FOREIGN KEY (task_id) REFERENCES migration_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='源端 CLB 配置快照表';
```

**对应 API 路由**：
- `POST /api/aliyun/clb/<instance_id>/snapshot` — 拉取并保存快照
- `GET /api/migration/tasks/<id>/snapshots` — 获取任务关联的所有快照

---

### 3.4 源端监听器表 `source_listener`

结构化存储阿里云 CLB 监听器配置（从 JSON 快照中解析）。

```sql
CREATE TABLE source_listener (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    snapshot_id         BIGINT UNSIGNED NOT NULL COMMENT '关联快照ID',
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',
    instance_id         VARCHAR(64)     NOT NULL COMMENT '阿里云 CLB 实例ID',

    -- 监听器核心属性
    listener_port       INT UNSIGNED    NOT NULL COMMENT '前端监听端口',
    listener_protocol   VARCHAR(8)      NOT NULL COMMENT '协议类型（TCP/UDP/HTTP/HTTPS）',
    backend_port        INT UNSIGNED    NULL COMMENT '后端端口',
    scheduler           VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '调度算法（wrr/wlc/rr 等）',
    status              VARCHAR(16)     NOT NULL DEFAULT '' COMMENT '监听器状态',

    -- 高级参数
    connection_timeout  INT             NULL COMMENT '连接超时（秒）',
    idle_timeout        INT             NULL COMMENT '空闲超时（秒）',
    request_timeout     INT             NULL COMMENT '请求超时（秒）',

    -- 会话保持
    sticky_session      ENUM('on','off') NOT NULL DEFAULT 'off' COMMENT '会话保持开关',
    sticky_session_type VARCHAR(16)     NULL COMMENT '会话保持类型（insert/server）',
    cookie_timeout      INT             NULL COMMENT 'Cookie 超时（秒）',
    cookie              VARCHAR(128)    NULL COMMENT '自定义 Cookie 名',

    -- 带宽
    bandwidth           INT             NULL COMMENT '带宽限制（Mbps），-1 表示不限',

    -- 原始 JSON（备份）
    raw_json            JSON            NULL COMMENT '该监听器的原始 JSON',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_snapshot_id (snapshot_id),
    INDEX idx_task_id (task_id),
    INDEX idx_port_proto (instance_id, listener_port, listener_protocol),
    CONSTRAINT fk_listener_snap FOREIGN KEY (snapshot_id) REFERENCES source_clb_snapshot(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='源端监听器配置表';
```

---

### 3.5 源端转发规则表 `source_forwarding_rule`

```sql
CREATE TABLE source_forwarding_rule (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    listener_id         BIGINT UNSIGNED NOT NULL COMMENT '关联监听器ID',
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',

    rule_id             VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '阿里云规则ID',
    domain              VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '域名',
    url_path            VARCHAR(512)    NOT NULL DEFAULT '' COMMENT 'URL 路径',
    scheduler           VARCHAR(32)     NULL COMMENT '规则级调度算法',

    -- 会话保持（规则级）
    sticky_session      ENUM('on','off') NULL COMMENT '规则级会话保持',
    sticky_session_type VARCHAR(16)     NULL,
    cookie_timeout      INT             NULL,

    -- 健康检查（规则级）
    health_check_enabled ENUM('on','off') NULL COMMENT '健康检查开关',

    raw_json            JSON            NULL COMMENT '原始 JSON',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_listener_id (listener_id),
    INDEX idx_task_id (task_id),
    CONSTRAINT fk_rule_listener FOREIGN KEY (listener_id) REFERENCES source_listener(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='源端转发规则表';
```

---

### 3.6 源端健康检查表 `source_health_check`

```sql
CREATE TABLE source_health_check (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    listener_id         BIGINT UNSIGNED NOT NULL COMMENT '关联监听器ID',
    rule_id             BIGINT UNSIGNED NULL COMMENT '关联转发规则ID（NULL 表示监听器级）',

    health_check_enabled ENUM('on','off') NOT NULL DEFAULT 'on' COMMENT '是否启用',
    check_type          VARCHAR(8)      NULL COMMENT '检查协议（TCP/HTTP）',
    check_port          INT             NULL COMMENT '检查端口',
    check_path          VARCHAR(256)    NULL COMMENT '检查路径（HTTP 类型）',
    check_domain        VARCHAR(256)    NULL COMMENT '检查域名',
    check_interval      INT             NULL COMMENT '检查间隔（秒）',
    check_timeout       INT             NULL COMMENT '检查超时（秒）',
    healthy_threshold   INT             NULL COMMENT '健康阈值（连续成功次数）',
    unhealthy_threshold INT             NULL COMMENT '不健康阈值（连续失败次数）',
    http_code           VARCHAR(64)     NULL COMMENT '期望 HTTP 状态码（如 http_2xx,http_3xx）',

    raw_json            JSON            NULL COMMENT '原始 JSON',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_listener_id (listener_id),
    CONSTRAINT fk_hc_listener FOREIGN KEY (listener_id) REFERENCES source_listener(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='源端健康检查配置表';
```

---

### 3.7 源端访问控制策略表 `source_acl_policy`

```sql
CREATE TABLE source_acl_policy (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    snapshot_id         BIGINT UNSIGNED NOT NULL COMMENT '关联快照ID',
    listener_id         BIGINT UNSIGNED NULL COMMENT '关联监听器ID（NULL 表示实例级）',

    acl_id              VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '阿里云 ACL ID',
    acl_name            VARCHAR(128)    NOT NULL DEFAULT '' COMMENT 'ACL 名称',
    acl_type            VARCHAR(16)     NOT NULL DEFAULT '' COMMENT 'ACL 类型（white/black）',
    acl_entries         JSON            NULL COMMENT 'ACL 条目列表 [{cidr, comment}]',

    raw_json            JSON            NULL COMMENT '原始 JSON',
    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_snapshot_id (snapshot_id),
    CONSTRAINT fk_acl_snap FOREIGN KEY (snapshot_id) REFERENCES source_clb_snapshot(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='源端访问控制策略表';
```

---

### 3.8 映射结果表 `mapping_result`

配置映射引擎的输出：每个源端配置项映射为目标端配置项的结果。

```sql
CREATE TABLE mapping_result (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',
    mapping_id          BIGINT UNSIGNED NOT NULL COMMENT '关联实例映射ID',

    -- 源端定位
    source_type         ENUM('listener','forwarding_rule','health_check','acl','session','timeout','bandwidth')
                        NOT NULL COMMENT '源端配置类型',
    source_ref_id       BIGINT UNSIGNED NULL COMMENT '源端记录ID（listener/rule/hc/acl 表的 ID）',
    source_description  VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '源端配置描述（如 TCP:80）',

    -- 映射结果
    mapping_status      ENUM('mapped','incompatible','partial','manual') NOT NULL DEFAULT 'mapped'
                        COMMENT '映射状态',
    source_config       JSON            NOT NULL COMMENT '源端配置值',
    target_config       JSON            NULL COMMENT '目标端映射后的配置值',
    diff_summary        VARCHAR(512)    NULL COMMENT '差异摘要',

    -- 用户决策
    user_action         ENUM('accept','skip','modify') NOT NULL DEFAULT 'accept'
                        COMMENT '用户决策（接受/跳过/手动修改）',
    user_modified_config JSON           NULL COMMENT '用户手动修改后的配置',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                        ON UPDATE CURRENT_TIMESTAMP(3),

    INDEX idx_task_id (task_id),
    INDEX idx_mapping_id (mapping_id),
    INDEX idx_mapping_status (mapping_status),
    CONSTRAINT fk_mr_task FOREIGN KEY (task_id) REFERENCES migration_task(id) ON DELETE CASCADE,
    CONSTRAINT fk_mr_mapping FOREIGN KEY (mapping_id) REFERENCES instance_mapping(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='配置映射结果表';
```

**对应 API 路由**：
- `POST /api/mapping/tasks/<id>/execute` — 执行映射（生成映射结果）
- `GET /api/mapping/tasks/<id>/results` — 获取映射结果列表
- `PATCH /api/mapping/results/<rid>` — 用户修改映射结果（接受/跳过/手动修改）

---

### 3.9 不兼容项表 `incompatible_item`

```sql
CREATE TABLE incompatible_item (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',
    mapping_result_id   BIGINT UNSIGNED NOT NULL COMMENT '关联映射结果ID',

    config_name         VARCHAR(128)    NOT NULL COMMENT '配置项名称',
    source_value        VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '阿里云配置值',
    reason              VARCHAR(512)    NOT NULL COMMENT '不兼容原因',
    severity            ENUM('error','warning','info') NOT NULL DEFAULT 'warning'
                        COMMENT '严重级别',
    suggestion          VARCHAR(512)    NULL COMMENT '建议处理方式',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_task_id (task_id),
    INDEX idx_mapping_result_id (mapping_result_id),
    CONSTRAINT fk_inc_task FOREIGN KEY (task_id) REFERENCES migration_task(id) ON DELETE CASCADE,
    CONSTRAINT fk_inc_mr FOREIGN KEY (mapping_result_id) REFERENCES mapping_result(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='不兼容配置项表';
```

---

### 3.10 迁移计划项表 `migration_plan_item`

迁移计划中每一个待执行的操作项，即迁移执行引擎的任务队列。

```sql
CREATE TABLE migration_plan_item (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',
    mapping_result_id   BIGINT UNSIGNED NULL COMMENT '关联映射结果ID',
    mapping_id          BIGINT UNSIGNED NOT NULL COMMENT '关联实例映射ID',

    -- 执行顺序与类型
    seq_no              INT UNSIGNED    NOT NULL COMMENT '执行顺序号',
    operation_type      ENUM('create_instance','create_listener','create_rule',
                             'modify_listener','modify_rule','set_health_check',
                             'set_acl','set_timeout','set_session','set_bandwidth')
                        NOT NULL COMMENT '操作类型',
    operation_desc      VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '操作描述',

    -- 执行参数
    target_instance_id  VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '目标腾讯云 CLB 实例ID',
    request_params      JSON            NOT NULL COMMENT '腾讯云 API 请求参数',

    -- 冲突检测
    has_conflict        TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '是否有冲突',
    conflict_detail     JSON            NULL COMMENT '冲突详情',
    conflict_action     ENUM('overwrite','skip','create_new') NULL COMMENT '冲突处理方式',

    -- 执行状态
    status              ENUM('pending','waiting_confirm','confirmed','running',
                             'success','failed','skipped','cancelled')
                        NOT NULL DEFAULT 'pending' COMMENT '执行状态',
    user_confirmed      TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '用户是否已确认',
    confirmed_at        DATETIME(3)     NULL COMMENT '确认时间',

    -- 执行结果
    executed_at         DATETIME(3)     NULL COMMENT '执行开始时间',
    completed_at        DATETIME(3)     NULL COMMENT '执行完成时间',
    duration_ms         INT UNSIGNED    NULL COMMENT '执行耗时（毫秒）',
    response_data       JSON            NULL COMMENT '腾讯云 API 响应数据',
    error_code          VARCHAR(64)     NULL COMMENT '错误码',
    error_message       TEXT            NULL COMMENT '错误信息',
    retry_count         INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '重试次数',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                        ON UPDATE CURRENT_TIMESTAMP(3),

    INDEX idx_task_id (task_id),
    INDEX idx_task_seq (task_id, seq_no),
    INDEX idx_status (status),
    CONSTRAINT fk_plan_task FOREIGN KEY (task_id) REFERENCES migration_task(id) ON DELETE CASCADE,
    CONSTRAINT fk_plan_mapping FOREIGN KEY (mapping_id) REFERENCES instance_mapping(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='迁移计划项表（执行队列）';
```

**对应 API 路由**：
- `POST /api/migration/tasks/<id>/plan` — 生成迁移计划
- `GET /api/migration/tasks/<id>/plan` — 获取迁移计划列表
- `PATCH /api/migration/plan-items/<pid>` — 更新计划项（用户确认/跳过）
- `POST /api/migration/plan-items/<pid>/confirm` — 用户确认操作（二次确认）
- `POST /api/migration/plan-items/batch-confirm` — 批量确认同类操作
- `POST /api/migration/tasks/<id>/execute` — 开始执行 / 断点续传
- `POST /api/migration/tasks/<id>/pause` — 暂停执行
- `POST /api/migration/tasks/<id>/resume` — 继续执行

---

### 3.11 执行日志表 `execution_log`

迁移过程中的实时操作日志，通过 WebSocket 推送给前端。

```sql
CREATE TABLE execution_log (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',
    plan_item_id        BIGINT UNSIGNED NULL COMMENT '关联计划项ID',

    log_level           ENUM('info','warn','error','debug') NOT NULL DEFAULT 'info'
                        COMMENT '日志级别',
    log_type            ENUM('system','api_call','user_action','confirm','error','progress')
                        NOT NULL DEFAULT 'system' COMMENT '日志类型',
    message             TEXT            NOT NULL COMMENT '日志内容',
    detail              JSON            NULL COMMENT '详细数据（API 请求/响应等）',

    logged_at           DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '日志时间',

    INDEX idx_task_id (task_id),
    INDEX idx_task_logged (task_id, logged_at),
    INDEX idx_plan_item_id (plan_item_id),
    CONSTRAINT fk_log_task FOREIGN KEY (task_id) REFERENCES migration_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='迁移执行日志表';
```

**对应 API 路由**：
- `GET /api/migration/tasks/<id>/logs` — 获取执行日志（支持分页、级别筛选）
- WebSocket `/ws/migration/<id>` — 实时推送日志和进度

---

### 3.12 迁移报告表 `migration_report`

```sql
CREATE TABLE migration_report (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',

    -- 统计摘要
    total_items         INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '总迁移项数',
    success_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '成功数',
    failed_count        INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '失败数',
    skipped_count       INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '跳过数',
    incompatible_count  INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '不兼容数',
    total_duration_ms   BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '总耗时（毫秒）',

    -- 报告元数据
    generated_at        DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '报告生成时间',
    report_summary      TEXT            NULL COMMENT '报告文本摘要',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    UNIQUE KEY uk_task_id (task_id),
    CONSTRAINT fk_report_task FOREIGN KEY (task_id) REFERENCES migration_task(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='迁移报告表';
```

---

### 3.13 报告明细表 `report_detail`

```sql
CREATE TABLE report_detail (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    report_id           BIGINT UNSIGNED NOT NULL COMMENT '关联报告ID',
    task_id             BIGINT UNSIGNED NOT NULL COMMENT '关联迁移任务ID',
    plan_item_id        BIGINT UNSIGNED NULL COMMENT '关联计划项ID',

    -- 明细信息
    category            ENUM('success','failed','skipped','incompatible') NOT NULL COMMENT '结果分类',
    operation_type      VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '操作类型',
    operation_desc      VARCHAR(256)    NOT NULL DEFAULT '' COMMENT '操作描述',

    source_config       JSON            NULL COMMENT '源端配置',
    target_config       JSON            NULL COMMENT '目标端配置',

    error_code          VARCHAR(64)     NULL COMMENT '错误码（失败项）',
    error_message       TEXT            NULL COMMENT '错误信息（失败项）',
    incompatible_reason VARCHAR(512)    NULL COMMENT '不兼容原因',

    executed_at         DATETIME(3)     NULL COMMENT '执行时间',
    duration_ms         INT UNSIGNED    NULL COMMENT '执行耗时（毫秒）',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    INDEX idx_report_id (report_id),
    INDEX idx_task_id (task_id),
    INDEX idx_category (category),
    CONSTRAINT fk_rd_report FOREIGN KEY (report_id) REFERENCES migration_report(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='迁移报告明细表';
```

**对应 API 路由**：
- `POST /api/migration/tasks/<id>/report` — 生成迁移报告
- `GET /api/migration/tasks/<id>/report` — 获取报告（含统计摘要）
- `GET /api/migration/tasks/<id>/report/details` — 获取报告明细（支持分类筛选）
- `GET /api/migration/tasks/<id>/report/export?format=json` — 导出报告（JSON）
- `GET /api/migration/tasks/<id>/report/export?format=csv` — 导出报告（CSV）

---

### 3.14 枚举值映射规则表 `enum_mapping_rule`

独立配置表，存储阿里云到腾讯云的枚举值映射规则（调度算法、协议等），无外键关联。

```sql
CREATE TABLE enum_mapping_rule (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category            VARCHAR(32)     NOT NULL COMMENT '映射分类（scheduler/protocol/health_check_type 等）',
    source_value        VARCHAR(64)     NOT NULL COMMENT '阿里云枚举值',
    target_value        VARCHAR(64)     NULL COMMENT '腾讯云枚举值（NULL 表示不兼容）',
    is_compatible       TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '是否兼容',
    remark              VARCHAR(256)    NULL COMMENT '备注',

    created_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at          DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
                        ON UPDATE CURRENT_TIMESTAMP(3),

    UNIQUE KEY uk_category_source (category, source_value),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='枚举值映射规则表';
```

**初始化数据**：

```sql
-- 调度算法映射
INSERT INTO enum_mapping_rule (category, source_value, target_value, is_compatible, remark) VALUES
('scheduler', 'wrr',  'WRR',        1, '加权轮询'),
('scheduler', 'wlc',  'LEAST_CONN', 1, '加权最小连接数'),
('scheduler', 'rr',   'WRR',        1, '轮询 → 加权轮询（权重均等）'),
('scheduler', 'sch',  NULL,          0, '源地址哈希，腾讯云 CLB 不支持'),
('scheduler', 'tch',  NULL,          0, '四元组哈希，腾讯云 CLB 不支持'),
('scheduler', 'qch',  NULL,          0, '五元组哈希，腾讯云 CLB 不支持'),

-- 协议类型映射
('protocol', 'tcp',   'TCP',   1, 'TCP 监听器'),
('protocol', 'udp',   'UDP',   1, 'UDP 监听器'),
('protocol', 'http',  'HTTP',  1, 'HTTP 七层监听器'),
('protocol', 'https', 'HTTPS', 1, 'HTTPS 七层监听器'),

-- 健康检查类型映射
('health_check_type', 'tcp',  'TCP',  1, 'TCP 健康检查'),
('health_check_type', 'http', 'HTTP', 1, 'HTTP 健康检查'),

-- ACL 类型映射
('acl_type', 'white', 'white', 1, '白名单'),
('acl_type', 'black', 'black', 1, '黑名单'),

-- 会话保持类型映射
('sticky_session_type', 'insert', 'NORMAL', 1, '植入 Cookie → 腾讯云 CLB 管理的 Cookie'),
('sticky_session_type', 'server', 'CUSTOMIZED', 1, '重写 Cookie → 自定义 Cookie');
```

---

## 4. Docker Compose 数据库编排

```yaml
# docker-compose.yml 中 MySQL 服务配置
services:
  mysql:
    image: mysql:8.0
    container_name: lb2tc-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-lb2tc_root_2026}
      MYSQL_DATABASE: ${MYSQL_DATABASE:-lb2tencentcloud}
      MYSQL_USER: ${MYSQL_USER:-lb2tc}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-lb2tc_pass_2026}
    ports:
      - "${MYSQL_PORT:-3306}:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./migrations/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-authentication-plugin=mysql_native_password
      - --max-connections=100
      - --innodb-buffer-pool-size=256M
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD:-lb2tc_root_2026}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    container_name: lb2tc-app
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      DATABASE_URL: mysql+pymysql://${MYSQL_USER:-lb2tc}:${MYSQL_PASSWORD:-lb2tc_pass_2026}@mysql:3306/${MYSQL_DATABASE:-lb2tencentcloud}?charset=utf8mb4

volumes:
  mysql_data:
    driver: local
```

---

## 5. SQLAlchemy ORM 模型约定

### 5.1 基类

```python
# app/models/base.py
from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    """所有表的时间戳 Mixin"""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)

class SoftDeleteMixin:
    """软删除 Mixin"""
    is_deleted = Column(Boolean, default=False, nullable=False)
```

### 5.2 模型文件组织

```
app/models/
├── __init__.py           # 导出所有模型
├── base.py               # Base, Mixin
├── migration_task.py     # MigrationTask
├── instance_mapping.py   # InstanceMapping
├── source_snapshot.py    # SourceClbSnapshot, SourceListener, SourceForwardingRule,
│                         #   SourceHealthCheck, SourceAclPolicy
├── mapping_result.py     # MappingResult, IncompatibleItem
├── plan_item.py          # MigrationPlanItem
├── execution_log.py      # ExecutionLog
├── report.py             # MigrationReport, ReportDetail
└── enum_mapping.py       # EnumMappingRule
```

---

## 6. 数据库迁移管理

```bash
# 初始化迁移
flask db init

# 生成迁移脚本
flask db migrate -m "initial schema"

# 执行迁移
flask db upgrade

# 回滚
flask db downgrade
```

---

## 7. 索引策略

| 表 | 索引 | 用途 |
|---|---|---|
| migration_task | `uk_task_no` | 任务编号唯一查询 |
| migration_task | `idx_status` | 按状态筛选任务列表 |
| migration_task | `idx_created_at` | 按时间排序 |
| instance_mapping | `idx_task_id` | 按任务查关联映射 |
| source_listener | `idx_port_proto` | 按实例+端口+协议定位监听器 |
| mapping_result | `idx_mapping_status` | 按映射状态筛选 |
| migration_plan_item | `idx_task_seq` | 按任务+顺序号遍历执行队列 |
| migration_plan_item | `idx_status` | 断点续传查找首个非 success 项 |
| execution_log | `idx_task_logged` | 按任务+时间查日志 |
| report_detail | `idx_category` | 按分类筛选报告明细 |

---

## 8. 关键查询场景

### 8.1 断点续传 — 查找第一个未完成项

```sql
SELECT * FROM migration_plan_item
WHERE task_id = ? AND status NOT IN ('success', 'skipped', 'cancelled')
ORDER BY seq_no ASC
LIMIT 1;
```

### 8.2 迁移报告统计

```sql
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
    SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) AS skipped_count
FROM migration_plan_item
WHERE task_id = ?;
```

### 8.3 不兼容项汇总

```sql
SELECT ii.*, mr.source_description
FROM incompatible_item ii
JOIN mapping_result mr ON ii.mapping_result_id = mr.id
WHERE ii.task_id = ?
ORDER BY ii.severity DESC, ii.id ASC;
```

### 8.4 实时进度计算

```sql
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN status IN ('success','failed','skipped') THEN 1 ELSE 0 END) AS completed,
    ROUND(SUM(CASE WHEN status IN ('success','failed','skipped') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS progress
FROM migration_plan_item
WHERE task_id = ?;
```

---

## 9. .env 数据库配置示例

```ini
# MySQL 连接配置
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=lb2tencentcloud
MYSQL_USER=lb2tc
MYSQL_PASSWORD=lb2tc_pass_2026
MYSQL_ROOT_PASSWORD=lb2tc_root_2026

# SQLAlchemy 连接串
DATABASE_URL=mysql+pymysql://lb2tc:lb2tc_pass_2026@mysql:3306/lb2tencentcloud?charset=utf8mb4
```
