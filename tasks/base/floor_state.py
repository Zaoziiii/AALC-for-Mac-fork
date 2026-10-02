"""Read floor indicators appropriate to the current dungeon page."""
import re
import cv2
import numpy as np


def current_floor_from_theme_pack(image):
    if image.mode != 'RGB' or image.size != (1920, 1080):
        return None
    from module.ocr import ocr
    # The heading is above the cards and below the toolbar. Exclude the
    # difficulty label and numbers elsewhere on the selection page.
    result = ocr.run(image.crop((600, 130, 1320, 215)))
    if not result.txts or not result.scores or min(result.scores) < 0.85:
        return None
    title = re.sub(r'\s+', '', ''.join(result.txts)).upper()
    # This narrow font is read as FL00R on the actual floor-three screen.
    # Accept O/0 only in the fixed word; never substitute the floor digit.
    match = re.fullmatch(r'SELECTFL[O0]{2}R([1-5])THEMEPACK', title)
    return int(match[1]) if match else None


def current_floor_from_panel(image):
    if image.mode != 'RGB' or image.size != (1920, 1080):
        return None
    hsv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2HSV)
    active = []
    # Interior patches exclude borders, labels and CLEAR text. Capture is
    # normalized to 1920x1080 before recognition, independently of window size.
    for floor, x in enumerate((748, 854, 960, 1066, 1172), start=1):
        patch = hsv[398:418, x-10:x+10]
        gold = ((patch[:, :, 0] >= 15) & (patch[:, :, 0] <= 40)
                & (patch[:, :, 1] >= 120) & (patch[:, :, 2] >= 150))
        if np.mean(gold) >= 0.70:
            active.append(floor)
    return active[0] if len(active) == 1 else None
