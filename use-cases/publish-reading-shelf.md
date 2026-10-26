---
title: 把同一个资料架公开发布
subtitle: 从本地阅读到关机后仍可访问、更新与停用
source_cutoff: 2026-10-26
---

# 把同一个资料架公开发布

你已经在本地读完[三份文档的小资料架](../examples/reading-shelf/README.md)，现在希望朋友在你的电脑关闭后仍能阅读这份**公开资料**。继续使用同一份原件和生成脚本，将检查过的静态文件交给 Workers Static Assets；这条路线不需要数据库、身份系统、搜索或模型，也不需要另写 Worker handler。[S172] [S173]

## 电脑关机后，文件由谁提供

本地 HTTP 从你的电脑取文件；[Tunnel 临时分享](temporary-sharing.md)仍将请求送回本地 HTTP；静态发布则提供上传的文件。因此停止本机服务会影响前两条路线，已发布的静态页面可以继续读取。本节先完成本地准备，再明确列出需要你选择目标和另外执行的远端步骤。

## 1 / 准备一个只含公开文件的目录

clone 仓库或下载完整 ZIP，进入仓库根目录或 `cf-fieldbook-reading-shelf/` 解压根目录。Python 3.11+ 即可准备：

```bash
python3 examples/reading-shelf/prepare_publish.py
```

脚本从 `materials/` 重新生成 `index.html`，再将下面四个文件复制到 `examples/reading-shelf/public/`，保留相对路径：

```text
public/
  index.html
  materials/
    welcome.md
    notes.md
    checklist.md
```

只有这四个文件可以进入 assets。源代码、维护说明、lockfile、凭据与私人配置都留在外面。脚本遇到符号链接或 `public/` 中的额外文件会停止，请先检查其来源和用途；它不会替你删除未知文件。原件是合成材料，改成自己的内容后仍须逐份确认可公开，并保留必要署名、许可和修改说明。

这里的 `public/` 是可重建的本地产物，不提交到仓库；`wrangler.publish.jsonc` 是你的实际发布配置，也不提交。静态目录的边界由脚本和下述 `assets.directory` 共同确定，不能把它改为仓库根目录。[S173]

## 2 / 安装固定工具并本地预览

普通阅读和 Python 重建不需要 npm。只有继续这条发布路线时，才安装本目录的可选开发工具：Node.js 22+、npm 和 lockfile 中固定的 Wrangler `4.152.0`。这个版本在编辑时实际安装并检查，未声称兼容未来版本。

从上述根目录进入例子目录，之后的 npm／Wrangler 命令都在这里执行：

```bash
cd examples/reading-shelf
npm ci
npx --no-install wrangler --version
cp wrangler.publish.example.jsonc wrangler.publish.jsonc
```

`npm ci` 下载依赖，需要软件源网络；不会创建云资源。`cp` 用于首次创建配置；已有 `wrangler.publish.jsonc` 时保留它，直接打开检查。模板使用合成名称 `reading-shelf-example`，将 `name` 改成你确认未被其他项目使用的独立名称。纯静态配置只指向 `./public`，省略 `main` 与 `ASSETS` binding；没有自定义域名、数据库或秘密信息。[S173]

```bash
WRANGLER_SEND_METRICS=false npx --no-install wrangler dev --local --ip 127.0.0.1 --port 8787 --config wrangler.publish.jsonc
```

保持终端运行，在浏览器打开 `http://127.0.0.1:8787/`，依次阅读三份文档、切换目录、下载原文。关闭 JavaScript 后也应可阅读。另开终端检查不存在的 `/missing` 返回 404，而不是被首页兜底；`/build.py` 和 `/README.md` 也不应返回源文件。最后 Ctrl+C 停止预览。[S174]

需要检查配置和本地打包时，另行执行下面的 dry run；它不上传，不替代实际部署验收：

```bash
WRANGLER_SEND_METRICS=false npx --no-install wrangler deploy --dry-run --config wrangler.publish.jsonc
```

