import argparse
import pandas as pd

import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL

from spearmint.dashboard.budget_sidebar_list_elements import make_sidebar_ul
from spearmint.dashboard.budget_sidebar_list_elements import register_sidebar_list_click, get_checked_sidebar_children
from spearmint.dashboard.utils import get_rounded_z_range_including_mid, make_centered_rg_colorscale, date_shift, \
    invisible_figure, round_date_to_month_begin
from spearmint.data.db_session import global_init
from spearmint.data_structures.budget import BudgetCollection
from spearmint.services.budget import get_overall_budget_collection
from spearmint.services.transaction import get_transactions, get_unique_transaction_categories_as_string

MOVING_AVERAGE_SLIDER_TICKS = [1, 2, 3, 6, 12]
ANNOTATION_ARGS = dict(
    xref='x1',
    yref='y1',
    showarrow=False,
    font=dict(color='black'),
)

CATEGORY_COLUMN = "category"
DATETIME_COLUMN = "datetime"
AMOUNT_COLUMN = "amount"
BUDGET_NAME_COLUMN = "budget_name"
BUDGET_VALUE_COLUMN = "budget"
DELTA_COLUMN = "delta"
SUBTOTAL_BUDGET_NAME = "Subtotal"

WORKING_DATA_ID = "working-data"

SLIDER_TITLE_WIDTHS = {'md': 2, 'sm': 12}
SLIDER_WIDTHS = {'md': 10, 'sm': 12}

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

BUDGET_COLLECTION = get_overall_budget_collection()


# Define a right margin for the heatmap and barchart.  This is to achieve a (implicitly) shared x-axis without having to
# put them in the same figure.
SHARED_FIGURE_MARGIN = {
    'l': 150,
    'r': 100,
    't': 0,
    'b': 0,
}


FIGURE_BACKGROUND = {
    'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
}


# Define x-axis padding to be shared across heatmap and barchart
X_AXIS_PAD = pd.Timedelta(15, unit='D')


