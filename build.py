"""Сборка ChatList.exe и установщика Inno Setup с версией из version.py."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import version

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
EXE_NAME = "ChatList.exe"
INSTALLER_ISS = ROOT / "installer.iss"
ISCC_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
)


def version_tuple() -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.__version__.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def installer_name() -> str:
    return f"ChatList-{version.__version__}-setup.exe"


def write_version_info(path: Path) -> None:
    major, minor, patch, build = version_tuple()
    path.write_text(
        f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'ChatList'),
          StringStruct('FileDescription', 'ChatList'),
          StringStruct('FileVersion', '{version.__version__}'),
          StringStruct('InternalName', 'ChatList'),
          StringStruct('OriginalFilename', '{EXE_NAME}'),
          StringStruct('ProductName', 'ChatList'),
          StringStruct('ProductVersion', '{version.__version__}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )


def find_iscc() -> Path:
    for candidate in ISCC_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Inno Setup не найден. Установите Inno Setup 6: https://jrsoftware.org/isinfo.php"
    )


def run_pyinstaller() -> None:
    version_info = ROOT / "version_info.txt"
    write_version_info(version_info)
    separator = ";" if sys.platform == "win32" else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "ChatList",
        "--icon",
        "app.ico",
        "--version-file",
        str(version_info),
        "--add-data",
        f"app.ico{separator}.",
        str(ROOT / "main.py"),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)


def run_inno_setup() -> Path:
    exe_path = DIST / EXE_NAME
    if not exe_path.exists():
        raise FileNotFoundError(f"Не найден файл сборки: {exe_path}")
    if not INSTALLER_ISS.exists():
        raise FileNotFoundError(f"Не найден скрипт установщика: {INSTALLER_ISS}")

    iscc = find_iscc()
    cmd = [
        str(iscc),
        f"/DAppVersion={version.__version__}",
        str(INSTALLER_ISS),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)

    installer_path = DIST / installer_name()
    if not installer_path.exists():
        raise FileNotFoundError(f"Установщик не создан: {installer_path}")
    return installer_path


def prepare_release_artifacts(installer_path: Path) -> None:
    latest_installer = DIST / "ChatList-setup.exe"
    latest_installer.write_bytes(installer_path.read_bytes())

    checksums_path = DIST / "SHA256SUMS.txt"
    lines: list[str] = []
    for path in (DIST / EXE_NAME, installer_path, latest_installer):
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    checksums_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    run_pyinstaller()
    installer_path = run_inno_setup()
    prepare_release_artifacts(installer_path)
    print(f"Сборка завершена: ChatList v{version.__version__}")
    print(f"  EXE: {DIST / EXE_NAME}")
    print(f"  Установщик: {installer_path}")
    print(f"  Latest alias: {DIST / 'ChatList-setup.exe'}")
    print(f"  Checksums: {DIST / 'SHA256SUMS.txt'}")


if __name__ == "__main__":
    main()
