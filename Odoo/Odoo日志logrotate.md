简要回答：没有被“移除”，但官方安装方式和打包方式的变化，导致不同部署渠道下的logrotate行为不一致，很多人会以为没了。

详情说明：
- 传统上，Debian/Ubuntu 下通过官方 .deb 包安装的 Odoo，会在 /etc/logrotate.d/odoo 或 /etc/logrotate.d/odoo14（随版本不同而变）放置 logrotate 配置，配合 /var/log/odoo/odoo.log 之类的日志文件一起轮转。
- 从 Odoo 13 之后，官方更鼓励用 systemd 管理服务与日志，且许多部署直接让 Odoo 将日志写到 stdout/stderr，由 journald 收集。这种情况下，不再需要 logrotate，因为日志由 journald 管理（可通过 journalctl 和 systemd-journald 的持久化与轮转策略控制），于是你在系统里可能看不到 Odoo 的 logrotate 配置，给人“被移除”的感觉。
- 如果你是通过源代码安装、pip 安装、Docker 镜像或自定义 systemd 单元文件部署，默认不会自动安装 logrotate 配置。这同样会让人误以为新版本不提供该项。
- 一些发行版或第三方打包（例如某些社区仓库）仍然会附带 logrotate 配置，这取决于打包者，而不是 Odoo 核心版本本身。

如何选择与检查：
- 使用 journald：如果你的 systemd 服务文件中没有指定 --logfile，且 StandardOutput=journal 或默认继承，那么日志走 journald。通过 journalctl -u odoo.service 查看；轮转由 journald 配置管理（/etc/systemd/journald.conf）。
- 使用文件日志：如果你在 odoo.conf 里设置了 logfile=/var/log/odoo/odoo.log，则建议：
  - 检查是否存在 /etc/logrotate.d/odoo*。
  - 若不存在，手动添加一份 logrotate 规则，例如：
    /var/log/odoo/odoo.log {
        weekly
        rotate 12
        compress
        delaycompress
        missingok
        notifempty
        create 640 odoo odoo
        sharedscripts
        postrotate
            systemctl kill -s USR1 odoo.service 2>/dev/null || true
        endscript
    }
    说明：USR1 信号会让多数 Python logging.handlers 或守护进程按需重新打开日志文件；若你的 Odoo 不处理 USR1，可改为 systemctl restart odoo.service，或使用 copytruncate。
- Docker 部署：通常直接用 Docker 的日志驱动或外部日志系统；logrotate 不参与容器内 stdout 日志的轮转，需在 Docker 层或外部收集端配置。

结论：
- Odoo 13+ 并未在软件层面“移除 logrotate 支持”，而是随着 systemd/journald 与不同打包方式的采用，默认不一定附带 logrotate 配置。是否存在取决于你的安装渠道与日志输出方式。