# Personal Unicode Shape-Phonetic Input

## Android 初步版本 0.2.4

触屏 Unicode 编辑器现可配合同文 Trime 使用，包含区块／全形／收藏、自由拼排、手机键位配置、草稿与发布管理。

安装包、同文部署包与重建输入见 [android-v0.2.4 发布页](https://github.com/vryTfmcat/personal-unicode-shape-input/releases/tag/android-v0.2.4)；[安装和源码构建说明](原型/安卓app/GitHub发布.md)。这是已完成本轮手机验收的初步版本，完整改码和编码格位等功能仍待后续开发。


A private Rime/Weasel input-method research project for assigning memorable
two-letter associations and visual shape codes to Unicode characters.

## What is included

- Python builders and regression tests for Unicode 17 data;
- a dependency-free local keymap and association-graph editor;
- Rime schemas and reproducible dictionary generators;
- small reviewed samples, project theory, and Unicode source metadata.

Large generated tables, editor payloads, Rime dictionaries, local backups,
and release archives are intentionally excluded from Git. They can be rebuilt
from the tracked tools and source data.

## Verify the project

From the repository root:

```powershell
python 工具/project_tasks.py test
```

To rebuild generated data and then run the full test suite:

```powershell
python 工具/project_tasks.py check --vault-root "PATH_TO_OBSIDIAN_VAULT"
```

The optional vault path is used only for the explicitly allowlisted legacy
source folders described in `来源/来源范围与综述.md`.

## Local editor

On Windows, run:

```text
原型/键位编辑器/启动键位编辑器.cmd
```

The service binds to `127.0.0.1` and keeps association-graph snapshots local.

## Privacy and licensing

This repository contains a personal semantic association graph and is intended
to remain private while the model and data boundaries are still evolving.
No open-source license has been granted at this stage.


## 三模式与形状审查工具

键位编辑器支持字块、全形、个人码本的独立查询和候选合并，工具目录保存规则审计、形状试验、Rime发布与相应测试。实体事实、个人码本、字体、生成词典、运行报告和备份不随本次源码更新提交。

全形审查索引是本机生成输入。需要启用时，按 `数据/三模式/全形核对版.example.json` 建立被忽略的 `全形核对版.json`，填写工程内索引路径与SHA-256；未配置时不启用此审查覆盖。不要把生成目录的整批报告纳入源码仓库。

基础验证：`node 工具/test_modes_core.cjs`、`node 工具/test_modes_reviewed_paths.cjs`、`python 工具/test_mode_codebooks.py`、`python 工具/test_shape_rule_audit.py`、`python 工具/test_shape_lab.py`。全量码表及本机字体相关验证需要已有Unicode输入表和生成的基础载荷。
