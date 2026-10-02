# Build with: python -m PyInstaller --noconfirm macos.spec
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from pathlib import Path
root=Path(SPECPATH)
a=Analysis([str(root/'main.py')],pathex=[str(root)],binaries=[],
    datas=[(str(root/'assets'),'assets'),(str(root/'i18n'),'i18n'),(str(root/'LICENSE'),'.')]
          +collect_data_files('rapidocr')+collect_data_files('qfluentwidgets'),
    hiddenimports=['pynput.keyboard._darwin','pynput.mouse._darwin','PIL.ImageQt','AppKit','Quartz','ApplicationServices']+collect_submodules('rapidocr'),
    excludes=['tkinter','PyQt5','PyQt6','PySide2','pytest','module.automation.input_handlers.simulator'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='AALC Mac',console=False,target_arch='arm64',codesign_identity=None)
coll=COLLECT(exe,a.binaries,a.datas,name='AALC Mac')
app=BUNDLE(coll,name='AALC Mac.app',icon=str(root/'assets/logo/macos.icns'),
    bundle_identifier='org.aalc.community.macos',
    info_plist={'CFBundleShortVersionString':'1.0.9','CFBundleVersion':'14','LSMinimumSystemVersion':'14.0',
    'NSHighResolutionCapable':True,'NSAppleEventsUsageDescription':'用于控制 CrossOver 中的游戏窗口。',
    'NSScreenCaptureUsageDescription':'识别边狱公司游戏画面以执行你选择的任务。'})
