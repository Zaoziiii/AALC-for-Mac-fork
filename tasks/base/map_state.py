"""Shared map-state detection for every transition back to the mirror map."""
from module.automation import auto


def is_mirror_map(*, take_screenshot=False):
    return bool(auto.find_element(
        'mirror/road_in_mir/legend_assets.png',
        model='retina', threshold=0.90, take_screenshot=take_screenshot,
    ))
