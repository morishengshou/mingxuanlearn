要点总结：
- ir.cron 最小粒度是分钟，不能原生支持秒级。
- 可通过外部调度器（如 systemd timer、Celery/Beat、APScheduler、Linux cron 每分钟+内部“秒级循环”）来实现秒级触发。
- 为避免并发冲突，需在方法执行时加“分布式锁”（数据库行级锁或 Redis 锁）或使用 Odoo 的 queue/job 模块并发控制。
- 还要考虑幂等性、超时与故障恢复。

下面给你几种实战方案，按复杂度从低到高排列。

方案A：ir.cron 每分钟 + 进程内秒级循环 + 分布式锁
- 思路：用 ir.cron 每分钟启动一次“守护任务”，在这 60 秒内循环每 N 秒调用你的方法。用数据库锁或 Redis 锁确保同一时刻只有一个 worker 运行。
- 实现步骤：
  1) 创建 ir.cron，interval_number=1, interval_type='minutes'。
  2) 在 Cron 方法中执行一个秒级循环，例如每 5 秒一次，直到 60 秒结束。
  3) 每次调用目标方法前先尝试获取锁；拿不到锁则跳过。
- 代码示例（PostgreSQL advisory lock，无需新表，简单可靠）：

```python
# -*- coding: utf-8 -*-
from odoo import api, models
import time
import logging

_logger = logging.getLogger(__name__)

ADVISORY_LOCK_KEY = 987654321  # 随意固定整数，建议每个任务不同

class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'

    @api.model
    def my_action(self):
        # 幂等逻辑放这里
        _logger.info("Running my_action()")
        # ... 实际业务 ...

    @api.model
    def _try_acquire_pg_lock(self, cr, key):
        # SELECT pg_try_advisory_lock(key) -> True/False
        cr.execute('SELECT pg_try_advisory_lock(%s)', (key,))
        return cr.fetchone()[0]

    @api.model
    def _release_pg_lock(self, cr, key):
        cr.execute('SELECT pg_advisory_unlock(%s)', (key,))

    @api.model
    def cron_runner_seconds(self, seconds_interval=5, runtime_window=55, lock_key=ADVISORY_LOCK_KEY):
        """
        每分钟由 ir.cron 触发一次，在 runtime_window 秒内每 seconds_interval 秒跑一次 my_action。
        使用 PG advisory lock 确保同一时刻只有一个进程在执行。
        """
        start = time.time()
        # 外层“调度器”也可使用锁，防止多 worker 同时跑同一循环
        cr = self.env.cr
        got_loop_lock = self._try_acquire_pg_lock(cr, lock_key)
        if not got_loop_lock:
            _logger.info("cron_runner_seconds: another loop is active, skip this minute.")
            return

        try:
            while time.time() - start < runtime_window:
                # 对单次执行也可用一个“子锁键”，但若整个循环独占，一个锁就足够
                try:
                    self.my_action()
                except Exception:
                    _logger.exception("my_action failed")
                # 睡眠秒级
                time.sleep(seconds_interval)
        finally:
            self._release_pg_lock(cr, lock_key)
```

- 优点：不引入外部组件；PG advisory lock 跨 worker 生效；实现简单。
- 注意：
  - seconds_interval 设置要小于 runtime_window。
  - 任务执行时长应明显小于间隔，否则会漂移或堆积。
  - Odoo Worker 不建议长时间阻塞；本方案每分钟阻塞约 55 秒，需评估并发容量。可单独为该任务部署一个专用 worker 进程或使用长轮询容忍。

方案B：数据库行级锁（FOR UPDATE SKIP LOCKED）实现单实例
- 思路：建一条“锁记录”，执行前 select for update skip locked，如果拿到即执行，否则跳过。
- 代码示例：

