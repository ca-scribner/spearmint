import copy
import json
from pprint import pprint
import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import State, Input, Output
import dash_table
import pandas as pd

df = pd.read_csv('../secrets/pc_2019-09-13_to_2020-05-11.csv')

app = dash.Dash(__name__)

# NOTES:
#   -   dash_table.DataTable returns a DashTable object.  It has an attribute for every item we add in the constructor.
#       we could modify them after init if that makes an easier workflow.  Can do things like add tables, edit columns
#       to add dropdowns, etc

# Column to keep track of any edits in the table
CHANGED_COLUMN = "__changed"

# "unique" padding for start and end of each column specified in the changed column to make them more unique.  Otherwise
# if we had columns of "Product Description" and "Description", "Description" might get triggered by both
CHANGED_PAD_START = "__"
CHANGED_PAD_END = "__"


def get_app_layout():
    children = [
        html.H1(id="header"),
        dash_table.DataTable(
            id='table',
            columns=[
                {"name": "Description", "id": "Description"},
                {"name": "Type", "id": "Type", "presentation": "dropdown"},
                {"name": "Card Holder Name", "id": "Card Holder", "presentation": "dropdown"},
                {"name": "Date", "id": "Date"},
                {"name": "Amount", "id": "Amount"},
                {"name": CHANGED_COLUMN, "id": CHANGED_COLUMN},
            ],
            data=df.to_dict('records'),
            editable=True,
            # Set dropdowns within columns by dict
            dropdown={
                # 'Type': {
                #     'options': [{'label': v, 'value': v} for v in pd.unique(df["Type"])],
                # },
                'Card Holder Name': {
                    'options': [{'label': v, 'value': v} for v in ["CARMEN", "HEATHER"]],
                }
            },
            style_table={'height': '90vh', 'overflowY': 'auto'},
            style_data_conditional=[
                {
                    "if": {
                        "filter_query": f"{{{CHANGED_COLUMN}}} contains {CHANGED_PAD_END}Description{CHANGED_PAD_END}",
                        "column_id": "Description",
                    },
                    "backgroundColor": "rgb(240, 240, 240)",
                }
            ]
        ),
        html.Div(id='sink1'),
    ]

    return html.Div(children)

app.layout = get_app_layout()


@app.callback(
    Output("table", "data"),
    [Input("table", "data_timestamp"),
     Input("table", "active_cell"),
    ],
    [State("table", "data"),
     State("table", "data_previous"),
    ]
)
def table_data_update_dispatcher(data_timestamp, active_cell, data, data_previous):
    """
    This callback wraps all actions that will result in the table data being output

    Future: Update this to instead take input of hidden div's (one for each separate process that wants to edit data)
            and pass the rows/columns to edit via these divs)
    """
    # This might not work properly if table is supposed to be empty
    if data is None and data_previous is None:
        return dash.no_update

    # During app boot (?) the callback fires without normal trigger events.  Do nothing
    ctx = dash.callback_context
    pprint(ctx.triggered)
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return dash.no_update

    data_edited = False

    # We have both callbacks that can cause edits (click here and change data somewhere else) and callbacks that react
    # to data changes (see a change in the table and possibly enact another change).  If we want the former to trigger
    # the latter, we need to do it ourselves (the callback wont trigger automatically, and if it did we'd have an
    # infinite loop)

    # These are logic branches that can result in edited data.  If we want them to trigger the later "on-edit" callback,
    # raise the data_edited flag
    if ctx.triggered[0]["prop_id"] == "table.active_cell":
        # Simulate data_previous because on-click callback needs it but app State wont provide it in this case
        data_previous = copy.deepcopy(data)
        data = table_on_click_via_active_cell(active_cell, data)
        data_edited = True
        # Do not return here because we still must hit the on-edit callback below

    # Final action that responds to edited data.  Do this separately and trigger both on data_timestamp (eg: user
    # changed something in the table on screen) and the data_edited boolean from above (callback changed data)
    if ctx.triggered[0]["prop_id"] == "table.data_timestamp" or data_edited:
        return table_edit_callback(data, data_previous)

    raise ValueError("I should not be here.  Something isn't working right")


def table_edit_callback(data, data_previous):
    """
    Compares two dash table data entities, printing the (row, column) locations of any differences
    """
    # Determine where the change occurred
    diff = diff_dashtable(data, data_previous)

    for d in diff:
        r_changed = d['index']
        c_changed = d['column_name']

        # If the column is empty it won't be in the dict.  Use .get to handle this with empty string as default
        data[r_changed][CHANGED_COLUMN] = f"{data[r_changed].get(CHANGED_COLUMN, '')} {CHANGED_PAD_START}{c_changed}{CHANGED_PAD_END}"

    return data


def table_on_click_via_active_cell(active_cell, rows):
    """
    Hack to make a cell in a DashTable act like a button.

    If any cell in column 'a' is clicked, it overwrites this row's data in column b with the value in column a
    """
    if active_cell is None:
        return rows

    # If I click on a particular column (say suggestion X), put that value into a different column (say blessed clf)
    if active_cell['column_id'] == 'Type':
        rows[active_cell['row']]['Description'] = rows[active_cell['row']]['Type']

    return rows


# Helpers
def diff_dashtable(data, data_previous, row_id_name=None):
    """Generate a diff of Dash DataTable data.

    Modified from: https://community.plotly.com/t/detecting-changed-cell-in-editable-datatable/26219/2

    Parameters
    ----------
    data: DataTable property (https://dash.plot.ly/datatable/reference)
        The contents of the table (list of dicts)
    data_previous: DataTable property
        The previous state of `data` (list of dicts).
    row_id_name: String
        Name of row to use as a returnable row id.  If None, will use row index and return it with the key "index" in
        the returned dict

    Returns
    -------
    A list of dictionaries in form of [{row_id_name:, column_name:, current_value:,
        previous_value:}]
    """
    df, df_previous = pd.DataFrame(data=data), pd.DataFrame(data_previous)

    if row_id_name is not None:
        # If using something other than the index for row id's, set it here
        for _df in [df, df_previous]:

            # Why do this?  Guess just to be sure?
            assert row_id_name in _df.columns

            _df = _df.set_index(row_id_name)
    else:
        row_id_name = "index"

    # Pandas/Numpy says NaN != NaN, so we cannot simply compare the dataframes.  Instead we can either replace the
    # NaNs with some unique value (which is fastest for very small arrays, but doesn't scale well) or we can do
    # (from https://stackoverflow.com/a/19322739/5394584):
    # Mask of elements that have changed, as a dataframe.  Each element indicates True if df!=df_prev
    df_mask = ~((df == df_previous) | ((df != df) & (df_previous != df_previous)))

    # ...and keep only rows that include a changed value
    df_mask = df_mask.loc[df_mask.any(axis=1)]

    changes = []

    # This feels like a place I could speed this up if needed
    for idx, row in df_mask.iterrows():
        row_id = row.name

        # Act only on columns that had a change
        row = row[row.eq(True)]

        for change in row.iteritems():

            changes.append(
                {
                    row_id_name: row_id,
                    "column_name": change[0],
                    "current_value": df.at[row_id, change[0]],
                    "previous_value": df_previous.at[row_id, change[0]],
                }
            )

    return changes


if __name__ == '__main__':
    # Hacky way to auto pick a port
    ports = range(8850, 8860, 1)
    for port in ports:
        try:
            print(f"TRYING PORT {port}")
            app.run_server(debug=True, port=port)
        except OSError:
            continue
        break