## 3 / 核对公开目标，再单独部署

以下开始涉及账号和远端写入。先在自己的私人记录中确定：目标账户、独立 Worker 名称、允许公开的四个文件、使用的套餐与预算、实验结束时间，以及由谁停用。不要把既有生产 Worker 的名字填入模板，也不要把此文当作对任何账户的部署授权。

账号登录和只读身份查询由读者在自己的环境执行，确认显示的是预期账户：

```bash
npx --no-install wrangler login
npx --no-install wrangler whoami
```

多账户时，在本地配置明确选择本次目标 `account_id`，再核对一次；真实账户标识不复制进公共例子。确认后，**下面这一条会上传静态文件并创建或更新所选 Worker**：[S174]

```bash
npx --no-install wrangler deploy --config wrangler.publish.jsonc
```

记录 CLI 返回的实际公开 URL 和部署结果，不从模板名称猜地址。模板启用 `workers.dev`，关闭额外 preview URLs；本文不为你创建自定义域名或 CI 接线。

停止本机 Python 服务和 Wrangler 预览，再从另一台设备或独立客户端打开实际 URL：三份文档都应可读、目录可跳转，下载的原文应与本次 `public/materials/` 一致；未知路径和源代码路径应维持预期拒绝结果。保存实际观察及失败，不要只记一行“部署成功”。若账号权限、套餐或工具报错，先检查具体失败，未经核对不要改名重建另一个资源。

## 4 / 修改后重新生成、预览和发布

仍在例子目录时，编辑 `materials/notes.md` 中的一句。暂不生成，比较原件和 `public/index.html`：公开目录仍是上一份副本。随后执行：

```bash
python3 prepare_publish.py
WRANGLER_SEND_METRICS=false npx --no-install wrangler dev --local --ip 127.0.0.1 --port 8787 --config wrangler.publish.jsonc
```

本地核对页面和下载都含新句，停止预览后，再执行第 3 节的同一部署命令，更新**同一个名称、同一个账户**。从独立客户端重新读取公开页面和原文，确认两处均已更新。页面仍旧时，依次检查本地是否生成、目标是否相同、部署输出和客户端缓存；只刷新本地文件不会改变云端副本。

## 5 / 停用与清理这次独立资源

结束前先保存需要的原件、公开 URL、Worker 名称和部署结果。确认本次资源只有静态文件，没有接入其他项目；删除前再次核对目标账号与本地配置。**下面这一条会删除配置指定的 Worker**，请阅读 CLI 提示后确认，不加入自动确认参数：[S174]

```bash
npx --no-install wrangler delete --config wrangler.publish.jsonc
```

删除请求返回后，仍要从独立客户端重新访问原 URL，并在账户内读回资源状态。记录实际状态码／错误和资源是否仍列出；删除命令成功不等于所有缓存、副本或账单立即消失。分享给读者的本地下载副本也不会被远程收回。本地 `public/` 可以保留供以后重建，不需要删除原件或源仓库。

## 本节检查到哪里

本节核对的是 2026-10-26 官方静态配置与 CLI 文档、实际安装的 Wrangler 版本、本地发布目录和预览。仓库默认检查不登录、不部署、不上传，也不执行上面的删除。一次真实云实验还须完成第 3–5 节的部署、关闭本机后的读取、原文下载、更新与停用读回；该结果仅适用于那次账号和资源。

资料需要限制读者时，再进入[Access 与替代入口](../guides/handbook.md#access)及[私有资料站实践](../practice/private-reader.md)。通用 Worker 开发与部署条件由[实施参考](../reference/implementation.md)保存；这里不把公开资料架扩为带权限的完整应用。

<!-- SOURCES -->

[S172]: https://developers.cloudflare.com/workers/static-assets/get-started/ "Workers Static Assets 静态站起步"
[S173]: https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/ "纯静态 assets.directory 与可省略的脚本和 binding"
[S174]: https://developers.cloudflare.com/workers/wrangler/commands/workers/ "Wrangler 预览、部署与删除"
