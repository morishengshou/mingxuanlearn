任务编号：{TASK_ID}
任务名称：{TASK_NAME}

背景：
{BACKGROUND}

请先阅读：
{REQUIRED_FILES}

本任务范围：
{IN_SCOPE}

明确不做：
{OUT_OF_SCOPE}

输入契约：
{INPUT_CONTRACT}

输出契约：
{OUTPUT_CONTRACT}

必须保持的业务不变量：
{INVARIANTS}

验收条件：
{ACCEPTANCE_CRITERIA}

要求：
1. 先检查已有代码，不重复建立相同能力。
2. 不擅自修改契约。
3. 给出最小改动计划。
4. 实现对应单元测试和必要集成测试。
5. 考虑重复请求、并发、权限不足和外部服务失败。
6. 第三方接口必须核实锁定版本。
7. 不伪造测试结果。
8. 最后提供文件清单、测试结果和回滚方式。