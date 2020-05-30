import argparse
import copy
import itertools
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
from spearmint.services.transaction import get_transactions


SUGGESTED_CATEGORY_PREFIX = "suggested category"
CATEGORY = "category"
CATEGORY_ID_SUFFIX = "_id"
CATEGORY_ID = CATEGORY + CATEGORY_ID_SUFFIX

# Column to keep track of any edits in the table
CHANGED_COLUMN = "__changed"

# "unique" padding for start and end of each column specified in the changed column to make them more unique.  Otherwise
# if we had columns of "Product Description" and "Description", "Description" might get triggered by both
CHANGED_PAD_START = "__"
CHANGED_PAD_END = "__"

# Specs for suggested colums.
# TODO: Consolidate with other suggested defs
def get_suggested_columns(spec):
    to_return = []
    for i in range(spec['n']):
        to_return.extend((f"{spec['name']}_{i}", f"{spec['name']}_{i}{CATEGORY_ID_SUFFIX}"))
    return to_return

SUGGESTED_COLUMN_SPECS = [
    {'name': f'{SUGGESTED_CATEGORY_PREFIX}_from_file', 'scheme': 'from_file', 'n': 1, 'order_by': None},
    {'name': f'{SUGGESTED_CATEGORY_PREFIX}_from_clf', 'scheme': 'from_clf', 'n': 2, 'order_by': None},
]
# TODO: Simplify this expansion
SUGGESTED_COLUMNS_TO_SHOW = list(itertools.chain(*[get_suggested_columns(spec) for spec in SUGGESTED_COLUMN_SPECS]))

SUGGESTED_COLUMNS_TO_WATCH = [c for c in SUGGESTED_COLUMNS_TO_SHOW if not c.endswith(CATEGORY_ID_SUFFIX)]

COLUMNS_TO_SHOW_FROM_DATA = ['id', 'datetime', 'amount', CATEGORY, CATEGORY_ID, 'description'] + \
                            SUGGESTED_COLUMNS_TO_SHOW

ADDITIONAL_COLUMNS_TO_SHOW = []
COLUMNS_TO_EDIT = [CATEGORY]
COLUMN_DROPDOWNS = {
    # "category": {
    #     "options": [{"label": v, "value": v} for v in get_expense_budget_collection()]
    # }
}
COLUMNS_TO_HIDE = [CHANGED_COLUMN]
COLUMNS_TO_SHOW = COLUMNS_TO_SHOW_FROM_DATA + ADDITIONAL_COLUMNS_TO_SHOW + COLUMNS_TO_HIDE




app = dash.Dash(__name__)


def define_columns(columns, editable):
    return [{"name": c, "id": c, "editable": c in editable} for c in columns]


def load_data(suggested_columns=tuple()):
    """
    Gets data from the db and adds any extra columns

    Args:
        suggested_columns (dict): Specifies which suggested columns to show by defining a list of dicts:
                                    {scheme: category scheme,
                                     n: maximum number of suggestions to include for this scheme,
                                     order_by: How to order suggestions from a scheme.  'confidence' will order in
                                               descending confidence value.  None will be in order on transaction obj,
                                    }

    Returns:
        (pd.DataFrame):
    """
    # df = get_all_transactions('df')
    trxs = get_transactions()

    def trx_to_dict(trx: Transaction):
        # TODO: Sync these with globals above for shown columns
        d = {k: getattr(trx, k) for k in ['id', 'datetime', 'amount', 'description']}
        d[CATEGORY_ID] = trx.category_id
        if d[CATEGORY_ID]:
            d[CATEGORY] = trx.category.category
        else:
            d[CATEGORY] = None

        for suggested_spec in suggested_columns:
            scheme = suggested_spec['scheme']
            n_max = suggested_spec['n']

            # Get suggestions within this scheme
            categories_suggested = [category for category in trx.categories_suggested if category.scheme == scheme]

            if suggested_spec['order_by'] is None:
                pass
            elif suggested_spec['order_by'] == 'confidence':
                raise NotImplementedError("SORT BY CONFIDENCE!")

            for i in range(n_max):
                try:
                    d[f'{SUGGESTED_CATEGORY_PREFIX}_{scheme}_{i}'] = categories_suggested[i].category
                    d[f'{SUGGESTED_CATEGORY_PREFIX}_{scheme}_{i}{CATEGORY_ID_SUFFIX}'] = categories_suggested[i].id
                except IndexError:
                    d[f'{SUGGESTED_CATEGORY_PREFIX}_{scheme}_{i}'] = None
                    d[f'{SUGGESTED_CATEGORY_PREFIX}_{scheme}_{i}{CATEGORY_ID_SUFFIX}'] = None

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
            data=load_data(SUGGESTED_COLUMN_SPECS).to_dict('records'),
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
        returned = accept_category_on_click_via_active_cell(active_cell, data, SUGGESTED_COLUMNS_TO_WATCH)
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


def table_edit_callback(data, data_previous, changed_column=CHANGED_COLUMN):
    """
    Compares two dash table data entities, recording column that is different in row[changed_column]
    """
    # Determine where the change occurred
    diff = diff_dashtable(data, data_previous)

    # Special case: If category changed and category_id did not, delete the category_id.  Do this first so the logic for
    # recording changes in the second loop is shared (this callback should always see one or two differences at most, so
    # this overhead should be small)
    # We ignore the case of a category_id that changed without category changing because we expect category_id to be
    # an uneditable columns
    changed_category = set()
    changed_category_id = set()
    for d in diff:
        if d['column_name'] == CATEGORY:
            changed_category.add(d['index'])
        if d['column_name'] == CATEGORY_ID:
            changed_category_id.add(d['index'])

    # Delete any hanging category_id
    for i in changed_category - changed_category_id:
        diff.append({'index': i, 'column_name': CATEGORY_ID})
        data[i][CATEGORY_ID] = None
        diff.append({
            'index': i,
            "column_name": CATEGORY_ID,
            # Mock of diff object doesn't need these
            # "current_value": "IGNORED_NOT_RELEVANT",
            # "previous_value": "IGNORED_NOT_RELEVANT",
        })

    for d in diff:
        r_changed = d['index']
        c_changed = d['column_name']

        # If the column is empty it won't be in the dict.  Use .get to handle this with empty string as default
        # Current iteration can have duplicate changes noted here.  Remove or just handle when interpretting the column?
        data[r_changed][changed_column] = f"{data[r_changed].get(changed_column, '')} {CHANGED_PAD_START}{c_changed}{CHANGED_PAD_END}"

    return data


def accept_category_on_click_via_active_cell(active_cell, rows, columns_to_watch):
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
    if active_cell['column_id'] in columns_to_watch:
        source_column = active_cell['column_id']
        source_id_column = active_cell['column_id'] + CATEGORY_ID_SUFFIX

        # If cell is empty, ignore (we only overwrite if there is content to overwrite with)
        if not rows[active_cell['row']][source_column]:
            return None

        target_column = CATEGORY
        target_id_column = CATEGORY_ID

        # Check if destination already has this content
        if rows[active_cell['row']][target_column] == rows[active_cell['row']][source_column] or \
           rows[active_cell['row']][target_id_column] == rows[active_cell['row']][source_id_column]:
            return None
        else:
            # Make a deep copy of rows so we can later compare data to data_previous
            rows_previous = copy.deepcopy(rows)
            rows[active_cell['row']][target_column] = rows[active_cell['row']][source_column]
            rows[active_cell['row']][target_id_column] = rows[active_cell['row']][source_id_column]
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
