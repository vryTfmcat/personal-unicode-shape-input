#!/usr/bin/env python3
"""Deploy a Rime workspace through the C API bundled with Weasel.

This is a fallback for cases where WeaselDeployer.exe stalls before it reaches
the workspace build. Stop WeaselServer before running it, then start the server
again after the process exits.
"""

from __future__ import annotations

import argparse
import ctypes
from pathlib import Path


class RimeTraits(ctypes.Structure):
    _fields_ = [
        ("data_size", ctypes.c_int),
        ("shared_data_dir", ctypes.c_char_p),
        ("user_data_dir", ctypes.c_char_p),
        ("distribution_name", ctypes.c_char_p),
        ("distribution_code_name", ctypes.c_char_p),
        ("distribution_version", ctypes.c_char_p),
        ("app_name", ctypes.c_char_p),
        ("modules", ctypes.POINTER(ctypes.c_char_p)),
        ("min_log_level", ctypes.c_int),
        ("log_dir", ctypes.c_char_p),
        ("prebuilt_data_dir", ctypes.c_char_p),
        ("staging_dir", ctypes.c_char_p),
    ]


def utf8(path: Path) -> bytes:
    return str(path.resolve()).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rime-dll", type=Path, required=True)
    parser.add_argument("--shared-data-dir", type=Path, required=True)
    parser.add_argument("--user-data-dir", type=Path, required=True)
    args = parser.parse_args()

    user_dir = args.user_data_dir.resolve()
    staging_dir = user_dir / "build"
    modules = (ctypes.c_char_p * 4)(b"core", b"dict", b"levers", None)
    keepalive = {
        "shared": utf8(args.shared_data_dir),
        "user": utf8(user_dir),
        "distribution_name": "小狼毫".encode("utf-8"),
        "distribution_code": b"Weasel",
        "distribution_version": b"0.17.4",
        "app_name": b"rime.weasel.codex_deploy",
        "log_dir": b"",
        "prebuilt": utf8(args.shared_data_dir),
        "staging": utf8(staging_dir),
    }
    traits = RimeTraits()
    traits.data_size = ctypes.sizeof(RimeTraits) - ctypes.sizeof(ctypes.c_int)
    traits.shared_data_dir = keepalive["shared"]
    traits.user_data_dir = keepalive["user"]
    traits.distribution_name = keepalive["distribution_name"]
    traits.distribution_code_name = keepalive["distribution_code"]
    traits.distribution_version = keepalive["distribution_version"]
    traits.app_name = keepalive["app_name"]
    traits.modules = ctypes.cast(modules, ctypes.POINTER(ctypes.c_char_p))
    traits.min_log_level = 0
    traits.log_dir = keepalive["log_dir"]
    traits.prebuilt_data_dir = keepalive["prebuilt"]
    traits.staging_dir = keepalive["staging"]

    rime = ctypes.WinDLL(str(args.rime_dll.resolve()))
    rime.RimeSetup.argtypes = [ctypes.POINTER(RimeTraits)]
    rime.RimeSetup.restype = None
    rime.RimeDeployerInitialize.argtypes = [ctypes.POINTER(RimeTraits)]
    rime.RimeDeployerInitialize.restype = None
    rime.RimeDeployWorkspace.argtypes = []
    rime.RimeDeployWorkspace.restype = ctypes.c_int
    rime.RimeJoinMaintenanceThread.argtypes = []
    rime.RimeJoinMaintenanceThread.restype = None
    rime.RimeFinalize.argtypes = []
    rime.RimeFinalize.restype = None

    rime.RimeSetup(ctypes.byref(traits))
    try:
        rime.RimeDeployerInitialize(ctypes.byref(traits))
        deployed = bool(rime.RimeDeployWorkspace())
        rime.RimeJoinMaintenanceThread()
    finally:
        rime.RimeFinalize()
    if not deployed:
        raise SystemExit("RimeDeployWorkspace returned false")
    print("Rime workspace deployment completed through rime.dll")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