def aggregate_to_budget_deltas(df, datetime_column=DATETIME_COLUMN, category_column=CATEGORY_COLUMN,
                               amount_column=AMOUNT_COLUMN, budget_name_column=BUDGET_NAME_COLUMN,
                               delta_column=DELTA_COLUMN,
                               budget_value_column=BUDGET_VALUE_COLUMN, budget=None, moving_average_window=None,
                               start_date=None, end_date=None, work_on_copy=True):
    if work_on_copy:
        df = df.copy()

    start_date, end_date, date_range = _parse_dates(datetime_column, df, end_date, start_date, moving_average_window)

    # If we have a budget collection with aggregated budgets (multiple categories -> single budget), aggregate
    if isinstance(budget, BudgetCollection):
        df[budget_name_column] = budget.aggregate_categories_to_budget(df[category_column], depth='child')
        budget_names = [b.name for b in budget.get_budgets()]
    else:
        raise NotImplementedError("This is not done.  I think we need to catch if dict here and do something.  "
                                  "Not sure about int")
        df[budget_name_column] = df[category_column]
        budget_names = pd.unique(df[budget_name_column])

    # Reject anything that doesn't have a mapped budget_name (because we don't care about it!)
    df = df.dropna(subset=[budget_name_column])

    # If we have no data here, we haven't selected any categories to plot.  Escape
    if len(df) == 0:
        # no data!
        return df

        # Rearrange df of individual transactions into format needed
    df_sums = df[[budget_name_column, datetime_column, amount_column]] \
        .groupby([budget_name_column, pd.Grouper(key=datetime_column, freq='MS')]).sum()

    # Make a regular index with all category/month combinations having values.
    # Fill anything missing with 0
    new_index = pd.MultiIndex.from_product((budget_names, date_range), names=[budget_name_column, datetime_column])
    df_sums = df_sums.reindex(new_index, fill_value=0)

    # Rearrange budget into format needed
    # TODO: Handle various possible budget input types more rigorously
    if isinstance(budget, (float, int)):
        # All budget values are equal and set to the number budget
        # Build budget such that each month/category has the same budget value, and it covers all values in df_sums
        df_budget = pd.DataFrame({budget_value_column: [budget] * len(df_sums.index)}, index=df_sums.index)
        # Alternatively, could make this a {category: _, budget: _} dataframe (no date) and cast to all months using
        # same code as below
    elif isinstance(budget, BudgetCollection):
        name_amount = [(b.name, b.amount) for b in budget.get_budgets()]
        name, amount = list(zip(*name_amount))

        # Indexed by budget_name
        df_budget = pd.DataFrame({budget_value_column: amount}, index=name)

        # Reindexed to broadcast across all dates
        # level sets the index to match to.  Others are broadcast across
        df_budget = df_budget.reindex(df_sums.index, level=budget_name_column)

    # NOT TESTED(?)
    # elif isinstance(budget, dict):
    #     # Build the {cat: budget} dict into a dataframe with index of cat, column of budget
    #     budget = pd.DataFrame(budget).T
    #     budget.index.name = category_column
    #     budget.rename(columns={0: "budget"}, inplace=True)
    # elif isinstance(budget, pd.Series):
    #     # Handle case where we have a series
    #     budget = pd.DataFrame(budget)

    # If we wanted to make everything into the full multi-index before merge, we can reshape it.  But, the merge below
    # can handle merging a 1d index into a multiindex
    # if len(budget.index) == 1:
    #     # Assume we're a budget that has index=category, values=budget values for categories
    #     # We're missing a time component.  One option is to expand this dataframe to have the time
    #     # component, then add as an index.  Can do this by:
    #     # Add column that has a list-like of all dates we want for a given budget category
    #     budget[datetime_column] = [date_range] * len(budget)
    #     # Explode the datetime column, which takes the elements from the list and generates new rows for each
    #     budget = budget.explode(datetime_column)
    #     # Reform the index to be category/datetime (could also reindex on above index and fill, but we will do that
    #     # after)
    #     budget = budget.reset_index().set_index(df_sums.index.names).reindex(df_sums.index, fill_value=0)

    df_sums = pd.merge(df_sums, df_budget[budget_value_column], left_index=True, right_index=True, how='left')

    # For anything that has no budget, fill with 0
    # TODO: Can we get here now?  Think this might have been before some refactoring, but not now?
    df_sums.loc[df_sums[budget_value_column].isna(), budget_value_column] = 0.0

    # Apply moving average, if applicable
    if moving_average_window:
        # Do rolling mean for each budget_name, then put this back to original index (dropping the extra level added
        # by the groupby).  Maybe this could be done with a .transform instead?
        # If we don't groupby on budget_name, the rolling means bleed between each budget_name (eg, last transaction
        # of budgetA is averaged with first transaction of budgetB!)
        df_sums = (df_sums.groupby(level=budget_name_column).
                   rolling(moving_average_window).
                   mean().droplevel(0)
                   )

    df_sums[delta_column] = df_sums[amount_column] - df_sums[budget_value_column]

    # Add Subtotal "category" to see everything subtotaled
    if delta_column in df_sums.index.get_level_values(budget_name_column):
        raise ValueError("Tried to add Subtotal as budget but Subtotal already exists")
    subtotal = df_sums.groupby(level=datetime_column)[delta_column].sum()
    subtotal = pd.concat([subtotal], keys=[SUBTOTAL_BUDGET_NAME], names=[BUDGET_NAME_COLUMN])
    df_sums = pd.concat([df_sums, subtotal.to_frame()])

    return df_sums


def budget_heatmap(df, datetime_column=DATETIME_COLUMN, category_column=CATEGORY_COLUMN,
                   amount_column=AMOUNT_COLUMN, budget=None, moving_average_window=None, start_date=None, end_date=None,
                   fig: go.Figure = None, annotations=True, annotation_text_size=8, delta_column=DELTA_COLUMN
                   ):
    """
    TODO:
        - Docstring
        - Visually show if there's no data before X date (right now it just looks like spending-budget is great!)

    Args:
        df:
        datetime_column:
        category_column:
        amount_column:
        budget:  (or really budget collection?)
        moving_average_window:
        start_date:
        end_date:
        fig:
        annotations (bool): If True, write the (amount-budget) value in each cell of the heatmap

    Returns:

    """
    if fig is None:
        fig = go.Figure()

    start_date, end_date, date_range = _parse_dates(datetime_column, df, end_date, start_date, moving_average_window)

    # If we have no data here, we haven't selected any categories to plot.  Escape
    if len(df) == 0:
        # no data!
        return fig

    # Construct plot
    zmid = 0
    zmin, zmax = get_rounded_z_range_including_mid(df[delta_column], zmid, round_to=10)
    colorscale = make_centered_rg_colorscale(zmin, zmax, zmid)

    # For plotting, reverse the order of the rows.  Rows picked on the sidebar are populated top to bottom, but y-values
    # on a heatmap show from bottom to top (increasing y direction)
    df_sums = _reverse_index_level_order(df, BUDGET_NAME_COLUMN)

    df_sums.sort_index()
    fig.add_trace(
        go.Heatmap(
            x=df_sums.index.get_level_values(datetime_column),
            y=df_sums.index.get_level_values(BUDGET_NAME_COLUMN),
            z=df_sums[DELTA_COLUMN],
            text=df_sums[DELTA_COLUMN],
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            xgap=1,
            ygap=3,
        )
    )

    if annotations:
        annotations = _make_annotations(df_sums, annotation_text_size, delta_column)
        fig.update_layout(
            annotations=annotations,
        )

    fig.update_layout(
        **FIGURE_BACKGROUND
    )
    fig.update_yaxes(dtick=1)

    # Ensure axes show full range of data, and pad by same amount as other figures
    fig.update_xaxes(range=[start_date - X_AXIS_PAD, end_date], dtick="M1")

    return fig


