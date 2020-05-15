import numpy as np
import pandas as pd
import datetime
import math
import plotly.graph_objects as go


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


def date_shift(ds, scale_factor=0.8):
    """
    Shifts/Scales the dates in a date Series

    Adjusts dates in Series such that that months are shifted ~1/2 month back and dates in each month are scaled such
    that each month has scale_factor "width" (eg for Jan, Jan 1 and Jan 31 are only scale_factor months apart, eg ~15
    days if scale_factor = 5.

    Original use for this was to take monthly data and temporally shift it to center around the start of each month
    (eg: data from Apr 1 to Apr 30 is shifted to center around April 1) and then tighten each month (so April data
    might occur between Mar 20 and April 10).  This was done to align data in a line graph with bars in a bargraph for
    the same months
    """
    # Shift +1 second so that MonthBegin of the very first date in a month isn't pushed to the previous month
    month_begin = ds + datetime.timedelta(1) + pd.offsets.MonthBegin(-1)
    month_end = ds + pd.offsets.MonthEnd(0)

    # Make a start date that is shifted half of a scaled month to the left of the beginning of this month
    reference_start = -((month_end - month_begin) * scale_factor / 2) + month_begin
    # Compute the date relative to a month start
    relative_date = (ds - month_begin) * scale_factor
    return relative_date + reference_start


def invisible_figure():
    transparent_figure_background = {
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
    }
    fig = go.Figure()
    fig.update_layout(
        **transparent_figure_background,
    )
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    return fig