```python
# -*- coding: utf-8 -*-
from odoo import api, fields, models
import time, logging
_logger = logging.getLogger(__name__)

class MyLock(models.Model):
    _name = 'my.lock'
    _description = 'Lock Row'
    name = fields.Char(default='my_action_lock', index=True, unique=True)

class MyModel(models.Model):
    _name = 'my.model'

    @api.model
    def _acquire_row_lock(self):
        # 确保存在唯一锁记录
        lock = self.env['my.lock'].sudo().search([('name', '=', 'my_action_lock')], limit=1)
        if not lock:
            lock = self.env['my.lock'].sudo().create({'name': 'my_action_lock'})
        # 尝试加行锁（跳过被锁的行）
        self.env.cr.execute("""
            SELECT id FROM my_lock
            WHERE name = %s
            FOR UPDATE SKIP LOCKED
        """, ('my_action_lock',))
        row = self.env.cr.fetchone()
        return bool(row)

    @api.model
    def cron_runner_seconds(self, seconds_interval=5, runtime_window=55):
        start = time.time()
        if not self._acquire_row_lock():
            _logger.info("Another runner active, skip.")
            return
        try:
            while time.time() - start < runtime_window:
                self.my_action()
                time.sleep(seconds_interval)
        finally:
            # 行锁随事务结束释放，无需显式释放
            pass
```

- 优点：纯数据库解决，不需要固定整数 key。
- 注意：需要在同一事务内保持锁（Odoo 会在方法结束时提交/释放）；因此循环期间不要手动 commit，否则锁会释放。避免调用会触发自动 commit 的操作。

方案C：使用 OCA queue_job 或 Odoo 16+ queue 机制并发=1
- 思路：将任务封装为队列作业，队列并发度设为1，且使用 channel/identity key 保证唯一运行。外部秒级触发器持续 enqueue，但因并发=1，最多一个在跑。
- 步骤：
  - 安装 OCA/queue, queue_job。
  - 定义 job @job(queue='my_channel', identity_key='my_action_singleton')。
  - channel 并发设为1。
- 优点：自带重试、超时、监控。
- 注意：仍需有秒级触发器（见方案D/E）。

方案D：系统级调度器（systemd timer 或 cron+curl）+ Odoo JSON-RPC/Controller
- 思路：在服务器用 systemd timer 每5秒触发一次，调用一个 Odoo 控制器或 JSON-RPC 执行方法。控制器内部加锁。
- 示例（概念）：
  - systemd timer: OnUnitActiveSec=5s
  - service: curl -s -X POST https://your.odoo/yourhook?token=... 
  - 控制器中获取 PG advisory lock，执行业务。
- 优点：真正的秒级，不阻塞 Odoo worker 太久；更稳定。
- 注意：要做鉴权、重试、超时。

方案E：APScheduler/Celery Beat 外部调度 + Redis 锁
- 思路：单独跑一个 Python 服务（APScheduler 每5秒触发），通过 XML-RPC/JSON-RPC 调 Odoo；用 Redis 分布式锁（如 redlock）确保唯一运行。
- 优点：弹性最好，运维标准化。
- 注意：引入外部组件。

并发与一致性建议
- 幂等性：my_action 应可安全重复执行（基于时间戳/版本号/唯一键去重）。
- 锁超时：PG advisory lock 不会自动过期，确保 finally 释放；异常时也要释放或借助 Odoo/PG 会话结束释放。
- 执行超时：为单次运行设置软/硬超时，避免卡死。
- 观测性：打日志+统计最后执行时间，便于监控。
- 资源：避免在 Odoo 普通 worker 长循环；必要时专门开一个 worker 或走外部调度。

推荐组合
- 如果不想引入外部组件：采用方案A或B；选 A（PG advisory lock）最省事。
- 如果追求稳定与可维护：方案D（systemd timer）或方案E（APScheduler/Celery），配合队列/锁，效果最佳。

如果你愿意，我可以根据你的 Odoo 版本（例如 14/15/16/17）、部署方式（多worker、Odoo.sh、K8s）和期望的秒级间隔，给你一份完整可用的模块代码或 systemd 配置示例。