"""Read-only bundled assets; user configuration and logs stay outside the app."""
import os
import sys
from pathlib import Path


def prepare_data_directory():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    data = Path(os.environ.get('AALC_DATA_DIR', Path.home() / 'Library/Application Support/AALC Mac'))
    data.mkdir(parents=True, exist_ok=True)
    for name in ('assets', 'i18n'):
        link = data / name
        target = root / name
        if link.is_symlink():
            if link.resolve() != target.resolve():
                temporary = data / (name + '.new')
                temporary.unlink(missing_ok=True)
                temporary.symlink_to(target, target_is_directory=True)
                temporary.replace(link)
        elif not link.exists():
            link.symlink_to(target, target_is_directory=True)
        else:
            raise RuntimeError(f'资源路径不是应用管理的链接，请选择空的数据目录: {link}')
    os.chdir(data)
    return data


def apply_mac_configuration(cfg):
    # These are invariants of this platform, not preferences or migrated Windows state.
    for key, value in {
        'simulator': False, 'background_click': False,
        'set_win_size': 1080, 'set_windows': False, 'set_reduce_miscontact': False,
        'memory_protection': False, 'check_update': False, 'autostart': False,
        'after_completion_actions': [], 'after_completion_power_action': 'none',
        'image_resource_sync': False,
    }.items():
        cfg.unsaved_set_value(key, value)
