要把 Odoo 放在一个子路径（例如 `https://example.com/dtdashboardbg/`）下，需要同时配置 **Nginx** 和 **Odoo**，以确保：

1. 所有进入该路径的请求都被正确地转发到 Odoo。
2. Odoo 在生成链接、静态资源地址、跳转时都带上这个前缀。

---

## 1. Nginx 反向代理配置

假设 Odoo 在本机 `127.0.0.1:8069`，长轮询（LiveChat/Bus）在 `127.0.0.1:8072`。

```nginx
# /etc/nginx/conf.d/odoo.conf (示例)

upstream odoo_app {
    server 127.0.0.1:8069;
}

upstream odoo_longpolling {
    server 127.0.0.1:8072;
}

server {
    listen 80;
    server_name example.com;

    # 其他站点位置...

    # 主 web/HTTP 请求
    location ^~ /dtdashboardbg/ {
        proxy_pass http://odoo_app/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 很重要：告知 Odoo 自己是挂在 /dtdashboardbg
        proxy_set_header X-Forwarded-Prefix /dtdashboardbg;

        # 避免 Nginx 修改 Location 响应头
        proxy_redirect off;

        # 确保 Cookie 路径包含前缀
        proxy_cookie_path / /dtdashboardbg/;

        # gzip/缓存等可以按需添加
    }

    # 长轮询（若使用实时讨论、通知）
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

> 注意：`proxy_pass` 结尾包含 `/`，这样 Nginx 会把 `dtdashboardbg/` 之后的路径原样转发给 Odoo，否则会丢失子路径。

---

## 2. Odoo 配置

编辑 `odoo.conf`（通常位于 `/etc/odoo/odoo.conf`），关键参数如下：

```ini
[options]
; 其他配置...

# 告知 Odoo 使用代理以及前缀
proxy_mode = True

# 固定基础 URL（带前缀）
web.base.url = https://example.com/dtdashboardbg
web.base.url.freeze = True
```

解释：

- `proxy_mode = True` 让 Odoo 信任 `X-Forwarded-*` 头，从而正确反映真实 URL/协议。
- `web.base.url` 设置 Odoo 生成链接的基地址；必须包含完整前缀。
- `web.base.url.freeze = True` 可防止管理员在 UI 中访问其他 URL 时被 Odoo 自动改写。

修改完后重启服务：

```bash
sudo systemctl restart odoo
sudo systemctl reload nginx
```

---

## 3. 额外提示

1. **资产缓存**：使用子路径后，若浏览器缓存旧的无前缀资产，可能需要清空浏览器缓存或在 Odoo 后台点击“清空资产缓存”。
2. **多站点/多数据库**：如果同一 Odoo 要同时提供多个前缀访问，建议使用多个 Nginx `location` + 多个 `web.base.url`（或专用模块）来区分。
3. **HTTPS**：生产环境最好把 `server` 改成 `listen 443 ssl;` 并配置证书，然后在 80 端口做跳转。
4. **负载均衡**：若有多个 Odoo workers，确保 upstream 指向各个实例；对长轮询尽量启用 `ip_hash` 保持会话一致性。

这样配置后，访问 `https://example.com/dtdashboardbg/` 即可完整加载 Odoo，且系统内生成的所有链接、静态资源、跳转都会自动带上 `/dtdashboardbg` 前缀。