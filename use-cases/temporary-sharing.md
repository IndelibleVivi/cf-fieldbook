---
title: 临时给几个人看本地 demo
subtitle: Protected Quick Tunnel 与长期入口怎样选择
source_cutoff: 2026-10-03
---

# 临时给几个人看本地 demo

本机已有一个能打开的合成资料架，只想让两位朋友看今天的 UI。这里的目标是短暂分享，不承诺电脑关机后继续服务。长期可读的资料应另走静态发布或云端交付。[S109]

## 从本机页面到指定邮箱

沿用[小资料架](../examples/reading-shelf/README.md)的本地服务，从仓库或完整包的解压根目录运行：

```bash
python3 -m http.server 8768 --bind 127.0.0.1 --directory examples/reading-shelf
```

保持这个终端运行，确认 `http://127.0.0.1:8768` 打开预期页面，再另开一个终端运行含新参数的 `cloudflared`：

```bash
cloudflared tunnel --url http://127.0.0.1:8768 --allowed-mail 'alice@example.com,bob@example.com'
```

访问者输入获准邮箱，再填写邮件 PIN；无需 Cloudflare account。也可以重复该参数，或明确选择 `'*@example.com'` 域规则。示例邮箱都是占位符。[S109]

分享已有应用时，改用你刚确认能打开的实际本地地址。这里的 `8768` 专门承接资料架，其他应用的端口不必跟随修改。

普通 Quick Tunnel 没有 `--allowed-mail` 时，拿到 URL 的人仍可访问。它不会自动成为默认私有入口，也不替应用建立角色、数据库权限或对下载副本的控制。[S110]

## 让分享有可以检查的结尾

读者另外执行这条网络路线时，检查三个结果：获准邮箱能通过 PIN；另一个邮箱无法进入；停止 `cloudflared` 后入口不再可用。原程序或电脑停止，Tunnel 也无法替它继续服务。[S109]

Quick Tunnel 用于测试与开发，没有 SLA，当前最多 200 个并发请求，也不支持 SSE。需要长期 hostname、SSE 或稳定运行时，采用正式 Tunnel 与相应 Access / 应用权限；只发布公开静态资料时可以直接采用静态托管。[S110]

## 从一次试看过渡到长期服务

先决定程序在哪里持续运行，再决定谁可用：公开的三份资料可以继续走[同一资料架的静态发布](publish-reading-shelf.md)，让朋友在电脑关闭后仍能读取上传的文件；仅把本机 HTTP 包装成公网 URL 做不到这一点。继续读[请求路线](../guides/handbook.md#routes)、[Access 与替代入口](../guides/handbook.md#access)和[私有阅读站实践](../practice/private-reader.md)。

本仓库没有运行 Tunnel、发送 PIN 或检验真实邮箱；上述检查属于另行授权的云端实验，本文证据是官方资料查阅。

<!-- SOURCES -->

[S109]: https://developers.cloudflare.com/changelog/post/2026-10-02-protected-quick-tunnels/ "Protected Quick Tunnels 发布"
[S110]: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ "Quick Tunnel 邮箱限制与开发边界"
