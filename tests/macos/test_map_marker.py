from pathlib import Path
import numpy as np
from PIL import Image
from utils.image_utils import ImageUtils

FIXTURES=Path(__file__).parent/'fixtures'
def load(name):return np.array(Image.open(FIXTURES/name).convert('L'))

def test_retina_marker_passes_without_lowering_global_threshold():
    scene=load('map_marker_retina.png');template=load('map_marker_template.png')
    assert ImageUtils.match_template(scene,template,None)[1] < .8
    assert ImageUtils.match_template(scene,template,None,model='retina')[1] >= .9

def test_battle_is_not_a_map():
    assert ImageUtils.match_template(load('battle_not_map.png'),load('map_marker_template.png'),None,model='retina')[1] < .9
