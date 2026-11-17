# Git 版本管理

> 当前唯一开发入口及隐私边界以 [DEVELOPMENT.md](DEVELOPMENT.md) 为准。Git基线、网页研究版本、人工确认版本和实际部署版本分别记录，不以main分支或一次测试代表全部实验已验收。当前只分类和审阅白名单，没有自动暂存、提交或推送。

本项目使用项目目录内的独立 Git 仓库，不把 Obsidian 全库、冷归档或个人资料纳入版本历史。当前 GitHub 远程仓库为 `https://github.com/vryTfmcat/personal-unicode-shape-input.git`，保持公开（用户于 2026-10-22 确认）。安卓初版源码在 `codex/android-0.2.4` 分支，发布版本为 `android-v0.2.4`，下载与重建见 [[原型/安卓app/GitHub发布]]。

## 分支与版本

- `main`：已合并源码的基线；不包含全部本地研究成果，也不保证当前所有实验均通过验收。
- `codex/*`：开发分支；完成并验证后再合并回 `main`。
- `v0.1.0`：全量 Unicode 码表与原始键位编辑器基线。
- `v0.2.0`：中文联想图谱、分层 Rime 与直接保存功能。

## 跟踪与忽略

源码白名单可以包含经审阅的工具、测试、Rime schema和必要公开输入。实体、个人码表、人工审议与联想图谱不默认进入公开仓库。历史索引仍含部分实体，不表示允许继续提交；不得运行git add .。生成数据是否可忽略，须先验证其输入、工具和恢复依赖均已保存，不能仅因扩展名是JSON或被称为生成物就排除。

提交钩子会阻止生成物、备份、疑似密钥和超过 10 MB 的普通文件。若钩子没有自动启用，在项目目录执行 `git config core.hooksPath .githooks`。

## 日常命令

当前组合局部核验使用库外`工具/verify_shape_release.py --output-dir 新验收目录`，按runtime.version选择生成器；v9单批复现使用`工具/apply_d_stroke_k_batch_20261026.py`默认只比对。v5/v4工具只复现对应冻结批。恢复用原双顺序完整包＋当前已封存归并增量，先验SHA，禁止回叠旧人工审议。下方完整build/check不作为局部核验默认步骤；公开源码须逐文件白名单审阅，禁止git add .。


```powershell
python 工具/project_tasks.py build
python 工具/project_tasks.py test
python 工具/project_tasks.py check
```

- `build`：补齐全字符表，重建全码表、编辑器数据和三个 Rime 词典。
- `test`：运行 Python、JavaScript、本地保存和 Rime 回归测试。
- `check`：先构建再测试，适合合并或打标签前使用。
- `python 工具/project_tasks.py sync-rime --apply`：备份并同步日常两个 Rime 方案，不重新部署小狼毫。

干净检出缺少私人运行输入时先按恢复清单恢复，不能只靠main重建本地现行总览。使用其它生成命令前先按README核实参数；`--vault-root`指向实际Vault根目录，不能把冷归档路径当作Vault根目录；冷归档始终只读。本轮未运行完整码表重建。

查看历史与修改使用 `git status`、`git log --oneline --decorate` 和 `git diff`。主联想图谱还可以从编辑器的“图谱快照”恢复。

AMD Fedora 网站的运行时协作数据位于 `/home/vrytfmcat/文档/unicode键位编辑器/`，不直接作为 Git 工作区。线上稳定变更应先导出或同步回项目源数据，通过测试后再提交；服务器口令、运行时备份和临时状态不得提交到仓库。
