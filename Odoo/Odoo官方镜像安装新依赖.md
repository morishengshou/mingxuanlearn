下面给你一套**推荐做法**：不要直接改运行中的容器，而是**基于 Odoo 18 官方镜像重新构建一个自定义 Odoo 镜像**，在镜像构建阶段安装第三方模块需要的系统依赖和 Python 依赖，并在 `docker-compose.yml` 中使用这个新镜像。

---

## 一、推荐目录结构

假设你的项目目录如下：

```text
odoo18-docker/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── addons/
│   ├── third_party_module_1/
│   ├── third_party_module_2/
│   └── my_custom_module/
└── config/
    └── odoo.conf
```

说明：

- `Dockerfile`：基于官方 `odoo:18` 构建新镜像
- `requirements.txt`：放第三方模块需要的 Python 包
- `addons/`：放第三方开源模块和自研模块
- `config/odoo.conf`：Odoo 配置文件

---

## 二、编写 requirements.txt

例如：

```txt
openpyxl==3.1.5
pandas==2.2.3
xlrd==2.0.1
requests==2.32.3
zeep==4.3.1
```

如果你的模块有各自的 `requirements.txt`，也可以先汇总到项目根目录的 `requirements.txt` 中。

> 建议固定版本号，避免以后重新构建镜像时因为依赖升级导致不可复现的问题。

---

## 三、编写 Dockerfile

下面这个示例支持：

- 基于 `odoo:18`
- 使用指定的 apt 镜像站
- 使用指定的 PyPI 镜像站
- 安装系统依赖
- 安装 Python 依赖
- 清理 apt 缓存，减小镜像体积

```dockerfile
FROM odoo:18

USER root

ARG APT_MIRROR=mirrors.aliyun.com
ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com

# 替换 Debian apt 源
RUN set -eux; \
    . /etc/os-release; \
    cp /etc/apt/sources.list /etc/apt/sources.list.bak || true; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list; \
        sed -i "s|security.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list; \
    fi; \
    if [ -d /etc/apt/sources.list.d ]; then \
        find /etc/apt/sources.list.d -type f -name "*.list" -exec sed -i "s|deb.debian.org|${APT_MIRROR}|g" {} \; ; \
        find /etc/apt/sources.list.d -type f -name "*.list" -exec sed -i "s|security.debian.org|${APT_MIRROR}|g" {} \; ; \
    fi

# 安装系统依赖
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        git \
        curl \
    ; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

# 安装 Python 依赖
RUN set -eux; \
    pip3 install --no-cache-dir \
        --index-url="${PYPI_INDEX_URL}" \
        --trusted-host="${PYPI_TRUSTED_HOST}" \
        -r /tmp/requirements.txt

USER odoo
```

---

## 四、关于 apt 镜像源的注意点

Odoo 官方镜像通常基于 Debian。不同版本的 Debian 可能会使用不同的源配置方式，例如：

```text
/etc/apt/sources.list
```

或者：

```text
/etc/apt/sources.list.d/debian.sources
```

如果你发现构建时报 apt 源相关错误，可以进入官方镜像查看：

```bash
docker run --rm -it --entrypoint bash odoo:18
cat /etc/os-release
ls -l /etc/apt/
ls -l /etc/apt/sources.list.d/
cat /etc/apt/sources.list || true
cat /etc/apt/sources.list.d/*
```

如果是 Debian 12 Bookworm，并且使用 `.sources` 格式，你可以改成更稳妥的写法。

例如使用阿里云 Debian 源：

```dockerfile
FROM odoo:18

USER root

ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com

RUN set -eux; \
    cat > /etc/apt/sources.list <<'EOF'
deb https://mirrors.aliyun.com/debian bookworm main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian bookworm-updates main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware
EOF

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/*.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        git \
        curl \
    ; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN set -eux; \
    pip3 install --no-cache-dir \
        --index-url="${PYPI_INDEX_URL}" \
        --trusted-host="${PYPI_TRUSTED_HOST}" \
        -r /tmp/requirements.txt

USER odoo
```

