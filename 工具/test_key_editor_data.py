#!/usr/bin/env python3
"""Validate the key editor's generated initial state."""

from build_key_editor_data import COMMON, build


def main() -> None:
    data = build()
    characters = data["characters"]
    by_char = {item["char"]: item for item in characters}
    assert data["version"] == 3
    assert len(characters) == 159345
    assert len(data["pages"]) == 381
    assert sum(item["pageId"] == "bo" for item in characters) == 91
    assert len(data["commonOrder"]) == 10
    for character, code in COMMON:
        assert by_char[character]["code"] == code
        assert by_char[character]["favorite"] is True
    assert by_char["ଉ"]["pageId"] == "bo"
    assert by_char["ଉ"]["code"] == "boki"
    assert by_char["Պ"]["pageId"] == "as"
    assert by_char["⦿"]["pageId"] == "dd"
    assert by_char["𒁔"]["pageId"] == "mv"
    assert by_char["ஆ"]["pageId"] == "pi"
    assert any(page["id"] == "kr" and "Kirat Rai" in page["block"] for page in data["pages"])
    print("键位编辑器初始数据校验通过。")


if __name__ == "__main__":
    main()
