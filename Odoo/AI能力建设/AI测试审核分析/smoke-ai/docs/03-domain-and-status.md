## 6.1 身份标识

不能只靠“产品＋日期＋用例名”识别一条结果。

建议完整身份包括：

```text
company_id
product_id
build_id
run_id
plan_revision
case_id
case_revision
parameter_set_id
device_id
attempt_id
```

关键说明：

- `build_id` 应能关联实际刷入的构建，而非只记录文件名。
- `run_id` 表示一次冒烟批次。
- `attempt_id` 表示一次具体执行，重跑生成新值。
- 参数化用例必须区别参数集合。
- 同日多次构建不能互相覆盖。
- 测试计划和特性映射应在批次创建时快照。

“昨天合入”是构建流程背景，不应成为唯一数据定位依据。报告应明确记录构建版本、分支、提交清单或构建清单摘要。

## 6.2 推荐 Odoo 模型

以下名称为拟议名称，最终优先映射到你的现有模型。

| 模型 | 作用 |
|---|---|
| `smoke.run` | 一次冒烟批次 |
| `smoke.plan.item` | 本批次预期执行项、必测属性、特性映射快照 |
| `smoke.case.execution` | 一次用例执行的原始事实 |
| `smoke.artifact` | 日志和其他制品元信息 |
| `smoke.review.job` | AI 复核任务、租约、重试状态 |
| `smoke.review` | AI 或人工复核记录，追加式保存 |
| `smoke.issue` | 问题主体 |
| `smoke.issue.signature` | 问题签名、适用范围、复用规则 |
| `smoke.issue.occurrence` | 某问题在某执行中的一次出现 |
| `smoke.feature.result` | 某批次中特性的汇总状态 |
| `smoke.report` | 结构化报告与发布快照 |
| `smoke.operation` | 幂等操作记录、请求摘要、处理结果 |

不一定要全部独立建表；例如现有问题模型能承载时，`smoke.issue` 应采用扩展或关联方式。

## 6.3 三层状态必须分开

### 第一层：原始执行结果

```text
PASS
FAIL
ERROR
SKIP
NOT_RUN
```

只能由测试结果接入流程写入，AI 无权改写。

### 第二层：失败归因

```text
PRODUCT_DEFECT       产品缺陷
TEST_DEFECT          用例或测试框架问题
ENVIRONMENT          外部测试环境问题
INFRASTRUCTURE       执行机、刷机、调度等基础设施问题
UNKNOWN              证据不足或存在冲突
```

注意：

> 同一现象可以有不同原因。例如 ADB 断开，可能是网络问题，也可能是设备系统崩溃。

因此不能建立“出现 adb offline 就判环境问题”的简单通用规则。

### 第三层：有效验证结论

```text
PASS
FAIL
BLOCKED
NEEDS_REVIEW
NOT_TESTED
```

| 情况 | 建议结论 |
|---|---|
| 有效执行通过，且满足完整性检查 | PASS |
| 已确认产品缺陷 | FAIL |
| 环境／测试／基础设施问题导致无法有效验证 | BLOCKED |
| 根因不确定、证据矛盾、待人工确认 | NEEDS_REVIEW |
| 未执行或不满足执行覆盖要求 | NOT_TESTED |

## 6.4 特性聚合规则

建议用确定性代码实现，默认优先级为：

```text
FAIL
  > NEEDS_REVIEW
  > BLOCKED
  > NOT_TESTED
  > PASS
```

对于某特性所要求的验证项：

1. 任一有效结论为 `FAIL`，特性为 `FAIL`。
2. 否则存在 `NEEDS_REVIEW`，特性为 `NEEDS_REVIEW`。
3. 否则存在 `BLOCKED`，特性为 `BLOCKED`。
4. 否则存在缺失／未测项，特性为 `NOT_TESTED`。
5. 只有全部必需验证项有效通过，特性才为 `PASS`。

补充约束：

- 零用例特性不能自动变绿。
- 已知产品缺陷仍然失败。
- 被豁免的问题单独显示“豁免”，不能伪装成正常通过。
- 重跑通过不能删除此前失败；是否接受重跑覆盖，要有明确策略。
- 当一次用例关联多个特性时，产品级用例统计不能重复计数。

## 6.5 人工与 AI 的优先级

```text
人工确认／覆盖
    > 已批准的确定性规则
    > AI 建议
```

人工修改必须记录：

- 修改人。
- 修改时间。
- 原结论。
- 新结论。
- 修改原因。
- 是否允许形成复用规则。

AI 重新分析只能追加新建议，不能覆盖已锁定的人工结论。