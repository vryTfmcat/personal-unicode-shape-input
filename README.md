# Personal Unicode Shape-Phonetic Input

Local four-round shape-overview work uses the version and privacy boundaries in
[DEVELOPMENT.md](DEVELOPMENT.md). The current local combination is t/b v17,
structure counts v5, subject attachments v1 and bucket-order queries. It includes
uncommitted tools and private inputs that cannot be reconstructed from main alone.
The complete local restore checkpoint is `../archive/2026-10-25-双顺序版固化/`;
the public-source and older Android instructions below have their own scope.

## Android 初步版本 0.2.4

触屏 Unicode 编辑器现可配合同文 Trime 使用，包含区块／全形／收藏、自由拼排、手机键位配置、草稿与发布管理。

安装包、同文部署包与重建输入见 [android-v0.2.4 发布页](https://github.com/vryTfmcat/personal-unicode-shape-input/releases/tag/android-v0.2.4)；[安装和源码构建说明](原型/安卓app/GitHub发布.md)。这是已完成本轮手机验收的初步版本，完整改码和编码格位等功能仍待后续开发。


A Rime/Weasel and web-editor research project for assigning memorable
two-letter associations and visual shape codes to Unicode characters.

The local editor now uses three independent codebooks: block, coarse shape,
and personal aliases, with an optional pinned Flypy Chinese layer.
See [the current editor guide](原型/键位编辑器/使用说明.md).
Reviewed four-letter shape paths from batches 01/02/03/05/06 are now enabled. Two-letter families, three-letter prefixes and four-letter paths share exact character identity; trial batches remain excluded.

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
python 工具/project_tasks.py check
```

The current three-mode builder does not depend on legacy cold-archive links.

## Local editor

On Windows, run:

```text
原型/键位编辑器/启动键位编辑器.cmd
```

The service binds to `127.0.0.1:8765`, saves revisioned codebooks and graph
snapshots to project files, and publishes the new Weasel schema after isolated
native Rime verification. Python dependencies are NumPy, Pillow and PyYAML.

## Hosted collaborative editor

The earlier collaborative editor is available at:

<https://amd-fedor.tail73cba1.ts.net/unicode-editor/>

Its runtime collaboration data is stored on the server at
`/home/vrytfmcat/文档/unicode键位编辑器/`. The hosted version supports shared
key submissions, server-side persistence, optimistic version-conflict
protection, backups, and password-protected editing. Credentials are not kept
in this repository.

## Privacy and licensing

This repository contains a personal semantic association graph. The GitHub
repository remains private while the model and data boundaries are still
evolving. No open-source license has been granted at this stage.
