"""Query a read-only copy of Weasel's deployed tables via its bundled Rime API."""

from __future__ import annotations

import argparse
import ctypes as ct
import hashlib
import shutil
import tempfile
from pathlib import Path

from deploy_rime_core import RimeTraits, utf8
from reviewed_shapes import REVIEWED_SHAPE_CODES


class Candidate(ct.Structure):
    _fields_ = [("text", ct.c_char_p), ("comment", ct.c_char_p), ("reserved", ct.c_void_p)]


class Iterator(ct.Structure):
    _fields_ = [("ptr", ct.c_void_p), ("index", ct.c_int), ("candidate", Candidate)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weasel-root", type=Path, required=True)
    parser.add_argument("--user-data-dir", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rime-verify-") as temp:
        root = Path(temp)
        staging = root / "build"
        staging.mkdir()
        files = list((args.user_data_dir / "build").glob("personal_unicode_symbols.*"))
        files += [args.user_data_dir / "build" / "personal_unicode.schema.yaml",
                  args.user_data_dir / "build" / "default.yaml"]
        for source in files:
            target = staging / source.name
            shutil.copy2(source, target)
            assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()
        dll = ct.WinDLL(str((args.weasel_root / "rime.dll").resolve()))
        for name, inputs, output in (
            ("RimeSetup", [ct.POINTER(RimeTraits)], None),
            ("RimeInitialize", [ct.POINTER(RimeTraits)], None),
            ("RimeFinalize", [], None),
            ("RimeCreateSession", [], ct.c_size_t),
            ("RimeDestroySession", [ct.c_size_t], ct.c_int),
            ("RimeSelectSchema", [ct.c_size_t, ct.c_char_p], ct.c_int),
            ("RimeSetOption", [ct.c_size_t, ct.c_char_p, ct.c_int], None),
            ("RimeClearComposition", [ct.c_size_t], None),
            ("RimeSetInput", [ct.c_size_t, ct.c_char_p], ct.c_int),
            ("RimeCandidateListBegin", [ct.c_size_t, ct.POINTER(Iterator)], ct.c_int),
            ("RimeCandidateListNext", [ct.POINTER(Iterator)], ct.c_int),
            ("RimeCandidateListEnd", [ct.POINTER(Iterator)], None),
        ):
            function = getattr(dll, name)
            function.argtypes = inputs
            function.restype = output
        traits = RimeTraits()
        traits.data_size = ct.sizeof(RimeTraits) - ct.sizeof(ct.c_int)
        traits.shared_data_dir = utf8(args.weasel_root / "data")
        traits.user_data_dir = utf8(root)
        traits.staging_dir = utf8(staging)
        traits.app_name = b"rime.codex_verify"
        traits.min_log_level = 2
        traits.log_dir = b""
        dll.RimeSetup(ct.byref(traits))
        dll.RimeInitialize(ct.byref(traits))
        session = dll.RimeCreateSession()
        try:
            assert session and dll.RimeSelectSchema(session, b"personal_unicode")
            dll.RimeSetOption(session, b"ascii_mode", 0)
            results = {}
            for code in sorted(set(REVIEWED_SHAPE_CODES.values())):
                dll.RimeClearComposition(session)
                assert dll.RimeSetInput(session, code.encode("ascii"))
                iterator = Iterator()
                candidates = []
                if dll.RimeCandidateListBegin(session, ct.byref(iterator)):
                    try:
                        while dll.RimeCandidateListNext(ct.byref(iterator)):
                            candidates.append(iterator.candidate.text.decode("utf-8"))
                    finally:
                        dll.RimeCandidateListEnd(ct.byref(iterator))
                results[code] = candidates
            for char, code in REVIEWED_SHAPE_CODES.items():
                assert char in results[code], (char, code, results[code])
            for code in ("sncx", "sncg", "snoi", "gsoe", "gssi", "gssf"):
                print(code, " ".join(results[code]), f"({len(results[code])} candidates)")
            print(f"Verified {len(REVIEWED_SHAPE_CODES)} approved characters in deployed Weasel tables.")
        finally:
            dll.RimeDestroySession(session)
            dll.RimeFinalize()


if __name__ == "__main__":
    main()
