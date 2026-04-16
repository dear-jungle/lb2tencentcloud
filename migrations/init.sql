-- CLB 迁移工具数据库初始化脚本
-- 此脚本由 docker-entrypoint-initdb.d 自动执行

USE lb2tencentcloud;

-- 枚举值映射规则初始数据
CREATE TABLE IF NOT EXISTS enum_mapping_rule (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category        VARCHAR(32)     NOT NULL COMMENT '映射分类',
    source_value    VARCHAR(64)     NOT NULL COMMENT '阿里云枚举值',
    target_value    VARCHAR(64)     NULL COMMENT '腾讯云枚举值',
    is_compatible   TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '是否兼容',
    remark          VARCHAR(256)    NULL COMMENT '备注',
    created_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    UNIQUE KEY uk_category_source (category, source_value),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='枚举值映射规则表';

-- 调度算法映射
INSERT INTO enum_mapping_rule (category, source_value, target_value, is_compatible, remark) VALUES
('scheduler', 'wrr',  'WRR',        1, '加权轮询'),
('scheduler', 'wlc',  'LEAST_CONN', 1, '加权最小连接数'),
('scheduler', 'rr',   'WRR',        1, '轮询 → 加权轮询（权重均等）'),
('scheduler', 'sch',  NULL,          0, '源地址哈希，腾讯云 CLB 不支持'),
('scheduler', 'tch',  NULL,          0, '四元组哈希，腾讯云 CLB 不支持'),
('scheduler', 'qch',  NULL,          0, '五元组哈希，腾讯云 CLB 不支持');

-- 协议类型映射
INSERT INTO enum_mapping_rule (category, source_value, target_value, is_compatible, remark) VALUES
('protocol', 'tcp',   'TCP',   1, 'TCP 监听器'),
('protocol', 'udp',   'UDP',   1, 'UDP 监听器'),
('protocol', 'http',  'HTTP',  1, 'HTTP 七层监听器'),
('protocol', 'https', 'HTTPS', 1, 'HTTPS 七层监听器');

-- 健康检查类型映射
INSERT INTO enum_mapping_rule (category, source_value, target_value, is_compatible, remark) VALUES
('health_check_type', 'tcp',  'TCP',  1, 'TCP 健康检查'),
('health_check_type', 'http', 'HTTP', 1, 'HTTP 健康检查');

-- ACL 类型映射
INSERT INTO enum_mapping_rule (category, source_value, target_value, is_compatible, remark) VALUES
('acl_type', 'white', 'white', 1, '白名单'),
('acl_type', 'black', 'black', 1, '黑名单');

-- 会话保持类型映射
INSERT INTO enum_mapping_rule (category, source_value, target_value, is_compatible, remark) VALUES
('sticky_session_type', 'insert', 'NORMAL',     1, '植入 Cookie → 腾讯云 CLB 管理的 Cookie'),
('sticky_session_type', 'server', 'CUSTOMIZED', 1, '重写 Cookie → 自定义 Cookie');
