# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['Anki-TTS-Edge.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('translations.json', '.'), # 包含翻译文件
        ('icon.ico', '.')          # 包含图标文件
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Anki-TTS-Edge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # <--- 修改为 False，禁用 UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # <--- 隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico', # <--- 设置程序图标
)
