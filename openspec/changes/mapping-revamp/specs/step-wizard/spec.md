# step-wizard Specification (Delta)

## MODIFIED Requirements

### Requirement: 步骤名称更新
系统 SHALL 将向导步骤名称更新：步骤2 从"选择实例"改为"实例关联"，步骤3 从"配置映射"改为"配置对比"。

#### Scenario: 步骤导航条展示
- **WHEN** 用户查看顶部 6 步导航条
- **THEN** 步骤名称依次为：凭证配置、实例关联、配置对比、迁移计划、执行迁移、迁移报告
