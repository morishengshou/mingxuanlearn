在两层 Nginx 的情况下，只要**后端（你服务器上的 Nginx）正确保留 `/dtdashboardbg` 前缀并把它告诉 Odoo**，Odoo 就会生成带此前缀的所有链接。下面给出推荐的做法。

---

## 1. 前端 Nginx（例：云上网关）配置要点
- 把 `http://example.com/dtdashboardbg/…` 的请求完整转发到你服务器 `http://your-server-ip:8069/dtdashboardbg/…`，不要去掉路径前缀。
- 可顺便把 `X-Forwarded-*` 头转发下去，便于后端获取真实协议、Host。
- （可选）在这一层就设置 `proxy_set_header X-Forwarded-Prefix /dtdashboardbg;`，也可以由后端再加一次。

---

## 2. 你服务器上的 Nginx（监听 8069）配置示例

假设 Odoo 应用实际监听 `127.0.0.1:8069`（或改为 8070 均可），再通过同机 Nginx 做反代并加前缀。

```nginx
# /etc/nginx/conf.d/odoo-subpath.conf

upstream odoo_app {
    server 127.0.0.1:8070;   # 这里写 Odoo 实际监听端口
}

upstream odoo_longpolling {
    server 127.0.0.1:8072;   # gevent/longpolling 端口
}

server {
    listen 8069;
    server_name _;           # 或你的内网域名

    # 主 Web 请求（保留子路径）
    location ^~ /dtdashboardbg/ {
        proxy_pass http://odoo_app/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 告诉 Odoo 自己挂在 /dtdashboardbg 下
        proxy_set_header X-Forwarded-Prefix /dtdashboardbg;

        proxy_redirect off;
        proxy_cookie_path / /dtdashboardbg/;
    }

    # 长轮询（若启用 Bus/Discuss 实时功能）
    location ^~ /dtdashboardbg/longpolling/ {
        proxy_pass http://odoo_longpolling/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Prefix /dtdashboardbg;

        proxy_redirect off;
        proxy_buffering off;
    }
}
```

关键点：

1. `location ^~ /dtdashboardbg/` 确保带此前缀的请求被匹配。
2. `proxy_pass http://odoo_app/;` 末尾的 `/` 让 `/dtdashboardbg/...` 之后的路径原样传给 Odoo。
3. `proxy_set_header X-Forwarded-Prefix /dtdashboardbg;` 是让 Odoo 知道自己运行在子路径的关键。
4. `proxy_cookie_path / /dtdashboardbg/;` 避免 Cookie 丢失前缀，确保登录状态正常。

---

## 3. Odoo 配置

在 `odoo.conf` 中启用代理模式并固定基础 URL：

```ini
[options]
proxy_mode = True
web.base.url = https://example.com/dtdashboardbg
web.base.url.freeze = True
```

- `proxy_mode = True` 让 Odoo 信任 `X-Forwarded-*` 头。
- `web.base.url` 指定完整访问 URL，带前缀。
- `web.base.url.freeze = True` 防止 Odoo 因管理员不同方式访问而重写该值。

重启服务：

```bash
sudo systemctl restart odoo
sudo systemctl reload nginx
```

---

## 4. 验证步骤

1. 通过浏览器访问 `http://example.com/dtdashboardbg/`。
2. 登录后在浏览器开发者工具查看任意链接或静态资源，确认其 URL 为 `https://example.com/dtdashboardbg/...`。
3. 若仍出现无前缀链接，检查：
   - 前后两层 Nginx 是否都保留了子路径。
   - `X-Forwarded-Prefix` 是否到达 Odoo（可在 Odoo 日志中启用 debug 查看请求头）。
   - 浏览器是否缓存了旧资产，可在 Odoo 后台清空资产或清理浏览器缓存。

这样配置后，即使有两层 Nginx，Odoo 也会认定自己运行在 `/dtdashboardbg` 子路径下，从而所有内部跳转、静态资源、通知链接都会自动带上该前缀。

