import argparse
import datetime

import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
import plotly.graph_objects as go

from spearmint.dashboard.budget_sidebar_elements import make_sidebar_ul
from spearmint.dashboard.budget_sidebar_elements import register_sidebar_list_click, get_checked_sidebar_children
from spearmint.dashboard.utils import get_rounded_z_range_including_mid, make_centered_rg_colorscale
from spearmint.data.db_session import global_init
from spearmint.data_structures.budget import BudgetCollection
from spearmint.services.budget import get_expense_budget_collection
from spearmint.services.transaction import get_all_transactions, get_transaction_categories

MOVING_AVERAGE_SLIDER_TICKS = [1, 2, 3, 6, 12]
ANNOTATION_ARGS = dict(
    xref='x1',
    yref='y1',
    showarrow=False,
    font=dict(color='black',),
)

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

BUDGET_COLLECTION = get_expense_budget_collection()


def budget_heatmap(df, datetime_column='datetime', category_column='category',
                   amount_column='amount', budget=None, moving_average_window=None, start_date=None, end_date=None,
                   fig: go.Figure = None,
                   ):
    """
    TODO:
        - Docstring
        - validate moving_average_window (coded but not rigorously checked)
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

    Returns:

    """
    df = df.copy()
    # Accept budget
    # - If number apply budget to all categories evenly (currently done)
    # - (NOT IMPLEMENTED) If mapping (ds, dict), apply budget to all categories of the mapped name.  Show only those categories (plot
    #   nothing without a budget).  Could use the same budget-category but with it =category
    # - If BudgetCollection, make a budget-category column with anything that should be aggregated to its corresponding
    #   budget.  Then plot on what is mapped

    if fig is None:
        fig = go.Figure()

    end_date, start_date, date_range = _parse_dates(datetime_column, df, end_date, start_date)

    # If we have a budget collection with aggregated budgets (multiple categories -> single budget), aggregate
    if isinstance(budget, BudgetCollection):
        df['budget_name'] = budget.aggregate_categories_to_budget(df[category_column])
        budget_names = [b.name for b in budget.get_budgets()]
    else:
        raise NotImplementedError("This is not done.  I think we need to catch if dict here and do something.  "
                                  "Not sure about int")
        df['budget_name'] = df[category_column]
        budget_names = pd.unique(df['budget_name'])

    # Reject anything that doesn't have a mapped budget_name (because we don't care about it!)
    df = df.dropna(subset=['budget_name'])

    # If we have no data here, we haven't selected any categories to plot.  Escape
    if len(df) == 0:
        # no data!
        return fig

    # Rearrange df of individual transactions into format needed
    df_sums = df[['budget_name', datetime_column, amount_column]]\
        .groupby(['budget_name', pd.Grouper(key='datetime', freq='MS')]).sum()

    # Make a regular index with all category/month combinations having values.
    # Fill anything missing with 0
    new_index = pd.MultiIndex.from_product((budget_names, date_range), names=['budget_name', datetime_column])
    df_sums = df_sums.reindex(new_index, fill_value=0)

    # Rearrange budget into format needed
    # TODO: Handle various possible budget input types more rigorously
    if isinstance(budget, (float, int)):
        # All budget values are equal and set to the number budget
        # Build budget such that each month/category has the same budget value, and it covers all values in df_sums
        df_budget = pd.DataFrame({'budget': [budget] * len(df_sums.index)}, index=df_sums.index)
        # Alternatively, could make this a {category: _, budget: _} dataframe (no date) and cast to all months using
        # same code as below
    elif isinstance(budget, BudgetCollection):
        name_amount = [(b.name, b.amount) for b in budget.get_budgets()]
        name, amount = list(zip(*name_amount))

        # Indexed by budget_name
        df_budget = pd.DataFrame({'budget': amount}, index=name)

        # Reindexed to broadcast across all dates
        # level sets the index to match to.  Others are broadcast across
        df_budget = df_budget.reindex(df_sums.index, level='budget_name')


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

    df_sums = pd.merge(df_sums, df_budget['budget'], left_index=True, right_index=True, how='left')

    # For anything that has no budget, fill with 0
    # TODO: Can we get here now?  Think this might have been before some refactoring, but not now?
    df_sums.loc[df_sums['budget'].isna(), 'budget'] = 0.0

    # Apply moving average, if applicable
    if moving_average_window:
        df_sums = (df_sums.rolling(moving_average_window).
                   mean()
                   )

    df_sums['delta'] = df_sums[amount_column] - df_sums['budget']

    # Construct plot
    annotations = _make_annotations(df_sums)
    zmid = 0
    zmin, zmax = get_rounded_z_range_including_mid(df_sums['delta'], zmid, round_to=10)
    colorscale = make_centered_rg_colorscale(zmin, zmax, zmid)

    fig.add_trace(
        go.Heatmap(
            x=df_sums.index.get_level_values(datetime_column),
            y=df_sums.index.get_level_values("budget_name"),
            z=df_sums['delta'],
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
        )
    )
    fig.update_layout(annotations=annotations)
    fig.update_yaxes(dtick=1)
    return fig


