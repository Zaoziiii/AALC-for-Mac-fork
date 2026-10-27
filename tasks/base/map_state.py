"""Shared map-state detection for every transition back to the mirror map."""
from module.automation import auto


def is_mirror_map(*, take_screenshot=False):
    # 实测地图上图例得分 0.89–0.92，其他画面最高 0.80；0.90 会漏判 0.89 的地图，
    # 导致事件结束回到地图后仍困在事件循环里，不去点节点的 Enter。
    return bool(auto.find_element(
        'mirror/road_in_mir/legend_assets.png',
        model='retina', threshold=0.85, take_screenshot=take_screenshot,
    ))