def monthly_bar(df, datetime_column=DATETIME_COLUMN, y_column=AMOUNT_COLUMN, delta_column=DELTA_COLUMN,
                budget=None, moving_average_window=None,
                start_date=None, end_date=None, fig=None, plot_burn_rate=False):
    """
    Returns a plotly figure of a bar chart of df[y_column], grouped monthly by df[datetime_column].

    Optionally has a horizontal line at y=budget, a moving average of the monthly data overlaid on the figure, and
    lineplots overlaid on each bar showing the burn rate per month.

    Optionally truncates view of the figure between start_date and end_date, but these only affect the range shown
    on the plot and do not remove data from being used in the moving average.
    """
    if fig is None:
        fig = go.Figure()

    start_date, end_date, date_range = _parse_dates(datetime_column, df, end_date, start_date, moving_average_window)

    # Rearrange data into what we need
    df_monthly = df.groupby(pd.Grouper(key=datetime_column, freq='MS')).sum().reindex(date_range, fill_value=0.0)

    if plot_burn_rate:
        df_daily = df.groupby(pd.Grouper(key=datetime_column, freq='d')).sum()
        # Get the cumulative daily sum, reset every month
        # No key because groupby by default moved datetime to index, and Grouper uses index as default key
        # Use .transform to return a series of the same shape as the input data so I can reincorporate into df_daily
        # ...I think I could leave it out and it would work here because pd.Series.cumsum returns the same shape anyway,
        # but this would also work for something like transform(pd.Series.sum)
        df_daily['cumsum'] = df_daily.groupby(pd.Grouper(freq='MS'))[y_column].transform(pd.Series.cumsum)

        # Make a column of the index for easier groupby
        df_daily[datetime_column] = df_daily.index

        # Make a datetime that is normalized/shifted to sit inside a bar chart bar
        # (bars are plotted centered on their date)
        df_daily[f'shifted_{datetime_column}'] = df_daily.groupby(pd.Grouper(freq="MS"))[datetime_column] \
            .transform(date_shift)

    # Plot bars monthly
    bar_name = "Monthly"
    if budget:
        bar_name += f" (budget = ${budget})"
    fig.add_trace(go.Bar(
        x=df_monthly.index,
        y=df_monthly[y_column],
        name=bar_name,
        hoverinfo="y",
    ))

    # Ensure axes show full range of data, and pad by same amount as other figures
    fig.update_xaxes(range=[start_date - X_AXIS_PAD, end_date], dtick="M1")

    if budget:
        fig.add_shape(
            type="line",
            xref="paper",
            x0=0,
            x1=1,
            yref='y',
            y0=budget,
            y1=budget,
            line=dict(
                dash="dot",
                width=3,
                color='cyan',
            ),
            name=f"Budget ({budget})",
        )

    if moving_average_window:
        df_ma = (df_monthly[[y_column]]
                 .rolling(moving_average_window)
                 .mean()
                 )
        df_ma = df_ma.loc[df_ma[y_column].notna()]

        if budget and len(df_ma) > 0:
            # TODO: This hovertext would make more sense in the bar rather than on just the moving average dot
            df_ma[delta_column] = df_ma[y_column] - budget
            df_ma['overunder'] = df_ma.apply(lambda row: "under" if row.loc[delta_column] > 0 else "over", axis=1)
            hovertext = df_ma.apply(
                lambda row: f"${row.loc[y_column]:.2f} (${abs(row.loc[delta_column]):.2f} {row.loc['overunder']} budget)",
                axis=1)
            hovertext = hovertext.to_list()

            # hovertext = (df_ma[y_column] - budget).to_list(),
            # hovertext = []
            hoverinfo = "text"
        else:
            hoverinfo = "none",
            hovertext = ""

        def set_color(val):
            if budget is None:
                return "black"
            if val > budget:
                return "green"
            else:
                return "red"

        fig.add_trace(go.Scatter(
            x=df_ma.index,
            y=df_ma[y_column],
            line=dict(
                # dash="dash",
                color="grey",
                width=3,
            ),
            marker=dict(
                size=7,
                color=list(map(set_color, df_ma[y_column]))
            ),
            name=f"{moving_average_window} Month Moving Average",
            hoverinfo=hoverinfo,
            hovertext=hovertext,
        ))

    if plot_burn_rate:
        for name, df_daily_this_month in df_daily.groupby(pd.Grouper(freq='MS')):
            fig.add_trace(go.Scatter(
                # x=df_daily_this_month.index - datetime.timedelta(days=15),
                x=df_daily_this_month[f'shifted_{datetime_column}'],
                y=df_daily_this_month['cumsum'],
                showlegend=False,
                line=dict(
                    dash="dot",
                    color="black",
                    width=2,
                ),
            ))

    return fig


