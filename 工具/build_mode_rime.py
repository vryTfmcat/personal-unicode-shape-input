"""Build mode-specific Rime dictionaries without legacy cold-archive dependencies."""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path
from mode_codebooks import (PROJECT, BOOK_PATH, base_data, effective_data, validate_codebooks,
                            candidate_index, write)
from mode_icons import MODE_LABELS, schema_id, write_icons

OUTPUT = PROJECT / "原型" / "rime" / "三模式"
LAYERS = ("block", "shape", "personal", "chinese", "extended")

SCHEMA = '''schema:
  schema_id: personal_unicode_modes
  name: Unicode 三模式
  version: "1.0"
  dependencies: [unicode_block, unicode_shape, unicode_personal, unicode_chinese, unicode_extended]
  icon: icons/unicode_mode_1.ico
  ascii_icon: icons/unicode_mode_ascii.ico
# Mode feedback belongs in the status icon; suppress transient option popups.
show_notifications: false
switches:
  - name: ascii_mode
    reset: 0
    states: [Unicode, 英文]
  - name: unicode_block
    states: [区块关, 区块开]
  - name: unicode_shape
    states: [全形关, 全形开]
  - name: unicode_personal
    states: [收藏关, 收藏开]
  - name: unicode_chinese
    states: [中文关, 中文开]
  - name: unicode_extended
    states: [扩展关, 扩展开]
engine:
  processors:
    - lua_processor@*unicode_modes*processor
    - ascii_composer
    - recognizer
    - key_binder
    - speller
    - punctuator
    - selector
    - navigator
    - express_editor
  segmentors: [ascii_segmentor, matcher, abc_segmentor, punct_segmentor, fallback_segmentor]
  translators: [lua_translator@*unicode_modes*translator]
speller:
  alphabet: abcdefghijklmnopqrstuvwxyz
  max_code_length: 4
  auto_select: false
ascii_composer:
  switch_key:
    Shift_L: noop
    Shift_R: commit_text
key_binder:
  bindings:
    - {when: always, accept: Control+Shift+1, toggle: unicode_block}
    - {when: always, accept: Control+Shift+2, toggle: unicode_shape}
    - {when: always, accept: Control+Shift+3, toggle: unicode_personal}
    - {when: always, accept: Control+Shift+4, toggle: unicode_chinese}
    - {when: always, accept: Control+Shift+5, toggle: unicode_extended}
    - {when: paging, accept: minus, send: Page_Up}
    - {when: has_menu, accept: equal, send: Page_Down}
menu:
  page_size: 5
'''


def build(book: dict | None = None, output: Path = OUTPUT) -> dict:
    base = base_data()
    book = book if book is not None else json.loads(BOOK_PATH.read_text(encoding="utf-8"))
    validate_codebooks(book, base)
    data = effective_data(base, book)
    index = candidate_index(data)
    output.mkdir(parents=True, exist_ok=True)
    counts = {}
    active = ["unicode_" + layer for layer in LAYERS if index[layer]]
    schema = SCHEMA.replace("dependencies: [unicode_block, unicode_shape, unicode_personal, unicode_chinese, unicode_extended]", "dependencies: [" + ", ".join(active) + "]")
    for layer in LAYERS:
        name = "unicode_" + layer
        rows = []
        for code, chars in index[layer].items():
            for i, c in enumerate(chars):
                rows.append(f"{c['char']}\t{code}\t{1000000-i}")
        header = f"---\nname: {name}\nversion: '1.0'\nsort: original\nuse_preset_vocabulary: false\ncolumns: [text, code, weight]\n...\n"
        (output / f"{name}.dict.yaml").write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
        (output / f"{name}.schema.yaml").write_text(
            f"schema:\n  schema_id: {name}\n  name: Unicode {layer} 数据\n  version: '1.0'\nengine:\n  translators: [table_translator]\ntranslator:\n  dictionary: {name}\n", encoding="utf-8")
        schema += f"\n{name}:\n  available: {'true' if rows else 'false'}\n"
        if layer=='shape':
            schema += f"  min_code_length: {1 if data.get('shapeReviewProfile') else 2}\n"
            if data.get('shapeReviewProfile'):schema += f"  review_id: {data['shapeReviewProfile']['experimentId']}\n"
        if rows:
            schema += f"  dictionary: {name}\n  enable_sentence: false\n  enable_completion: false\n  enable_user_dict: false\n  enable_charset_filter: false\n"
        counts[layer] = len(rows)
    # Display variants share all dictionaries, Lua components and independent options.
    # Weasel 0.17.4 reloads status icons only when the schema ID changes.
    variants = [schema_id(mask) for mask in range(8) if mask != 1]
    main_schema = schema.replace("dependencies: [" + ", ".join(active) + "]",
                                 "dependencies: [" + ", ".join(active + variants) + "]")
    (output / "personal_unicode_modes.schema.yaml").write_text(main_schema, encoding="utf-8")
    for mask in range(8):
        if mask == 1: continue
        variant = schema.replace("schema_id: personal_unicode_modes\n", f"schema_id: {schema_id(mask)}\n", 1)
        variant = variant.replace("name: Unicode 三模式\n", f"name: Unicode · {MODE_LABELS[mask]}\n", 1)
        variant = variant.replace("icons/unicode_mode_1.ico", f"icons/unicode_mode_{mask}.ico")
        (output / f"{schema_id(mask)}.schema.yaml").write_text(variant, encoding="utf-8")
    write_icons(output / "icons")
    (output / "lua").mkdir(exist_ok=True)
    shutil.copy2(PROJECT / "原型" / "rime" / "lua" / "unicode_modes.lua", output / "lua" / "unicode_modes.lua")
    return {"counts": counts, "output": str(output), "schema": "personal_unicode_modes",'shapeReviewProfile':data.get('shapeReviewProfile')}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    write()
    print(json.dumps(build(output=args.output), ensure_ascii=False))
