import argparse
import copy
from pprint import pprint
import pandas as pd
import numpy as np

import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import State, Input, Output
import dash_table

from spearmint.dashboard.diff_dashtable import diff_dashtable
from spearmint.data.db_session import global_init
from spearmint.data.transaction import Transaction
from spearmint.services.budget import get_expense_budget_collection
from spearmint.services.transaction import get_all_transactions


SUGGESTED_CATEGORY_PREFIX = "suggested category"

# Column to keep track of any edits in the table
CHANGED_COLUMN = "__changed"

# "unique" padding for start and end of each column specified in the changed column to make them more unique.  Otherwise
# if we had columns of "Product Description" and "Description", "Description" might get triggered by both
CHANGED_PAD_START = "__"
CHANGED_PAD_END = "__"

COLUMNS_TO_SHOW_FROM_DATA = ['id', 'datetime', 'amount', 'category', 'description'] + \
                            [f"{SUGGESTED_CATEGORY_PREFIX}_{i}" for i in range(1)]
ADDITIONAL_COLUMNS_TO_SHOW = []
COLUMNS_TO_EDIT = ['category']
COLUMN_DROPDOWNS = {
    # "category": {
    #     "options": [{"label": v, "value": v} for v in get_expense_budget_collection()]
    # }
}
COLUMNS_TO_HIDE = [CHANGED_COLUMN]
COLUMNS_CLICKABLE_MAP = {f"{SUGGESTED_CATEGORY_PREFIX}_{i}": "category" for i in range(1)}
COLUMNS_TO_SHOW = COLUMNS_TO_SHOW_FROM_DATA + ADDITIONAL_COLUMNS_TO_SHOW + COLUMNS_TO_HIDE

app = dash.Dash(__name__)


def define_columns(columns, editable):
    return [{"name": c, "id": c, "editable": c in editable} for c in columns]


def load_data(n_suggested_categories=1):
    """
    Gets data from the db and adds any extra columns

    # TODO: Handle suggested categories more explicitly (dict specifying number per scheme?)

    Args:
        n_suggested_categories (int): Number of suggested categories to pull from the database

    Returns:
        (pd.DataFrame):
    """
    # df = get_all_transactions('df')
    trxs = get_all_transactions()

    def trx_to_dict(trx: Transaction):
        # TODO: Sync these with globals above for shown columns
        d = {k: getattr(trx, k) for k in ['id', 'datetime', 'amount', 'description']}
        d['category_id'] = trx.category_id
        if d['category_id']:
            d['category'] = trx.category.category
        else:
            d['category'] = None

        for i in range(n_suggested_categories):
            try:
                d[f'{SUGGESTED_CATEGORY_PREFIX}_{i}'] = trx.categories_suggested[i].category
                d[f'{SUGGESTED_CATEGORY_PREFIX}_id_{i}'] = trx.categories_suggested[i].id
            except IndexError:
                d[f'{SUGGESTED_CATEGORY_PREFIX}_{i}'] = None
                d[f'{SUGGESTED_CATEGORY_PREFIX}_id_{i}'] = None
            # suggested = trx.categories_suggested
            # for i, cat in enumerate(trx.categories_suggested[:n_suggested_categories]):
            #     d[f'{SUGGESTED_CATEGORY_PREFIX}_{i}'] = trx.categories_suggested[i].category
            #     d[f'{SUGGESTED_CATEGORY_PREFIX}_id_{i}'] = trx.categories_suggested[i].id

        return d

    trxs_as_dicts = [trx_to_dict(trx) for trx in trxs]
    df = pd.DataFrame(trxs_as_dicts)

    for c in ADDITIONAL_COLUMNS_TO_SHOW + COLUMNS_TO_HIDE:
        if c in df:
            raise ValueError(f"Column {c} already exists!  Cannot add hidden column that overlaps with main data")
        df[c] = None

    # TODO: things like populate suggestions via ML!  Or just randomly create them...
    # possible_categories = pd.unique(df['category'])
    # np.random.seed(42)
    # df['suggested category'] = np.random.choice(possible_categories, len(df))

    return df


def get_app_layout():
    children = [
        html.H1("Transaction Table"),
        dash_table.DataTable(
            id='transaction-table',
            columns=define_columns(columns=COLUMNS_TO_SHOW, editable=COLUMNS_TO_EDIT),
            data=load_data().to_dict('records'),
            editable=True,
            # Set dropdowns within columns by dict
            dropdown=COLUMN_DROPDOWNS,
            style_table={'height': '90vh', 'overflowY': 'auto'},
            # style_data_conditional=[
            #     {
            #         "if": {
            #             "filter_query": f"{{{CHANGED_COLUMN}}} contains {CHANGED_PAD_END}Description{CHANGED_PAD_END}",
            #             "column_id": "Description",
            #         },
            #         "backgroundColor": "rgb(240, 240, 240)",
            #     }
            # ]
        ),
        html.Div(id='sink1'),
    ]

    return html.Div(children)


# Callbacks
@app.callback(
    Output("transaction-table", "data"),
    [Input("transaction-table", "data_timestamp"),
     Input("transaction-table", "active_cell"),
     ],
    [State("transaction-table", "data"),
     State("transaction-table", "data_previous"),
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
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == '.':
        return dash.no_update

    data_edited = False

    # We have both callbacks that can cause edits (click here and change data somewhere else) and callbacks that react
    # to data changes (see a change in the table and possibly enact another change).  If we want the former to trigger
    # the latter, we need to do it ourselves (the callback wont trigger automatically, and if it did we'd have an
    # infinite loop)

    # These are logic branches that can result in edited data.  If we want them to trigger the later "on-edit" callback,
    # raise the data_edited flag
    if ctx.triggered[0]["prop_id"].endswith(".active_cell"):
        returned = table_on_click_via_active_cell(active_cell, data, COLUMNS_CLICKABLE_MAP)
        if returned:
            data, data_previous, data_edited = returned
        else:
            data_edited = False
        # Do not return here because we still must hit the on-edit callback below

    # Final action that responds to edited data.  Do this separately and trigger both on data_timestamp (eg: user
    # changed something in the table on screen) and the data_edited boolean from above (callback changed data)
    if ctx.triggered[0]["prop_id"].endswith(".data_timestamp") or data_edited:
        return table_edit_callback(data, data_previous)

    return dash.no_update


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


def table_on_click_via_active_cell(active_cell, rows, clickable_column_map):
    """
    Hack to make a cell in a DashTable act like a button.

    If any cell in column 'a' is clicked, it overwrites this row's data in column b with the value in column a

    Returns:
        If a change is made, returns (rows, rows_prior_to_change)
        If a change is not made, returns None
    """
    if active_cell is None:
        return None

    # If I click on a column that is clickable, (eg suggestion X), put that value into a different column (eg category)
    if active_cell['column_id'] in clickable_column_map:
        print("Caught click")
        source_column = active_cell['column_id']
        target_column = clickable_column_map[source_column]

        # Check if destination already has this content
        if rows[active_cell['row']][target_column] == rows[active_cell['row']][source_column]:
            print("data already updated")
            return None
        else:
            print('updating data')
            # Make a deep copy of rows so we can later compare data to data_previous
            rows_previous = copy.deepcopy(rows)
            rows[active_cell['row']][target_column] = rows[active_cell['row']][source_column]
            return rows, rows_previous, True

    # No edits
    return None


# CLI

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
    ports = range(8850, 8860, 1)
    for port in ports:
        try:
            print(f"TRYING PORT {port}")
            app.run_server(debug=True, port=port)
        except OSError:
            continue
        break
