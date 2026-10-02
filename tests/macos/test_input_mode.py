from unittest.mock import patch

from module.automation import auto
from module.macos.window import window
from module.macos.bootstrap import apply_mac_configuration


def test_background_choice_selects_driver_without_forcing_foreground():
    from module.config import cfg
    from module.automation.input_handlers.background import BackgroundInput
    with patch.object(cfg, 'get_value', return_value='background'):
        auto.init_input()
    try:
        assert isinstance(auto.input_handler, BackgroundInput)
        assert window.background is True
        assert cfg.background_click is True
    finally:
        with patch.object(cfg, 'get_value', return_value='foreground'):
            auto.init_input()


def test_platform_configuration_preserves_selected_mode():
    class Config:
        def __init__(self):
            self.values = {'win_input_type': 'background'}

        def unsaved_set_value(self, key, value):
            self.values[key] = value

    config = Config()
    apply_mac_configuration(config)
    assert config.values['win_input_type'] == 'background'
