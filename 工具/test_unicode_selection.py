import csv
import hashlib
import json
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "数据" / "Unicode精选"
OUTPUT = ROOT / "输出"
UCD = ROOT / "UCD-17.0.0"


def read_tsv(name: str) -> list[dict[str, str]]:
    with (OUTPUT / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class UnicodeSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        broad_path = OUTPUT / "unicode-17-全量精选.tsv"
        if broad_path.is_file():
            cls.broad = read_tsv("unicode-17-全量精选.tsv")
        else:
            from build_unicode_selection import build_records, record_row
            records, _counts = build_records(UCD, set())
            cls.broad = [record_row(record) for record in records]
        cls.v1 = read_tsv("unicode-17-v1-2000.tsv")

    def test_expected_counts_and_unique_codepoints(self) -> None:
        self.assertEqual(len(self.broad), 159345)
        self.assertEqual(len(self.v1), 2000)
        self.assertEqual(len({row["codepoint"] for row in self.broad}), len(self.broad))
        self.assertEqual(len({row["codepoint"] for row in self.v1}), len(self.v1))

    def test_broad_catalog_has_only_graphic_categories(self) -> None:
        self.assertTrue(all(row["category"][0] in "LMNPS" for row in self.broad))
        marks = [row for row in self.broad if row["category"].startswith("M")]
        self.assertEqual(len(marks), 2280)
        self.assertTrue(all(row["requires_base"] == "true" for row in marks))
        self.assertTrue(all(row["display_sample"].startswith("◌") for row in marks))

    def test_v1_is_standalone_and_locally_displayable(self) -> None:
        self.assertTrue(all(row["standalone_safe"] == "true" for row in self.v1))
        self.assertTrue(all(row["requires_base"] == "false" for row in self.v1))
        self.assertTrue(all(row["windows_font_covered"] == "true" for row in self.v1))

    def test_all_confirmed_anchors_are_in_v1(self) -> None:
        anchors = {"¤", "𓆟", "ܜ", "ଉ", "Պ", "○", "◌", "⦿", "●", "𒁔", "ᗚ", "ஆ", "ᗣ", "༳"}
        self.assertTrue(anchors.issubset({row["char"] for row in self.v1}))

    def test_ucd_files_match_recorded_hashes(self) -> None:
        manifest = json.loads((UCD / "SHA256SUMS.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["unicode_version"], "17.0.0")
        for name, metadata in manifest["files"].items():
            digest = hashlib.sha256((UCD / name).read_bytes()).hexdigest()
            self.assertEqual(digest, metadata["sha256"], name)
            self.assertTrue(metadata["url"].startswith("https://www.unicode.org/"))


if __name__ == "__main__":
    unittest.main()