# 第一层nginx配置
下面给出在“第一层”网关（位于 example.com 前端、只负责把 `/dtdashboardbg/` 路径转发到你服务器 8069 端口）的 Nginx 配置示例。此示例假设：

- 域名：`example.com`
- 第一层网关只做转发，不跑 Odoo。
- 你的服务器 IP：`203.0.113.10`（请替换为实际地址），在 8069 端口上运行第二层 Nginx。
- 第一层希望统一加上 `X-Forwarded-*` 信息和前缀。

```nginx
# /etc/nginx/conf.d/gateway-odoo.conf

upstream odoo_backend {
    server 203.0.113.10:8069;
}

server {
    listen 80;
    server_name example.com;

    # 若需要 HTTPS，可把 listen 换成 443 ssl 并配置证书，再在 80 上做重定向。

    # 把 /dtdashboardbg/ 下的所有请求转发到后端
    location ^~ /dtdashboardbg/ {
        proxy_pass http://odoo_backend;
        # 注意：这里不在 proxy_pass 末尾加 /，因为我们希望把完整路径（含 /dtdashboardbg）原样送给后端，
        # 让后端 Nginx 接着处理并继续保留前缀。

        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 告诉后端本次请求的前缀（便于最终传递到 Odoo）
        proxy_set_header X-Forwarded-Prefix /dtdashboardbg;

        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # 可选：其他路径由网关自行处理或返回 404
    location / {
        return 404;
    }
}
```

### 关键说明

1. **路径保留**  
   - 因为第二层 Nginx 还要根据 `/dtdashboardbg/` 路径去匹配、再写入 `X-Forwarded-Prefix`，所以这里的 `proxy_pass` 没有以 `/` 结尾，表示把原始路径完整转发过去。

2. **前缀头信息**  
   - `proxy_set_header X-Forwarded-Prefix /dtdashboardbg;` 虽可在第二层再设置一次，但提前加上能确保即使第二层漏配，Odoo 仍能拿到正确的前缀。

3. **长轮询**  
   - 如果第一层需要单独优化长轮询（例如 `/dtdashboardbg/longpolling/`），可以另建一个 `location`，或保持当前配置（因为第二层已经针对该路径做了专门处理）。示例：

     ```nginx
     location ^~ /dtdashboardbg/longpolling/ {
         proxy_pass http://odoo_backend;
         proxy_set_header Host $host;
         proxy_set_header X-Forwarded-Host $host;
         proxy_set_header X-Forwarded-Proto $scheme;
         proxy_set_header X-Forwarded-Port $server_port;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Prefix /dtdashboardbg;

         proxy_redirect off;
         proxy_http_version 1.1;
         proxy_set_header Connection "";
         proxy_buffering off;   # 长轮询建议关闭缓冲
     }
     ```

4. **HTTPS**  
   - 生产环境建议开启 HTTPS。可在 443 端口配置证书并监听，80 端口做 301 跳转：
     ```nginx
     server {
         listen 80;
         server_name example.com;
         return 301 https://$host$request_uri;
     }
     ```

配置完成后，重载第一层 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

这套配置确保第一层网关把带有 `/dtdashboardbg/` 的所有请求完整地、带上必要头信息地流转到你的服务器，从而第二层 Nginx 与 Odoo 能继续识别该前缀并生成正确的链接。

# 不配置upstream块

可以的，`proxy_pass` 完全可以直接指向具体的 IP（或域名），并不一定要先定义 `upstream`。例如：

```nginx
location ^~ /dtdashboardbg/ {
    proxy_pass http://203.0.113.10:8069;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Prefix /dtdashboardbg;
    proxy_redirect off;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
}
```

### 什么时候需要 `upstream`
- **负载均衡或多后端**：你想在多台服务器之间做轮询、`ip_hash` 等策略时，需要使用 `upstream`。
- **长连接/keepalive**：`upstream` 块可配置 `keepalive`，减少建立 TCP 连接的开销。
- **可读性/维护性**：统一的后端地址方便集中管理、重复引用。

如果只是单一 IP、端口，没有上述需求，直接在 `proxy_pass` 中写死地址即可，功能上没有问题。

