# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for KAYO Desktop Application.
Build with: pyinstaller kayo.spec
"""

import os
import sys

block_cipher = None

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['desktop.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=[
        # Include app templates and static files
        ('app/templates', 'app/templates'),
        ('app/static', 'app/static'),
        # Include instance folder for database
        ('instance', 'instance'),
        # Include migrations if needed
        ('migrations', 'migrations'),
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'flask_migrate',
        'flask_wtf',
        'flask_mail',
        'flask_cors',
        'wtforms',
        'werkzeug',
        'jinja2',
        'sqlalchemy',
        'sqlalchemy.orm',
        'email_validator',
        'requests',
        'openpyxl',
        'pandas',
        'reportlab',
        'qrcode',
        'PIL',
        'jwt',
        'dateutil',
        'psutil',
        'webbrowser',
        # App modules
        'app',
        'app.models',
        'app.routes',
        'app.services',
        'app.utils',
        'config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='KAYO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Enable console to see errors
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/static/images/logo.ico' if os.path.exists('app/static/images/logo.ico') else None,
)

# Create folder distribution (more reliable across machines)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KAYO',
)