如果你使用清华源，可以类似这样：

```dockerfile
RUN set -eux; \
    cat > /etc/apt/sources.list <<'EOF'
deb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm main contrib non-free non-free-firmware
deb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm-updates main contrib non-free non-free-firmware
deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware
EOF
```

PyPI 清华源：

```dockerfile
ARG PYPI_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PYPI_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
```

---

## 五、docker-compose.yml 示例

```yaml
services:
  db:
    image: postgres:15
    container_name: odoo18-db
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
    volumes:
      - odoo18-db-data:/var/lib/postgresql/data
    restart: unless-stopped

  odoo:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APT_MIRROR: mirrors.aliyun.com
        PYPI_INDEX_URL: https://mirrors.aliyun.com/pypi/simple/
        PYPI_TRUSTED_HOST: mirrors.aliyun.com
    image: my-odoo:18
    container_name: odoo18-web
    depends_on:
      - db
    ports:
      - "8069:8069"
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
    volumes:
      - odoo18-web-data:/var/lib/odoo
      - ./config:/etc/odoo
      - ./addons:/mnt/extra-addons
    restart: unless-stopped

volumes:
  odoo18-db-data:
  odoo18-web-data:
```

然后构建并启动：

```bash
docker compose build odoo
docker compose up -d
```

或者强制无缓存构建：

```bash
docker compose build --no-cache odoo
docker compose up -d
```

---

## 六、odoo.conf 示例

`config/odoo.conf`：

```ini
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
admin_passwd = admin
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
proxy_mode = True
```

注意：

```ini
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
```

要包含官方模块路径和你的自定义模块路径。

---

## 七、如果第三方模块需要 Node、Less、Sass 等依赖

有些 Odoo 模块可能还依赖前端构建工具，可以在 Dockerfile 中加入：

```dockerfile
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        nodejs \
        npm \
    ; \
    npm config set registry https://registry.npmmirror.com; \
    npm install -g rtlcss; \
    rm -rf /var/lib/apt/lists/*
```

如果需要 `less`：

```dockerfile
RUN npm config set registry https://registry.npmmirror.com \
    && npm install -g less less-plugin-clean-css
```

不过 Odoo 18 一般情况下不建议随意加入大量前端构建依赖，除非你的模块明确要求。

---

## 八、如果 Python 包需要编译，常见系统依赖

常见映射如下：

| Python 包/功能 | 可能需要的 apt 包 |
|---|---|
| `psycopg2` | `libpq-dev`, `gcc`, `python3-dev` |
| `lxml` | `libxml2-dev`, `libxslt1-dev`, `gcc`, `python3-dev` |
| `python-ldap` | `libldap2-dev`, `libsasl2-dev`, `python3-dev` |
| `Pillow` | `libjpeg-dev`, `zlib1g-dev` |
| `cryptography` | `libssl-dev`, `libffi-dev`, `rustc`, `cargo` |
| `pandas` | 通常优先使用 wheel，少数环境需要编译依赖 |
| `zeep` | 通常依赖 `lxml` |

如果某些包安装失败，通常需要根据报错补充 apt 依赖。

---

## 九、更推荐的生产镜像写法：构建依赖和运行依赖分离

上面的 Dockerfile 简单直接，但会把 `gcc`、`build-essential` 这类构建工具也留在最终镜像里。生产环境可以使用 wheelhouse 方式减少最终镜像体积。

示例：

