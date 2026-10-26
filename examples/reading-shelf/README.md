---
title: 离线阅读架
subtitle: 三份合成文档的离线阅读与下载示例
edition: 2026.10 · 例子
author: Faye & Cove
github: https://github.com/IndelibleVivi
credits: made by Faye & Cove
---

# 离线阅读架

**2026.10 · 例子**  
三份合成文档的离线阅读与下载示例 · Faye & Cove

这个小例子把三份独立文档放进一小架资料：不加后端、不依赖网络，也能在本地阅读[欢迎](materials/welcome.md)、[笔记](materials/notes.md)与[检查清单](materials/checklist.md)。它演示公开内容如何打包成离线可读、可下载的形式。

它也在[个人基础设施实践手册](../../guides/handbook.md#content)里被引用，沿同一份材料继续解释权限、版本、任务与检索。示例使用合成输入，不含真实账户或私人原始资料。

## 取得完整例子

在[阅读站的例子页](https://indeliblevivi.github.io/cf-fieldbook/examples/reading-shelf/README.html)可以直接打开资料架成品，也可以下载保留目录结构的完整 ZIP。解压后先进入 `cf-fieldbook-reading-shelf/` 根目录，再执行下列命令；clone 仓库的读者仍从仓库根目录执行。逐个保存源文件不会自动建立 `materials/`，需要运行和修改时请取完整包。

## 本地查看

直接打开 `index.html` 可以阅读与跳转到三份原件；在 `file://` 下，浏览器可能忽略链接的 `download` 属性而打开 Markdown 文本。需要触发文件下载时，用本地静态服务器托管这个目录：

```sh
python3 -m http.server 8768 --bind 127.0.0.1 --directory examples/reading-shelf
```

打开 `http://127.0.0.1:8768/`。三份文档都在页面内，“下载／打开原文”链接指向对应 Markdown 原件；经本地 HTTP 提供时可下载，关闭 JavaScript 后仍可阅读和下载。结束查看时用 Ctrl+C 停止本地服务器，不产生云端资源。

`example.meta.json` 的 `check_command` 只确认页面与三份原件存在，不证明渲染、导航或下载成功。实际核对时，分别打开页面内的三份文档、点击目录，并把下载内容与 `materials/` 的原件比较；直接打开文件与本地 HTTP 的链接行为应分开观察。

## 修改并重建

先打开 `materials/notes.md`，将“旧引用可以保留版本身份”改成“旧引用也要注明资料日期”，保存后**暂不 build**。刷新资料架：页面仍是旧句，下载／打开原文已是新句。两份内容来自不同文件，保存原件不会自动更新已生成的 HTML。

比较过这两句后，从仓库或解压根目录生成页面：

```sh
python3 examples/reading-shelf/build.py
```

刷新页面，再下载原文，确认两处都包含新句。这里观察的是原件与生成文件的差异，不是浏览器缓存或线上部署。`index.html` 是生成文件，不另行编辑正文。对于材料没有提供的论文结论，应回答材料不足；当前页面没有自动问答或模型调用。

## 沿同一份材料继续

| 下一步 | 手册中的设计 | 当前例子的边界 |
|---|---|---|
| 临时给朋友看 | [保持本机服务并用 Tunnel 分享](../../use-cases/temporary-sharing.md) | 仍依赖本机服务和连接器运行 |
| 电脑关闭后继续公开阅读 | [同一资料架的静态发布](../../use-cases/publish-reading-shelf.md) | 先离线准备四个公开文件；实际部署、更新与删除单独执行 |
| 保留版本与原件 | R2 或已有存储保存原件，D1 或已有数据库保存当前指针 | 当前只有本地文件，没有数据库 |
| 只给指定读者看 | Access、会话与读取资格分开检查 | 当前是公开静态资料，没有登录或授权服务 |
| 更新后继续处理 | 任务保存阶段与结果，先准备派生内容再切当前版本 | 当前由编辑者手动运行 build，没有队列或恢复执行器 |
| 找回原文与撤下内容 | 检索结果带版本和来源，撤下先停止读取再清索引 | 当前可直接读三份原文，没有云端索引或远端缓存清理 |

这些扩展见手册相应章节与[匿名资料站实践](../../practice/private-reader.md)。它们需要另行实施与验收，静态页面的成功不证明权限、云端检索或恢复机制已经运行。

静态发布的可选工具单独放在本目录的 `package.json` 与真实 `package-lock.json`：Node.js 22+，Wrangler 固定为 `4.152.0`。只读和重建仍只需 Python，不需要安装 npm 依赖。`prepare_publish.py` 从三份原件重新生成页面，并仅复制 `index.html` 与三份原件到 `public/`；遇到目录中的额外文件或符号链接会停止，要求先检查。它不登录、不上传，也不清理未知文件。完整安装、预览、远端操作和停用步骤见上述静态发布指南。

GitHub · [https://github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*
