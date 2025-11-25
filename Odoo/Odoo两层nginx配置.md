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