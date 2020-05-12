import numpy as np
import math


def floor_to(x, to_value=0.05):
    """
    Floors x to the nearest multiple of to_value

    For example, floor_to(1.27, 0.05) evaluates to 1.25

    Args:
        x (float): Value to floor
        to_value (float): Value to floor to a multiple of

    Returns:
        (float)
    """
    return x // to_value * to_value


def ceil_to(x, to_value=0.05):
    """
    Ceils x to the nearest multiple of to_value

    For example, floor_to(1.27, 0.05) evaluates to 1.30

    Args:
        x (float): Value to floor
        to_value (float): Value to ceil to a multiple of

    Returns:
        (float)
    """
    return math.ceil(x / to_value) * to_value


def get_rounded_z_range_including_mid(values, zmid=0.0, round_to=10.0):
    """
    Returns zmin and zmax that are the min/max of values floord/ceiled to the nearest round_to

    If zmid<zmin (or zmid>zmax), zmin=zmid (zmax=zmid) so that zmid is always included.

    Args:
        values (iterable): Values to use to compute zmin/zmax.  Nan values will be ignored.
        zmid (float): Value to be included in the zmin to zmax range
        round_to (float): Multiple to which zmin/zmax value will be rounded to.  Ex, if zmin=-12 and round_to=5, zmin
                          will be rounded (floored) to -15.

    Returns:
        zmin, zmax
    """
    zmin = float(min(zmid, np.nanmin(values)))
    zmax = float(max(zmid, np.nanmax(values)))

    if round_to:
        zmin = floor_to(zmin, round_to)
        zmax = ceil_to(zmax, round_to)

    return zmin, zmax


def make_centered_rg_colorscale(v_min, v_max, v_mid=0, reverse=False):
    """
    Returns a Plotly Heatmap colorscale list from min(values) (red) to max(values) (green), with white at v_mid

    Optionally can be reversed (green to red)
    """
    v_range = v_max - v_min

    if v_range == 0:
        # No range - doesn't really matter...
        z_mid = 0.5
    else:
        # Locate v_mid in normalized coordinates
        z_mid = (v_mid - v_min) / v_range

    z = [
        0.0,
        z_mid / 2,
        z_mid,
        (1 - z_mid) / 2 + z_mid,
        1.0
    ]

    colors = ["rgb(255,0,0)", "rgb(240,0,0)", "rgb(255,255,255)", "rgb(0,240,0)", "rgb(0,255,0)"]
    if reverse:
        colors.reverse()
    return list(zip(z, colors))
