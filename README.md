# Personal Unicode Shape-Phonetic Input

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