def _make_annotations(df_sums, annotation_text_size=8, delta_column=DELTA_COLUMN):
    annotations = []
    for (cat, datetime_), ds in df_sums.iterrows():
        kwargs = dict(
            text=f"<b>${ds[delta_column]:.0f}</b>",
            x=datetime_,
            y=cat,
            **ANNOTATION_ARGS,
        )
        # Add/Update annotation_text_size without clobbering existing fonts
        kwargs['font'] = kwargs.get('font', {})
        kwargs['font'].update({'size': annotation_text_size})

        annotations.append(
            go.layout.Annotation(
                **kwargs
            )
        )
    return annotations


def _parse_dates(date_column, df, end_date, start_date, moving_average_window):
    """
    Returns parsed start_ and end_date and a date_range for the dates, including left padding for moving_average_window

    start_date is rounded down to the beginning of its month, end_date is rounded up to the beginning of the next month,
    so that a date_range from them includes all months that they're present in.  date_range is wider than the
    interval between start_date and end_date by moving_average_window months

    Args:
        date_column:
        df:
        end_date:
        start_date:

    Returns:

    """
    if start_date is None:
        start_date = df[date_column].min()
    else:
        start_date = pd.to_datetime(start_date)
    start_date = round_date_to_month_begin(start_date)

    if moving_average_window:
        start_date_padded = round_date_to_month_begin(start_date, -(moving_average_window - 1))
    else:
        start_date_padded = start_date

    if end_date is None:
        end_date = df[date_column].max()
    else:
        end_date = pd.to_datetime(end_date)
    end_date = end_date + pd.offsets.MonthEnd(0)

    date_range = pd.date_range(start=start_date_padded, end=end_date, freq='MS')
    return start_date, end_date, date_range


def _reverse_index_level_order(df, level_name):
    """
    Reverses the index (row) order of a multiindexed dataframe

    Gets a list of unique index values in the reversed order and then reindexes.  Not tested and likely has problems
    if the level being reversed is broken into several groups
    """
    unique_names = pd.unique(df.index.get_level_values(level_name))
    unique_names_reversed = reversed(unique_names)
    return df.reindex(unique_names_reversed, level=level_name)


def get_app_layout():
    return html.Div(
        children=[
            # Banner
            dbc.Container(
                [
                    dbc.Row(
                        children=[
                            dbc.Col(
                                id='controls-sidebar',
                                children=get_controls(depth=3),
                                lg=3, md=4, xs=6,  # Responsive widths
                            ),
                            dbc.Col(
                                children=[
                                    html.Div(
                                        id='heatmap-graph-div',
                                        children=dcc.Graph(
                                            id='heatmap-graph',
                                            # This should be set commonly with any other figures
                                            style={'height': '55vh'},
                                        ),
                                        # Start with graph hidden (no data populating it yet)
                                        # This gets quickly overridden by the callbacks which instead make invisible
                                        # figures, but it avoids an empty plot showing briefly during load
                                        style={'display': 'none'},
                                    ),
                                    html.Div(
                                        id='bar-graph-div',
                                        children=dcc.Graph(
                                            id='bar-graph',
                                            # This should be set commonly with any other figures
                                            style={'height': '35vh'},
                                        ),
                                        # Start with graph hidden (no data populating it yet)
                                        style={'display': 'none'},
                                    ),
                                ],
                                lg=9, md=8, xs=6,
                                id="content-col",
                            ),
                        ]
                    ),
                ],
                fluid=True,
            ),
            html.Div(
                id=WORKING_DATA_ID,  # JSONified pandas df holding the current data subset (to avoid duplicate work)
            )
        ]
    )


