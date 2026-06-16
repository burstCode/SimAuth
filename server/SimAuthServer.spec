# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for SimAuthServer
# Run: pyinstaller SimAuthServer.spec  (from server/ directory)

block_cipher = None

a = Analysis(
    ['server_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[],           # config.json и simauth.db — рядом с exe, не внутри bundle
    hiddenimports=[
        # uvicorn динамически подгружает протоколы и event loop
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # SQLAlchemy диалект SQLite
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.sqlite.pysqlite',
        'sqlalchemy.sql.default_comparator',
        # asyncio backend для anyio
        'anyio._backends._asyncio',
        # pydantic
        'pydantic',
        'pydantic_core',
        # email (нужен starlette для responses)
        'email.mime.multipart',
        'email.mime.text',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'matplotlib', 'numpy', 'PIL', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SimAuthServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,       # сервер — консольное приложение, чтобы видеть логи
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SimAuthServer',
)
