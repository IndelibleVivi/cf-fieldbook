# 私有状态页：把门禁和健康分开检查

想在手机上查看自己的服务状态，又不希望把内部服务名称、故障时间线和管理入口公开。一条合适的路线是保留原有状态页应用，由 Cloudflare Tunnel 提供入口，再用 Access 限制谁能进入。

作者在 2026-08-09 使用 Uptime Kuma 建立过这样的私有状态页。状态页与管理入口各有明确 hostname，使用专用 Tunnel，两个入口都先经过 Access。Kuma 的管理登录与 2FA 保留在里面。通过 Access 以后能到达状态页，并不自动获得管理权限。

## Tunnel 接入口，原服务器继续运行应用

```text
浏览器 → Cloudflare Access → Cloudflare Tunnel
       → 原服务器上的 cloudflared → Uptime Kuma

管理操作继续经过 Kuma 自己的登录与权限
```

`cloudflared` 主动连接 Cloudflare，再把指定 hostname 的请求送到[源站](../docs/glossary.md#origin--源站)。Tunnel 为已有服务改变访问方式，状态页、监控任务和数据仍由原服务器运行。主机停止或应用退出，Tunnel 不能替它执行检查或保存新的观察。[Cloudflare Tunnel routing](https://developers.cloudflare.com/tunnel/concepts/routing/)与[连接配置说明](https://developers.cloudflare.com/tunnel/configuration/)。

在这份组合里，Kuma 与 cloudflared 通过私有容器网络通信，应用没有为了入口开放一个公网监听。Access 规则先准备好，再连接正式 hostname。依赖 Access 的源站还需要拒绝绕过入口的请求；官方提供 cloudflared 的 Access token 验证或源站自行验证两种接法。[保护自托管应用官方说明](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)。应用自身的管理密码则保留它自己的作用：只允许具备管理资格的人改变监控配置。

## 门口有回应，里面仍可能不工作

实际运行后，最容易混淆的是状态页监控到底在观察什么。匿名外部请求收到 Access 登录重定向，说明入口到门禁这段工作；它还没读取受保护的应用，无法证明源站正在提供正确结果。

同样，Tunnel 在控制台显示 Healthy，只确认 cloudflared 与 Cloudflare 连接，并不检查 route 指向的服务或本地源站。这个区别也在 [Cloudflare Tunnel 故障排查文档](https://developers.cloudflare.com/tunnel/troubleshooting/https-origins/)中明确说明。

所以这份实践把三类检查分开：

| 检查 | 能回答的问题 | 还缺哪一段 |
|---|---|---|
| 外部匿名请求 | 正式 hostname 是否到达预期门禁 | 登录后的页面与源站业务 |
| 源站本地检查 | 原应用进程和受检查的接口是否正常 | 外部 route、Access 与浏览器访问 |
| 已登录的真实浏览器 | 读者是否取得正确页面，管理登录是否可用 | 下一次故障和其他设备的状态 |

每条 monitor 的名称也要按它实际观察的对象来写。「入口要求登录」可以是一个预期结果；不能把它命名为「整个服务正常」。若用源站上的定时 probe 把结果推给 Kuma，就说明它从哪台环境观察，失败时保留无法访问的原因，不能将访问被拒一概记成目标应用宕机。

这份部署没有记录过需要重写 Tunnel 架构的事故；留下的主要教训是验收容易过早结束：看到连接器健康、容器运行、登录页出现，就宣布系统完成。修正的方法是把登录后的实际页面作为独立一步，并只给已经启用的监控下结论。准备在以后添加的 monitor 不进入当前覆盖范围。

## 历史验收和后来的清点

| 日期 | 实际检查 | 能说到哪里 |
|---|---|---|
| 2026-08-09 | Kuma 与连接器运行，两个正式入口受 Access 保护，匿名请求跳转登录；真实 Chrome 登录后显示状态页，六条初始监控已启用 | 当日状态页入口与代表性阅读路径通过；不代表所有被监控服务都得到业务验收 |
| 2026-08-29 | 只读 API 清点仍返回相同六条 active monitor 定义 | 证明配置仍在；没有重跑各项健康检查，也没有重新验收浏览器 |

本文在 2026-10-03 根据这些历史观察重构，并查阅公开文档，没有连接原主机或登录状态页。8 月的 active 与 Healthy 不应当作今天仍然在线的判断。

## 怎样在自己的环境验证

先为自己的测试 hostname 选一个固定、无敏感内容的样本页面。把「能访问状态」和「能修改监控」分别定义好，再检查：

1. 从源站所在环境请求应用，确认得到预期页面或健康 JSON，记录应用自己的登录要求。
2. 检查 Tunnel route 的 service 地址是 cloudflared 实际能到达的源站地址。容器里的 `localhost` 指该容器，不能自动代表另一个应用容器。
3. 从外部未登录环境访问状态与管理 hostname，二者都按设计进入 Access；没有把源站公网端口留下作替代入口。
4. 用获准身份登录，确认状态页是真实应用页面；需要管理时继续完成内层应用登录。只出现密码框还不算 owner 能管理。
5. 在隔离测试服务上停止应用，比较 Tunnel 状态、外部响应与本地 probe。再恢复应用，确认实际结果恢复；不要为制造故障而停止真实业务。
6. 导出一份只含合成名称的检查记录，分别写明入口、源站和浏览器的时间与结果，别用一个绿色圆点替它们作答。

私人页面也应只展示读者需要知道的服务信息。页面可见性、管理权限和每个被监控接口的权限应分别配置；给 monitor 一个万能管理 token 会把原本简单的状态观察变成更大的权限面。

如果目标是所有人都能访问的公开状态页，本篇的整站 Access 会改变它的使用方式，需要重新安排公开摘要与私人管理入口。如果应用需要在主机故障时继续运行，Tunnel 也不会解决这个需求。[手册：已有服务器与 Tunnel](../guides/handbook.md#已有服务器tunnel-只改变访问方式)帮助选择入口；[健康检查离线例子](../examples/health-worker/README.md)可以先观察 HTTP handler 的返回边界，它不检查本篇的 Tunnel 或 Kuma。
