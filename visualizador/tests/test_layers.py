import numpy as np

from core.layers import RAPID_LAYER, depth_levels, layer_indices
from core.parser import Move
from core.toolpath import Toolpath


def make_path():
    # cortes em z=0 (início) e z=-5; um rápido de volta ao topo
    return Toolpath([
        Move((0, 0, 0), (10, 0, 0), is_cut=True, feed=600.0),
        Move((10, 0, 0), (10, 0, -5), is_cut=True, feed=600.0),
        Move((10, 0, -5), (0, 0, -5), is_cut=True, feed=600.0),
        Move((0, 0, -5), (0, 0, 0), is_cut=False, feed=0.0),
    ])


def test_depth_levels_are_sorted_and_unique():
    levels = depth_levels(make_path())
    assert levels.tolist() == [-5.0, 0.0]


def test_layer_indices_map_each_move_and_mark_rapids():
    path = make_path()
    indices = layer_indices(path, depth_levels(path))
    assert indices.tolist() == [1, 0, 0, RAPID_LAYER]


def test_no_cuts_means_no_levels():
    path = Toolpath([Move((0, 0, 0), (5, 0, 0), is_cut=False, feed=0.0)])
    assert depth_levels(path).size == 0
    assert np.all(layer_indices(path, depth_levels(path)) == RAPID_LAYER)