```dockerfile
FROM odoo:18 AS builder

USER root

ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    ; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN set -eux; \
    pip3 wheel --no-cache-dir \
        --wheel-dir=/tmp/wheels \
        --index-url="${PYPI_INDEX_URL}" \
        --trusted-host="${PYPI_TRUSTED_HOST}" \
        -r /tmp/requirements.txt


FROM odoo:18

USER root

ARG APT_MIRROR=mirrors.aliyun.com

RUN set -eux; \
    cat > /etc/apt/sources.list <<'EOF'
deb https://mirrors.aliyun.com/debian bookworm main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian bookworm-updates main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware
EOF

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/*.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
        libldap-2.5-0 \
        libsasl2-2 \
        libssl3 \
        libffi8 \
        libpq5 \
        libjpeg62-turbo \
        zlib1g \
    ; \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /tmp/wheels /tmp/wheels
COPY requirements.txt /tmp/requirements.txt

RUN set -eux; \
    pip3 install --no-cache-dir \
        --no-index \
        --find-links=/tmp/wheels \
        -r /tmp/requirements.txt; \
    rm -rf /tmp/wheels /tmp/requirements.txt

USER odoo
```

不过要注意：

1. `builder` 阶段和最终阶段的基础镜像应尽量一致。
2. 最终阶段仍需要安装运行时动态库，例如 `libxml2`、`libxslt1.1`、`libpq5` 等。
3. 如果你的依赖都是纯 Python 或都有 wheel，简单 Dockerfile 已经足够。

---

## 十、是否要把 addons 复制进镜像？

有两种方式。

### 方式一：开发环境推荐挂载

```yaml
volumes:
  - ./addons:/mnt/extra-addons
```

优点：

- 修改模块代码后不用重新构建镜像
- 开发调试方便

缺点：

- 生产环境依赖宿主机目录
- 发布版本不够固定

---

### 方式二：生产环境推荐 COPY 进镜像

Dockerfile 中加入：

```dockerfile
COPY ./addons /mnt/extra-addons
```

并确保权限：

```dockerfile
RUN chown -R odoo:odoo /mnt/extra-addons
```

完整片段：

```dockerfile
COPY ./addons /mnt/extra-addons
RUN chown -R odoo:odoo /mnt/extra-addons
```

生产环境可以不再挂载 `./addons`：

```yaml
volumes:
  - odoo18-web-data:/var/lib/odoo
  - ./config:/etc/odoo
```

优点：

- 镜像包含完整应用代码
- 更方便 CI/CD
- 版本可追溯

缺点：

- 每次模块代码变化都要重新构建镜像

---

## 十一、一个比较完整的推荐版本

### Dockerfile

```dockerfile
FROM odoo:18

USER root

ARG DEBIAN_CODENAME=bookworm
ARG APT_MIRROR=https://mirrors.aliyun.com
ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/*.sources; \
    cat > /etc/apt/sources.list <<EOF
deb ${APT_MIRROR}/debian ${DEBIAN_CODENAME} main contrib non-free non-free-firmware
deb ${APT_MIRROR}/debian ${DEBIAN_CODENAME}-updates main contrib non-free non-free-firmware
deb ${APT_MIRROR}/debian-security ${DEBIAN_CODENAME}-security main contrib non-free non-free-firmware
EOF

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        git \
        curl \
    ; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN set -eux; \
    pip3 install --no-cache-dir \
        --index-url="${PYPI_INDEX_URL}" \
        --trusted-host="${PYPI_TRUSTED_HOST}" \
        -r /tmp/requirements.txt; \
    rm -f /tmp/requirements.txt

USER odoo
```

### docker-compose.yml

```yaml
services:
  db:
    image: postgres:15
    container_name: odoo18-db
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
    volumes:
      - odoo18-db-data:/var/lib/postgresql/data
    restart: unless-stopped

  odoo:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APT_MIRROR: https://mirrors.aliyun.com
        PYPI_INDEX_URL: https://mirrors.aliyun.com/pypi/simple/
        PYPI_TRUSTED_HOST: mirrors.aliyun.com
    image: my-odoo:18
    container_name: odoo18-web
    depends_on:
      - db
    ports:
      - "8069:8069"
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
    volumes:
      - odoo18-web-data:/var/lib/odoo
      - ./config:/etc/odoo
      - ./addons:/mnt/extra-addons
    restart: unless-stopped

volumes:
  odoo18-db-data:
  odoo18-web-data:
```

