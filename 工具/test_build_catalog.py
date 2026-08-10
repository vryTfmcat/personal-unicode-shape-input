#!/usr/bin/env python3
"""Focused regression tests for the catalog builder."""

from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent))
import build_catalog as catalog  # noqa: E402


def main() -> int:
    assert catalog.extract_symbol_sequences("⦿꜏ଉ.md") == ("⦿꜏ଉ",)
    assert catalog.extract_symbol_sequences("𓆟(13)") == ("𓆟",)
    assert catalog.extract_symbol_sequences("圆周率") == ()
    assert catalog.codepoints("𓆟") == ["U+1319F"]
    assert catalog.is_valid_input_code("jj")
    assert catalog.is_valid_input_code("boki")
    assert not catalog.is_valid_input_code("j")
    assert not catalog.is_valid_input_code("abcde")

    with tempfile.TemporaryDirectory() as temporary:
        page = Path(temporary) / "sample.md"
        page.write_text(
            "---\nid: u-1319f\ntype: character\ndisplay: \"𓆟\"\ncodepoints: [\"U+1319F\"]\ninput_code: abcd\nmnemonic: \"\"\nshape_tags: []\nstatus: active\nexport_to_rime: true\nsources:\n  - example.md\nnote: \"\"\n---\n",
            encoding="utf-8",
        )
        parsed = catalog.parse_frontmatter(page)
        assert parsed["id"] == "u-1319f"
        assert parsed["sources"] == ["example.md"]
    print("build_catalog tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