def get_date_picker():
    # Is there a better way to do this where I don't need a separate data access step purely for the date_picker?
    # Wasn't sure how to make a date picker placeholder then update it later.  Maybe I can store it globally and change
    # its properties later?
    df = get_transactions('df')
    start_date = "2019-01-01"
    end_date = df[DATETIME_COLUMN].max()

    return dcc.DatePickerRange(
        id='monthly-hist-date-range',
        start_date=pd.to_datetime(start_date),
        end_date=pd.to_datetime(end_date),
        # min_date_allowed=pd.to_datetime("2019-01-01"),
        # max_date_allowed=pd.to_datetime("2020-01-01"),  # Could set to real data range
        display_format="YYYY-MMM-DD",
        className="controls-sidebar",
        # style={'height': 1110},
    )


def get_controls(depth):
    return html.Div(
        dbc.Container(
            [
                dbc.Row([
                    dbc.Col(
                        get_date_picker(),
                        style={'fontSize': 5}
                    ),
                ]
                ),
                dbc.Row([
                    dbc.Col(
                        html.Div("Moving Average"),
                        **SLIDER_TITLE_WIDTHS,  # Responsive widths
                    ),
                    dbc.Col(
                        get_moving_average_slider(),
                        **SLIDER_WIDTHS,  # Responsive widths
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div("Budget Depth"),
                        **SLIDER_TITLE_WIDTHS,
                    ),
                    dbc.Col(
                        get_depth_slider(depth),
                        **SLIDER_WIDTHS,
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div("Annotation Size"),
                        **SLIDER_TITLE_WIDTHS,
                    ),
                    dbc.Col(
                        get_annotation_size_slider(),
                        **SLIDER_WIDTHS,
                    ),
                ]),
                dbc.Row([
                    html.Div(make_sidebar_ul(BUDGET_COLLECTION.categories_flat_dict,
                                             "Overall",
                                             depth=depth,
                                             )),
                ]),
            ],
            fluid=True
        ),
        className='controls-sidebar-base',
    )


def get_moving_average_slider():
    return dcc.Slider(
        id="monthly-hist-ma-slider",
        min=1,
        max=12,
        step=None,
        marks={x: str(x) for x in MOVING_AVERAGE_SLIDER_TICKS},
        value=6,
        className="controls-sidebar",
    )


def get_depth_slider(depth):
    return dcc.Slider(
        id="monthly-hist-depth-slider",
        min=0,
        max=3,
        step=1,
        marks={x: str(x) for x in range(4)},
        value=depth,
        className="controls-sidebar",
    )


def get_annotation_size_slider():
    return dcc.Slider(
        id="annotation-size-slider",
        min=0,
        max=14,
        step=2,
        marks={x: str(x) for x in [0, 8, 10, 12, 14]},
        value=14,
        className="controls-sidebar",
    )


@app.callback(
    Output("controls-sidebar", "children"),
    [
        Input("monthly-hist-depth-slider", "value")
    ]
)
def update_controls(depth):
    return get_controls(depth=depth)


