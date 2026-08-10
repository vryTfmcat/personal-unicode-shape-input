# Git 版本管理

本项目使用项目目录内的独立 Git 仓库，不把 Obsidian 全库、冷归档或个人资料纳入版本历史。目前只保存在本机，没有配置远程仓库。

## 分支与版本

- `main`：可使用、通过完整测试的稳定版本。
- `codex/*`：开发分支；完成并验证后再合并回 `main`。
- `v0.1.0`：全量 Unicode 码表与原始键位编辑器基线。
- `v0.2.0`：中文联想图谱、分层 Rime 与直接保存功能。

## 跟踪与忽略

Git 跟踪项目说明、理论、实体页、工具、测试、Rime schema、官方 Unicode 17 源数据、精选 2000 和主联想图谱。全量编码 TSV、编辑器初始数据、生成词典、构建报告、图谱快照与 Rime 备份可由脚本恢复，因此不进入历史。

提交钩子会阻止生成物、备份、疑似密钥和超过 10 MB 的普通文件。若钩子没有自动启用，在项目目录执行 `git config core.hooksPath .githooks`。

## 日常命令

```powershell
python 工具/project_tasks.py build
python 工具/project_tasks.py test
python 工具/project_tasks.py check
```

- `build`：补齐全字符表，重建全码表、编辑器数据和三个 Rime 词典。
- `test`：运行 Python、JavaScript、本地保存和 Rime 回归测试。
- `check`：先构建再测试，适合合并或打标签前使用。
- `python 工具/project_tasks.py sync-rime --apply`：备份并同步日常两个 Rime 方案，不重新部署小狼毫。

从项目目录外的干净检出重建时，用 `--vault-root "Obsidian 库根目录"` 指向原始只读冷归档；Unicode 全字符表、码表、编辑器数据和词典仍在当前检出中重新生成，不会写入冷归档。

查看历史与修改使用 `git status`、`git log --oneline --decorate` 和 `git diff`。主联想图谱还可以从编辑器的“图谱快照”恢复。
