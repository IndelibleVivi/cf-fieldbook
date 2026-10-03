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

## 本地查看

直接打开 `index.html`，或用任意静态服务器托管这个目录：

```sh
python3 -m http.server 8768 --bind 127.0.0.1 --directory examples/reading-shelf
```

打开 `http://127.0.0.1:8768/`。三份文档都在页面内，下载链接指向对应 Markdown 原件；关闭 JavaScript 后仍可阅读和下载。结束查看时用 Ctrl+C 停止本地服务器，不产生云端资源。

## 修改并重建

编辑 `materials/` 中的原件，再生成页面：

```sh
python3 examples/reading-shelf/build.py
```

`index.html` 是生成文件，不另行编辑正文。先问“哪份文档讲更新与撤下”，回到第二份原文；改写其中一句、重建，再核对页面与下载。对于材料没有提供的论文结论，应回答材料不足；当前页面没有自动问答或模型调用。

## 沿同一份材料继续

| 下一步 | 手册中的设计 | 当前例子的边界 |
|---|---|---|
| 保留版本与原件 | R2 或已有存储保存原件，D1 或已有数据库保存当前指针 | 当前只有本地文件，没有数据库 |
| 只给指定读者看 | Access、会话与读取资格分开检查 | 当前是公开静态资料，没有登录或授权服务 |
| 更新后继续处理 | 任务保存阶段与结果，先准备派生内容再切当前版本 | 当前由编辑者手动运行 build，没有队列或恢复执行器 |
| 找回原文与撤下内容 | 检索结果带版本和来源，撤下先停止读取再清索引 | 当前可直接读三份原文，没有云端索引或远端缓存清理 |

这些扩展见手册相应章节与[匿名资料站实践](../../practice/private-reader.md)。它们需要另行实施与验收，静态页面的成功不证明权限、云端检索或恢复机制已经运行。

GitHub · [https://github.com/IndelibleVivi](https://github.com/IndelibleVivi)  
*made by Faye & Cove*
