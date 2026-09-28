"""Сборка ChatList.exe и установщика с версией из version.py."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import version

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
EXE_NAME = "ChatList.exe"


def version_tuple() -> tuple[int, int, int, int]:
    parts = [int(part) for part in version.__version__.split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def installer_name() -> str:
    return f"ChatList-{version.__version__}-setup.zip"


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


def create_installer() -> Path:
    exe_path = DIST / EXE_NAME
    if not exe_path.exists():
        raise FileNotFoundError(f"Не найден файл сборки: {exe_path}")

    installer_path = DIST / installer_name()
    if installer_path.exists():
        installer_path.unlink()

    with zipfile.ZipFile(installer_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(exe_path, EXE_NAME)
        env_example = ROOT / ".env.example"
        if env_example.exists():
            archive.write(env_example, ".env.example")
        readme = ROOT / "README.md"
        if readme.exists():
            archive.write(readme, "README.md")

    return installer_path


def main() -> None:
    run_pyinstaller()
    installer_path = create_installer()
    print(f"Сборка завершена: ChatList v{version.__version__}")
    print(f"  EXE: {DIST / EXE_NAME}")
    print(f"  Установщик: {installer_path}")


if __name__ == "__main__":
    main()
