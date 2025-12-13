可以在 `location /dtdashboard` 里用 **rewrite** 把前缀 `/dtdashboard` 替换成 `/dashboardapi`，然后再 `proxy_pass` 到 8069。常见写法如下（保留原来的子路径和查询参数）：

```nginx
server {
    listen 80;
    server_name your.domain.com;

    # /dtdashboard 及其子路径都映射到后端的 /dashboardapi...
    location ^~ /dtdashboard/ {
        # 把 /dtdashboard/xxx -> /dashboardapi/xxx
        rewrite ^/dtdashboard/(.*)$ /dashboardapi/$1 break;

        proxy_pass http://127.0.0.1:8069;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 精确匹配 /dtdashboard（不带尾部斜杠）也要处理
    location = /dtdashboard {
        # /dtdashboard -> /dashboardapi
        rewrite ^ /dashboardapi break;

        proxy_pass http://127.0.0.1:8069;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 效果
- `GET /dtdashboard` → 转发到后端 `http://127.0.0.1:8069/dashboardapi`
- `GET /dtdashboard/a/b?x=1` → 转发到后端 `http://127.0.0.1:8069/dashboardapi/a/b?x=1`

### 检查与生效
```bash
nginx -t
nginx -s reload
```

如果你的后端是 WebSocket / SSE 或需要更大的上传体积、超时时间等，也可以再补充对应的 `proxy_http_version`、`Upgrade` 头、`proxy_read_timeout` 等配置。你后端 8069 是什么服务（例如 Odoo/Node/Java）？我可以按场景把反代细节一起补齐。