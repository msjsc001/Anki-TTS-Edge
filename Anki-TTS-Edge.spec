# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Anki-TTS-PY\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('d:\\软件编写\\Anki-TTS-Edge\\Anki-TTS-PY\\assets', 'assets'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\icons\\.DS_Store', 'customtkinter\\assets\\icons'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\.DS_Store', 'customtkinter\\assets'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\fonts\\CustomTkinter_shapes_font.otf', 'customtkinter\\assets\\fonts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\fonts\\Roboto\\Roboto-Medium.ttf', 'customtkinter\\assets\\fonts\\Roboto'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\themes\\dark-blue.json', 'customtkinter\\assets\\themes'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\fonts\\Roboto\\Roboto-Regular.ttf', 'customtkinter\\assets\\fonts\\Roboto'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\themes\\green.json', 'customtkinter\\assets\\themes'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\icons\\CustomTkinter_icon_Windows.ico', 'customtkinter\\assets\\icons'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\customtkinter\\assets\\themes\\blue.json', 'customtkinter\\assets\\themes'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\communicate.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\data_classes.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\__main__.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\typing.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\version.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\__init__.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\submaker.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\util.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\drm.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\srt_composer.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\constants.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\exceptions.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\py.typed', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts\\voices.py', 'edge_tts'), ('C:\\Users\\lulu\\AppData\\Roaming\\Python\\Python313\\site-packages\\edge_tts-7.2.3.dist-info', 'edge_tts-7.2.3.dist-info')],
    hiddenimports=['PIL', 'PIL._tkinter_finder', 'customtkinter', 'engineio.async_drivers.threading', 'pystray', 'pystray._win32', 'edge_tts', 'edge_tts.__main__', 'edge_tts.communicate', 'edge_tts.constants', 'edge_tts.data_classes', 'edge_tts.drm', 'edge_tts.exceptions', 'edge_tts.srt_composer', 'edge_tts.submaker', 'edge_tts.typing', 'edge_tts.util', 'edge_tts.version', 'edge_tts.voices'],
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
    [],
    exclude_binaries=True,
    name='Anki-TTS-Edge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['d:\\软件编写\\Anki-TTS-Edge\\Anki-TTS-PY\\assets\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Anki-TTS-Edge',
)