---

## 十二、构建、启动、更新模块

构建：

```bash
docker compose build odoo
```

启动：

```bash
docker compose up -d
```

查看日志：

```bash
docker compose logs -f odoo
```

进入 Odoo 容器：

```bash
docker compose exec odoo bash
```

检查 Python 依赖是否安装成功：

```bash
docker compose exec odoo python3 -c "import openpyxl; print(openpyxl.__version__)"
```

更新 Odoo 模块列表：

```bash
docker compose exec odoo odoo \
  -c /etc/odoo/odoo.conf \
  -d your_database_name \
  -u your_module_name \
  --stop-after-init
```

或者在 Odoo Web 后台：

```text
应用 → 更新应用列表 → 搜索并安装模块
```

---

## 十三、常见坑

### 1. 不要在运行中的容器里 `pip install`

例如：

```bash
docker exec -it odoo18-web pip3 install xxx
```

这只是临时改容器，容器重建后就没了。应该写进 Dockerfile。

---

### 2. 不要覆盖掉官方 addons_path

错误示例：

```ini
addons_path = /mnt/extra-addons
```

这样可能导致官方模块找不到。

推荐：

```ini
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
```

---

### 3. Python 包版本要兼容 Odoo 18 的 Python 版本

先查看镜像里的 Python 版本：

```bash
docker run --rm odoo:18 python3 --version
```

然后确认你的依赖包支持该 Python 版本。

---

### 4. pip 可能提示 externally-managed-environment

如果遇到类似：

```text
error: externally-managed-environment
```

可以尝试在 Dockerfile 中加：

```dockerfile
RUN pip3 install --break-system-packages ...
```

例如：

```dockerfile
RUN set -eux; \
    pip3 install --break-system-packages --no-cache-dir \
        --index-url="${PYPI_INDEX_URL}" \
        --trusted-host="${PYPI_TRUSTED_HOST}" \
        -r /tmp/requirements.txt
```

不过官方 Odoo 镜像通常已经适配了自己的 Python 包安装方式。是否需要这个参数取决于镜像基础系统和 pip 版本。

---

### 5. 公司内网 PyPI 镜像使用自签证书

如果你的 PyPI 镜像使用 HTTPS 但证书不是公共 CA 签发，建议把 CA 证书加入镜像：

```dockerfile
COPY company-ca.crt /usr/local/share/ca-certificates/company-ca.crt

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates; \
    update-ca-certificates; \
    rm -rf /var/lib/apt/lists/*
```

不推荐长期使用：

```bash
--trusted-host
```

它会降低 TLS 校验安全性。

---

## 十四、最简结论

你要做的是：

1. 新建 `Dockerfile`
2. `FROM odoo:18`
3. 切换到 `USER root`
4. 替换 apt 镜像源
5. 安装模块需要的系统依赖
6. 使用指定 PyPI 源 `pip3 install -r requirements.txt`
7. 切回 `USER odoo`
8. 在 `docker-compose.yml` 中把 `image: odoo:18` 改成 `build: .` 或你的自定义镜像

最小可用版：

```dockerfile
FROM odoo:18

USER root

ARG PYPI_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PYPI_TRUSTED_HOST=mirrors.aliyun.com

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/*.sources; \
    cat > /etc/apt/sources.list <<'EOF'
deb https://mirrors.aliyun.com/debian bookworm main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian bookworm-updates main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware
EOF

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
        git \
    ; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN pip3 install --no-cache-dir \
    --index-url="${PYPI_INDEX_URL}" \
    --trusted-host="${PYPI_TRUSTED_HOST}" \
    -r /tmp/requirements.txt

USER odoo
```

然后：

```bash
docker compose build
docker compose up -d
```