# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parents[1]
a = Analysis(
    [str(root / 'notryn_cli.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'web'), 'web')],
    hiddenimports=[
        'desktop',
        'filemoves',
        'github_sync',
        'notryn_install',
        'notryn_license',
        'notryn_progress',
        'notryn_version',
        'removals',
        'server',
        'share',
        'store',
        'themes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='notryn',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='notryn',
)
