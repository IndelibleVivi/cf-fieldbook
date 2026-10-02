# 许可与权利范围

CF Fieldbook 的项目原创部分由 Faye 按下列条款提供，作品署名为 **Faye & Cove**。作品来源：[github.com/IndelibleVivi/cf-fieldbook](https://github.com/IndelibleVivi/cf-fieldbook)。

本仓库采用分层许可，**不是可任意商用的 OSI 开源项目**。代码属于 source-available；正文与独立图形采用内容许可。下表按材料本身划分，而非把整个仓库都视为同一种作品。

| 材料与范围 | 适用条款 |
|---|---|
| `tools/`、`tests/`、`examples/` 中的原创 Python / JavaScript / MJS 程序；`styles/` 的 CSS / JavaScript；文档中可独立执行的原创代码片段 | [Sustainable Use License 1.0（SUL-1.0）](LICENSE) |
| 原创运行、构建与依赖配置：`.github/`、`.gitattributes`、`.gitignore`、`package*.json`、`requirements-*.txt`、`diagrams/mermaid.config.json`、`styles/fieldbook-tokens.json`、`examples/health-worker/wrangler.example.json` | [SUL-1.0](LICENSE)，仅就本项目有权许可的部分 |
| 原创正文与模板：根目录文档，`docs/`、`guides/`、`services/`、`use-cases/`、`comparisons/`、`reference/`、`reports/`、`editorial/`、`templates/`，以及例子和图示目录中的说明 | [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md)，可执行代码片段除外 |
| 原创独立图形及其绘图源：`assets/` 中的 SVG、`diagrams/src/` 的 Mermaid | [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md) |
| `catalog/`、`diagrams/index.json`、图示 manifest、例子元数据中的原创说明、选择与编排 | [CC BY-NC-SA 4.0](LICENSE-DOCUMENTATION.md)，限于本项目拥有的著作权或相关数据库权利；不对事实本身主张独占权 |
| `dist/` 及后续导出的 Markdown / HTML / PDF | 原创文字和图形沿用 CC BY-NC-SA 4.0；其中可分离的功能代码、脚本与样式沿用 SUL-1.0；第三方材料仍按其本来的权利边界处理 |

## 使用与修改

SUL-1.0 允许个人、非商业用途及内部业务用途的使用或修改；向他人分发或提供软件必须免费且用于非商业目的，并保留许可和必要通知。修改副本须醒目标明修改。以 [完整许可文本](LICENSE) 为准。

CC BY-NC-SA 4.0 允许在其条件下非商业分享与改编。分享时保留合理署名、许可链接并标明修改；分享改编作品时遵守相同许可要素或兼容许可要求。以 [内容许可说明与官方法律文本](LICENSE-DOCUMENTATION.md) 为准。

这些是原始许可证的摘要，不追加限制，也不替代法定例外。保留出处、资料截止日期与已有修改说明，有助于避免把历史判断误认为当前服务承诺。

## 第三方材料与依赖

Cloudflare、TypeSafe、OpenRouter、Vercel 等产品名、商标、官方文档和被引用资料仍属于相应权利人。来源链接和引述不表示本项目重新许可其完整文档、模型、服务或商标，也不表示官方认可。

通过 Python / npm 安装的依赖不以本项目许可证重新授权；安装包和依赖锁中的上游许可标识继续有效。本仓库不分发依赖包本体或独立字体文件。出版物可能包含排版所需的字体子集，字体权利不纳入项目的内容许可。

本次为首次公开时的明确授权，不修改历史成品的 bytes，也不重写早期 commit。早期本地许可状态不构成另一份已授予的公开许可证；任何第三方已有授权均不因本说明而被收回。
