# Health Worker：本地示例

只处理 `/health` 的 GET / HEAD。无 binding、秘密信息、数据库或模型调用。

从仓库根目录运行：

```bash
node --test examples/health-worker/worker.test.mjs
```

测试仅调用 handler，不连接 Cloudflare。

实际使用时先在自己的项目中安装并固定部署工具版本；将 `wrangler.example.json` 复制成该工具读取的配置，选择自己的测试路由。本模板关闭默认开发和预览入口，且没有任何真实路由。不要把它当成“复制后自动公开”的模板。

本包没有执行过 `wrangler deploy`，没有验证账户、资源、TLS 或费用。相关步骤见手册第 4 章。
