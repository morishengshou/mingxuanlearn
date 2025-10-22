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


# Odoo18官方镜像
简要结论：
- 官方 Odoo 18 Docker 镜像默认将日志输出到 stdout/stderr，由 Docker 日志驱动管理，不走文件日志，因此容器内“开启 logrotate”并不是正确路径。
- 你有两种主流方案：
  1) 在宿主机层面对 Docker 日志进行轮转（推荐）。
  2) 让 Odoo 写入文件，再用宿主机上的 logrotate 轮转这些文件（不太推荐，但可行）。

以下给出两种方案的做法。

方案一：在宿主机对 Docker 日志轮转（推荐）
- 适用场景：你沿用镜像默认行为，让 Odoo 打印到 stdout/stderr。
- 操作方式取决于你的 Docker 引擎日志驱动（默认 json-file；在 Docker Desktop 或部分平台可能是 journald）。

A. json-file 驱动（默认）
- 全局设置（影响所有容器）：
  编辑宿主机 /etc/docker/daemon.json（不存在就新建）：
  {
    "log-driver": "json-file",
    "log-opts": {
      "max-size": "100m",
      "max-file": "10",
      "compress": "true"
    }
  }
  然后重启 Docker 守护进程：
  sudo systemctl restart docker
- 仅对 Odoo 容器生效（docker run 示例）：
  docker run -d --name odoo \
    --log-driver json-file \
    --log-opt max-size=100m \
    --log-opt max-file=10 \
    --log-opt compress=true \
    -p 8069:8069 \
    --link db:db \
    -e ... \
    odoo:18
- Docker Compose 示例（推荐）：
  services:
    odoo:
      image: odoo:18
      ports: ["8069:8069"]
      logging:
        driver: json-file
        options:
          max-size: "100m"
          max-file: "10"
          compress: "true"

B. journald 驱动
- 如果你的 Docker 配置使用 "log-driver": "journald"，则日志进 journald。轮转由 systemd-journald 管理，调整 /etc/systemd/journald.conf：
  - SystemMaxUse=5G
  - SystemMaxFileSize=200M
  - MaxRetentionSec=30day
  修改后执行：
  sudo systemctl restart systemd-journald

方案二：写入文件并用宿主机 logrotate 管理（可行但不如方案一简单）
- 适用场景：你必须保留传统的文件日志，例如对接外部代理或合规需求。
- 步骤：
  1) 创建宿主机日志目录并授予权限：
     sudo mkdir -p /var/log/odoo
     sudo chown 1000:1000 /var/log/odoo
     说明：官方镜像内 odoo 用户通常为 uid/gid 1000。
  2) 将该目录挂载进容器，并让 Odoo 写文件日志：
     - 在 odoo.conf 里设置 logfile=/var/log/odoo/odoo.log，或在启动参数里加 --logfile=/var/log/odoo/odoo.log。
     - Docker Compose 示例：
       services:
         odoo:
           image: odoo:18
           volumes:
             - /var/log/odoo:/var/log/odoo
             - odoo_data:/var/lib/odoo
           command: >
             odoo
             --logfile=/var/log/odoo/odoo.log
             --logrotate=False
           # 注意：把 Odoo 自带的内置轮转关掉（若默认开启），统一交给 logrotate
  3) 在宿主机新增 logrotate 规则，例如 /etc/logrotate.d/odoo：
     /var/log/odoo/odoo.log {
       daily
       rotate 14
       compress
       delaycompress
       missingok
       notifempty
       create 640 1000 1000
       sharedscripts
       copytruncate
     }
     说明：
     - 在容器内进程无法接收宿主机的 postrotate 信号时，使用 copytruncate 最稳妥，避免需要向容器发 USR1 或重启。
     - 若你愿意重载日志句柄，也可以在 postrotate 中调用 docker exec 发送 USR1 或 reload，但复杂度更高。

常见问题与建议
- 既用 stdout 又想本地文件备份？建议只选其一，或在宿主机用 docker logs 导出时再做落盘。
- 使用 ELK/Promtail/Fluent Bit？继续让容器走 stdout，然后在宿主机以日志驱动或日志收集器对接，避免在容器内搞 logrotate。
- 确认当前驱动：docker inspect <container> | jq -r '.[0].HostConfig.LogConfig'

简单推荐
- 没有强制文件日志需求：用方案一，设置 json-file 的 max-size/max-file 即可。
- 有合规存档需求：方案二，用宿主机 logrotate，容器只负责写文件，避免在容器内安装 logrotate。