@app.callback(
    [
        Output("heatmap-graph-div", "style"),
        Output("heatmap-graph", "figure"),
        Output(WORKING_DATA_ID, "children"),
    ],
    [
        Input('monthly-hist-date-range', "start_date"),
        Input('monthly-hist-date-range', "end_date"),
        Input("monthly-hist-ma-slider", "value"),
        Input("sidebar-ul", "children"),
        Input("annotation-size-slider", "value")
    ],
)
def update_heatmap(start_date, end_date, ma, sidebar_ul_children, annotation_text_size):
    """
    TODO: Docs
    -   note that we persis data in WORKING_DATA_ID for the xy plot
    """
    budgets_to_show = get_checked_sidebar_children(sidebar_ul_children)

    div_style = {'display': 'block'}

    if len(budgets_to_show) == 0:
        # If no data selected, return an empty, blanked out figure and set the div style to not be hidden
        # There's a bug where if we hide this figure now, it'll raise javascript errors due to sizing.  I think it makes
        # a really small figure and then scales it up, but has trouble with the small figure?
        # Related to: https://github.com/plotly/plotly.js/issues/4155
        fig = invisible_figure()

        # "show" the invisible figure by returning a style {display == block}
        return div_style, fig, ""

    if annotation_text_size > 0:
        annotations = True
    else:
        annotations = False

    # Make a subset of the overall Budget definition for only these children
    bc_subset = BUDGET_COLLECTION.slice_by_budgets(budgets_to_show)

    df = get_transactions('df')
    # Aggregate transactions to the budgets we have chosen
    df = aggregate_to_budget_deltas(df, datetime_column=DATETIME_COLUMN, category_column=CATEGORY_COLUMN,
                                         amount_column=AMOUNT_COLUMN, budget=bc_subset, moving_average_window=ma, start_date=start_date,
                                         end_date=end_date, work_on_copy=False)

    fig = budget_heatmap(df,
                         datetime_column=DATETIME_COLUMN,
                         category_column=CATEGORY_COLUMN,
                         budget=bc_subset,
                         amount_column=AMOUNT_COLUMN,
                         moving_average_window=ma,
                         start_date=start_date,
                         end_date=end_date,
                         annotations=annotations,
                         annotation_text_size=annotation_text_size
                         )

    # Update layout to match other figures in this column
    fig.update_layout(margin=SHARED_FIGURE_MARGIN)
    fig.update_yaxes(automargin=False)  # Otherwise our figures will be out of alignment
    return div_style, fig, df.to_json(orient='table')


# Sidebar callbacks
app.callback(
    Output("sidebar-ul", "children"),
    [Input({"type": "list_item", "id": ALL}, 'n_clicks'), ],
    [State("sidebar-ul", "children")]
)(register_sidebar_list_click)


@app.callback(
    [
        Output("bar-graph-div", "style"),
        Output("bar-graph", "figure"),
    ],
    [
        Input("heatmap-graph", "clickData"),
        Input('monthly-hist-date-range', "start_date"),
        Input('monthly-hist-date-range', "end_date"),
        Input("monthly-hist-ma-slider", "value"),
     ],
    [
        State(WORKING_DATA_ID, "children"),
    ]
)
def update_barchart(clickData, start_date, end_date, moving_average_window, working_data):
    div_style = {'display': 'block'}

    if not clickData:
        # See update_heatmap for why we return an invisible figure and always set div visible
        fig = invisible_figure()
        return div_style, fig

    # budget_name is first point clicked's (click only returns one) y attribute
    budget_name = clickData["points"][0]['y']


    if budget_name == SUBTOTAL_BUDGET_NAME:
        budget_amount = None
        plot_burn_rate = False
        # Special case where data is not in DB
        df = pd.read_json(working_data, orient='table')
        df = df.reset_index()
        df[AMOUNT_COLUMN] = df[DELTA_COLUMN]
    else:
        budget = BUDGET_COLLECTION.get_budget_by_name(budget_name)
        budget_amount = budget.amount
        plot_burn_rate = True
        df = get_transactions('df')
        # Filter down to only the budget_name we care about, aggregating categories to a budget if needed
        df[BUDGET_NAME_COLUMN] = budget.aggregate_categories_to_budget(df[CATEGORY_COLUMN], depth='this')

    df = df.loc[df[BUDGET_NAME_COLUMN] == budget_name]

    fig = monthly_bar(df,
                      datetime_column=DATETIME_COLUMN,
                      y_column=AMOUNT_COLUMN,
                      budget=budget_amount,
                      moving_average_window=moving_average_window,
                      start_date=start_date,
                      end_date=end_date,
                      plot_burn_rate=plot_burn_rate,
                      )

    # Update layout to match other figures in this column
    fig.update_layout(
        legend_orientation='h',
        margin=SHARED_FIGURE_MARGIN,
    )
    # Apply transparent background
    fig.update_layout(
        **FIGURE_BACKGROUND,
    )
    # Aligned with above, use the title as a heading to the figure, and don't show the ticks since they're redundant
    # with the figure above
    fig.update_xaxes(
        title=f"<b>{budget_name}</b>",
        title_font=dict(size=18),
        showticklabels=False,
        side='top',
    )

    fig.update_yaxes(automargin=False)

    return div_style, fig


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "db",
        help="Path to transactions database",
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    global_init(args.db, echo=False)

    app.layout = get_app_layout()
    app.run_server(debug=True, port=8051)
