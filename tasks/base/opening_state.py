"""Recognition shared by mirror opening transitions."""
from module.automation import auto


def find_grace_anchor():
    # Keep the strict threshold while tolerating Retina rasterization.
    return auto.find_element(
        'mirror/road_to_mir/dreaming_star/coins_assets.png',
        model='retina', threshold=0.90,
    )
