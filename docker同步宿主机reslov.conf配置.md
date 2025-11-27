要在 docker-compose up 时“同步宿主机的 DNS 配置”，有三种主路可选。不同环境适用性不同，优先级从稳妥到激进排列如下：

方案 A：使用 Docker 守护进程的全局默认 DNS（推荐，简单稳妥）
- 将宿主机当前的 DNS 写入 /etc/docker/daemon.json，让之后创建的所有容器默认使用这些 DNS。
- 步骤：
  1) 从宿主机读取当前 resolv.conf 的有效上游地址（避免 127.0.0.53/127.0.0.1 这类本地 stub）：
     - cat /etc/resolv.conf
  2) 编辑 /etc/docker/daemon.json，例如：
     - {
         "dns": ["223.5.5.5","114.114.114.114"],
         "dns-search": ["example.com"],
         "dns-opts": ["ndots:1"]
       }
  3) 重启 Docker：
     - sudo systemctl daemon-reload
     - sudo systemctl restart docker
  4) 之后执行 docker compose up -d，新容器会自动使用这些 DNS。无需在 compose 文件里写死 DNS。
- 说明：这是“在 up 时自动使用宿主配置”的等价做法，但需要你把宿主机的当前配置固化到 Docker 守护进程级别。宿主机 DNS 若频繁变更，则需同步更新 daemon.json 并重启 Docker。

方案 B：在 docker-compose.yml 中显式跟随宿主配置（可控、需要维护）
- 手动把宿主机当前 DNS 写进 compose 文件，使每次 up 都应用：
- 示例：
  - services:
      app:
        image: your-image
        dns:
          - 223.5.5.5
          - 114.114.114.114
        dns_search:
          - example.com
        dns_opt:
          - ndots:1
- 适合固定网络环境。若宿主 DNS 会改动，你需要更新 compose 配置并重新 up --force-recreate。

方案 C：直接把宿主 /etc/resolv.conf 挂载进容器（动态同步，需谨慎）
- 让容器在运行时实时“继承”宿主的 resolv.conf：
  - services:
      app:
        image: your-image
        volumes:
          - /etc/resolv.conf:/etc/resolv.conf:ro
- 优点：宿主机 resolv.conf 改了，容器内立即生效（无需重建）。
- 风险与注意：
  - 如果宿主 resolv.conf 使用本地 stub（nameserver 127.0.0.53 或 127.0.0.1），容器通常访问不到该回环地址，解析会失败。解决办法是改为在 A 或 B 中明确指定上游 DNS。
  - 某些基础镜像会在启动脚本中覆盖 /etc/resolv.conf，挂载可避免被覆盖，但要用 :ro 保护宿主文件。
  - 已运行的容器无法追加挂载，需重建。

可选增强：用环境变量或生成脚本在 up 前自动注入 DNS
- 若你希望“每次 up 前自动读取宿主 resolv.conf 并写入 compose”，可以做一个小脚本：
  - 读取宿主 resolv.conf 中的有效 nameserver（过滤 127.0.0.0/8）
  - 生成一个 .env 文件或 docker-compose.override.yml，把 dns/dns_search/dns_opt 写入
  - 再执行 docker compose up -d
- 示例 Bash 片段（生成 override 文件）：
  - #!/usr/bin/env bash
    set -euo pipefail
    ns=$(grep -E '^nameserver ' /etc/resolv.conf | awk '{print $2}' | grep -Ev '^127\.' | xargs)
    searches=$(grep -E '^search ' /etc/resolv.conf | cut -d' ' -f2-)
    opts=$(grep -E '^options ' /etc/resolv.conf | cut -d' ' -f2-)
    cat > docker-compose.override.yml <<'YAML'
    version: "3.8"
    services:
      app:
        dns:
    YAML
    for ip in $ns; do echo "          - $ip" >> docker-compose.override.yml; done
    if [ -n "${searches:-}" ]; then
      echo "        dns_search:" >> docker-compose.override.yml
      for s in $searches; do echo "          - $s" >> docker-compose.override.yml; done
    fi
    if [ -n "${opts:-}" ]; then
      echo "        dns_opt:" >> docker-compose.override.yml
      for o in $opts; do echo "          - $o" >> docker-compose.override.yml; done
    fi
    docker compose up -d --force-recreate
- 这样你保持 docker-compose.yml 干净，把“跟随宿主”的逻辑外置。注意根据你的服务名替换 app。

验证与排错
- 检查容器内 resolv.conf：
  - docker compose exec app cat /etc/resolv.conf
- 测试解析：
  - docker compose exec app getent hosts example.com
- 对比 Docker 视图：
  - docker inspect <container_id> | jq '.[0].HostConfig.Dns, .[0].HostConfig.DnsSearch, .[0].HostConfig.DnsOptions'
- 若解析慢或失败，检查是否存在 ndots 过大、IPv6 优先、或本地 stub 的问题。

简要结论
- 想“开箱即用”：用方案 A（Docker 守护进程默认 DNS）。
- 想“每次 up 跟宿主最新配置”：用方案 C 挂载，确保 nameserver 可达；或用“生成 override”的脚本自动化注入。