def _make_annotations(df_sums):
    annotations = []
    for (datetime_, cat), ds in df_sums.iterrows():
        annotations.append(
            go.layout.Annotation(
                text=f"<b>${ds['delta']:.2f}</b>",
                x=datetime_,
                y=cat,
                **ANNOTATION_ARGS,
            )
        )
    return annotations


def _parse_dates(date_column, df, end_date, start_date):
    if start_date is None:
        start_date = df[date_column].min()
    else:
        start_date = pd.to_datetime(start_date)
    if end_date is None:
        end_date = df[date_column].max()
    else:
        end_date = pd.to_datetime(end_date)

    date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
    return end_date, start_date, date_range


def get_date_picker():
    # Is there a better way to do this where I don't need a separate data access step purely for the date_picker?
    # Wasn't sure how to make a date picker placeholder then update it later.  Maybe I can store it globally and change
    # its properties later?
    df = get_all_transactions('df')
    start_date = df["datetime"].min()
    end_date = df["datetime"].max()

    return dcc.DatePickerRange(
        id='monthly-hist-date-range',
        start_date=pd.to_datetime(start_date),
        end_date=pd.to_datetime(end_date),
        # min_date_allowed=pd.to_datetime("2019-01-01"),
        # max_date_allowed=pd.to_datetime("2020-01-01"),  # Could set to real data range
        display_format="YYYY-MMM-DD",
        className="controls-sidebar",
    )


def get_controls():
    return html.Div(
        [
            get_date_picker(),
            html.Hr(),
            dcc.Slider(
                id="monthly-hist-ma-slider",
                min=1,
                max=12,
                step=None,
                marks={x: str(x) for x in MOVING_AVERAGE_SLIDER_TICKS},
                value=3,
                className="controls-sidebar",
            ),
            html.Hr(),
            html.Div(make_sidebar_ul(BUDGET_COLLECTION.categories_flat_dict,
                                     "Expenses",
                                     )),
        ],
        className='controls-sidebar-base'
        # style=dict(fontSize='10px'),
    )

def get_app_layout():
    return html.Div(
        children=[
            # Banner
            html.H1(children="Budget Heatmaps"),
            dbc.Container(
                [
                    dbc.Row(
                        children=[
                            dbc.Col(
                                children=get_controls(),
                                lg=3, md=4, xs=6,  # Responsive widths
                            ),
                            dbc.Col(
                                children=[
                                    dcc.Graph(
                                        id='main-graph',
                                        # This should be set commonly with any other figures
                                        style={'height': '80vh'},
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
        ]
    )


@app.callback(Output("main-graph", "figure"),
              [Input('monthly-hist-date-range', "start_date"),
               Input('monthly-hist-date-range', "end_date"),
               Input("monthly-hist-ma-slider", "value"),
               Input("sidebar-ul", "children")
               ],
              )
def update_figure(start_date, end_date, ma, sidebar_ul_children):
    df = get_all_transactions('df')

    budgets_to_show = get_checked_sidebar_children(sidebar_ul_children)

    # Make a subset of the overall Budget definition for only these children
    bc_subset = BUDGET_COLLECTION.slice_by_budgets(budgets_to_show)

    fig = budget_heatmap(df,
                         datetime_column='datetime',
                         category_column='category',
                         budget=bc_subset,
                         amount_column='amount',
                         moving_average_window=ma,
                         start_date=start_date,
                         end_date=end_date,
                         )
    return fig


# Sidebar callbacks
app.callback(
    Output("sidebar-ul", "children"),
    [Input({"type": "list_item", "id": ALL}, 'n_clicks'), ],
    [State("sidebar-ul", "children")]
)(register_sidebar_list_click)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "db",
        help="Path to transactions database",
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    global_init(args.db, echo=True)

    app.layout = get_app_layout()
    app.run_server(debug=True, port=8051)
