import pytest

from spearmint.dashboard.utils import get_rounded_z_range_including_mid, make_centered_rg_colorscale


@pytest.mark.parametrize(
    "values,zmid,round_to,expected",
    (
            (
                    [-50, 20, 100],
                    0,
                    None,
                    (-50, 100),
            ),
            (
                    [50, 20, 100],
                    0,
                    None,
                    (0, 100),
            ),
            (
                    [-53, 20, 107],
                    0,
                    11,
                    (-55, 110),
            ),
            (
                    [53, 20, 107],
                    0,
                    11,
                    (0, 110),
            ),
            (
                    [-50, -20, -100],
                    0,
                    None,
                    (-100, 0),
            ),
            (
                    [-50, -20, 100],
                    101,
                    11,
                    (-55, 110),
            ),
    )
)
def test_get_rounded_z_range_including_mid(values, zmid, round_to, expected):
    actual = get_rounded_z_range_including_mid(values, zmid, round_to)

    assert list(expected) == pytest.approx(list(actual))


COLOR_PROGRESSION = ('rgb(255,0,0)', 'rgb(240,0,0)', 'rgb(255,255,255)', 'rgb(0,240,0)', 'rgb(0,255,0)')
COLOR_PROGRESSION_REVERSED = tuple(x for x in COLOR_PROGRESSION[::-1])

@pytest.mark.parametrize(
    "vmin,vmax,vmid,reverse,expected_values,expected_colors",
    (
            (
                    -5,
                    10,
                    0,
                    False,
                    [0.0, 1/6, 1/3, 2/3, 1.0],
                    COLOR_PROGRESSION
            ),
            (
                    -5,
                    10,
                    5,
                    False,
                    [0.0, 1/3, 2/3, 5/6, 1.0],
                    COLOR_PROGRESSION
            ),
            (
                    -5,
                    10,
                    0,
                    True,
                    [0.0, 1/6, 1/3, 2/3, 1.0],
                    COLOR_PROGRESSION_REVERSED
            ),
            (
                    0,
                    0,
                    0,
                    False,
                    [0.0, 0.25, 0.5, 0.75, 1.0],
                    COLOR_PROGRESSION
            ),
    ),
)
def test_make_colorscale(vmin, vmax, vmid, reverse, expected_values, expected_colors):
    actual = make_centered_rg_colorscale(vmin, vmax, vmid, reverse)
    # Transform [[v1, c1], [v2, c2], ...] into [[v1, v2 ...], [c1, c2 ...]]
    actual_values, actual_colors = zip(*actual)

    assert expected_values == pytest.approx(actual_values)
    assert expected_colors == actual_colors