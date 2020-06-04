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
from spearmint.data.category import Category
from spearmint.data.db_session import global_init, create_session
from spearmint.data.transaction import Transaction
from spearmint.services.budget import get_expense_budget_collection, get_income_budget_collection, \
    get_excluded_budget_collection, get_unbudgeted_categories
from spearmint.services.category import get_category_by_id
from spearmint.services.transaction import get_transactions, get_transactions_by_id, \
    get_unique_transaction_categories_as_string

SUGGESTED_CATEGORY_PREFIX = "(S)"
CATEGORY = "category"
CATEGORY_ID_SUFFIX = " id"
CATEGORY_ID = CATEGORY + CATEGORY_ID_SUFFIX
DATETIME = "datetime"
DESCRIPTION = "description"
RELOAD_BUTTON = "reload-data-button"
RELOAD_BUTTON_CONFIRM = "reload-data-button-confirm"
SAVE_TO_DB_BUTTON_CONFIRM = "save-to-db-button-confirm"
TRANSACTION_TABLE = "transaction-table"

# Column to keep track of any edits in the table
CHANGED_COLUMN = "__changed"

# "unique" padding for start and end of each column specified in the changed column to make them more unique.  Otherwise
# if we had columns of "Product Description" and "Description", "Description" might get triggered by both
CHANGED_DELIMINATOR = "_|_"


# TODO: Simplify the suggested category naming stuff once we're done debugging
def get_suggested_column_name(spec, i=None):
    if i is None:
        suffix = ""
    else:
        suffix = f" {i}"
    return f"{spec['name']}{suffix}"


def get_suggested_column_names(spec, id_suffix=None):
    if id_suffix is None:
        suffix = ""
    else:
        suffix = f"{id_suffix}"

    if spec["n"] == 1:
        column_indices = [None]
    else:
        column_indices = range(spec["n"])

    return [f"{get_suggested_column_name(spec, i)}{suffix}" for i in column_indices]


def get_suggested_column_names_with_id_interleaved(spec, id_suffix):
    """
    Returns an interleaved list of suggested column names for this spec without and with ID

    For example:
        get_suggested_column_names_with_id_interleaved(
            spec={'name': 'suggested_from_file', 'scheme': 'from_file', 'n': 2},
            id_suffix="_id"
        )
        # returns:
        # ["suggested_from_file 0", "suggested_from_file 0_id", "suggested_from_file 1", "suggested_from_file 1_id"]
    """
    return interleave(get_suggested_column_names(spec), get_suggested_column_names(spec, id_suffix=id_suffix))


def interleave(l1, l2):
    return list(itertools.chain(*zip(l1, l2)))


def flatten(lst):
    return list(itertools.chain(*lst))


SUGGESTED_COLUMN_SPECS = [
    {'name': f'{SUGGESTED_CATEGORY_PREFIX} most_common', 'scheme': 'most_common', 'n': 2, 'order_by': None},
    {'name': f'{SUGGESTED_CATEGORY_PREFIX} rf', 'scheme': 'rf', 'n': 1, 'order_by': None},
    {'name': f'{SUGGESTED_CATEGORY_PREFIX} from_file', 'scheme': 'from_file', 'n': 1, 'order_by': None},
    # {'name': f'{SUGGESTED_CATEGORY_PREFIX} clf', 'scheme': 'clf', 'n': 1, 'order_by': None},
]

# SUGGESTED_COLUMNS_TO_SHOW = [get_suggested_column_names_with_id_interleaved(spec=spec, id_suffix=CATEGORY_ID_SUFFIX)
#                              for spec in SUGGESTED_COLUMN_SPECS]
SUGGESTED_COLUMNS_TO_SHOW = flatten([get_suggested_column_names(spec=spec)
                                     for spec in SUGGESTED_COLUMN_SPECS])

SUGGESTED_COLUMNS_TO_WATCH_FOR_ON_CLICK = flatten([get_suggested_column_names(spec=spec)
                                                   for spec in SUGGESTED_COLUMN_SPECS])

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

show_hidden_columns = False
COLUMNS_TO_SHOW = COLUMNS_TO_SHOW_FROM_DATA + ADDITIONAL_COLUMNS_TO_SHOW
if show_hidden_columns:
    COLUMNS_TO_SHOW += COLUMNS_TO_HIDE


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

            # Get suggestions within this scheme
            categories_suggested = [category for category in trx.categories_suggested if category.scheme == scheme]

            if suggested_spec['order_by'] is None:
                pass
            elif suggested_spec['order_by'] == 'confidence':
                raise NotImplementedError("SORT BY CONFIDENCE!")

            suggested_names = get_suggested_column_names(suggested_spec)
            suggested_names_with_id = get_suggested_column_names(suggested_spec, CATEGORY_ID_SUFFIX)

            for i, (name, name_with_id) in enumerate(zip(suggested_names, suggested_names_with_id)):
                try:
                    d[name] = categories_suggested[i].category
                    d[name_with_id] = categories_suggested[i].id
                except IndexError:
                    d[name] = None
                    d[name_with_id] = None

        return d

    trxs_as_dicts = [trx_to_dict(trx) for trx in trxs]
    df = pd.DataFrame(trxs_as_dicts)

    # Reformat dates to nicer display
    df[DATETIME] = pd.DatetimeIndex(df[DATETIME]).strftime("%Y-%m-%d")

    for c in ADDITIONAL_COLUMNS_TO_SHOW + COLUMNS_TO_HIDE:
        if c in df:
            raise ValueError(f"Column {c} already exists!  Cannot add hidden column that overlaps with main data")
        df[c] = None

    return df


def load_unbudgeted_categories():
    all_categories = get_unique_transaction_categories_as_string(category_type='accepted')
    return get_unbudgeted_categories(all_categories)


def get_conditional_styles():
    # Styling priority, from highest to lowest (from https://dash.plotly.com/datatable/style)
    #     1. style_data_conditional
    #     2. style_data
    #     3. style_filter_conditional
    #     4. style_filter
    #     5. style_header_conditional  # header = only header
    #     6. style_header
    #     7. style_cell_conditional  # cell = header and data
    #     8. style_cell
    #
    # From https://dash.plotly.com/datatable/style
    #     Notice the three different groups you can style: "cell" is the whole table, "header" is just the header rows,
    #     and "data" is just the data rows. To use even/odd or other styling based on row_index you must use
    #     style_data_conditional.

    style_cell_conditional = []
    style_data_conditional = []
    style_filter_conditional = []
    style_header_conditional = []

    # Styling for editable
    style_data_conditional.append({
        "if": {"column_editable": True},
        "backgroundColor": "rgb(96, 190, 247)",
    })
    style_header_conditional.append({
        "if": {"column_editable": True},
        "backgroundColor": "rgb(96, 190, 247)",
    })

    # Color if category column is empty
    style_data_conditional.append(
        {
            "if": {
                "filter_query": f"{{{CATEGORY}}} is blank",
                "column_id": CATEGORY,
            },
            "backgroundColor": "rgb(255, 0, 0)",

        }
    )


    # Styling for clickable columns
    for c in SUGGESTED_COLUMNS_TO_WATCH_FOR_ON_CLICK:
        style_data_conditional.append(
            {
                "if": {"column_id": c},
                "backgroundColor": "rgb(195, 247, 188)",
                'border': '1px solid blue'
            }
        )

    # Style any editable column that has changed
    for c in COLUMNS_TO_EDIT:
        style_data_conditional.append(
            {
                "if": {
                    "filter_query": f"{{{CHANGED_COLUMN}}} contains {CHANGED_DELIMINATOR}{c}",
                    "column_id": c,
                },
                "backgroundColor": "rgb(250, 140, 0)",
            }
        )

    # Not sure why, but this only worked after the DataTable's style_cell had
    # {"overflow": "hidden", "textOverflow": "ellipsis", "maxWidth": 50},
    # style_cell_conditional.append(
    #     {"if": {"column_id": "id"},
    #      "width": "50%",
    #      }
    # )


    return {
        'style_data_conditional': style_data_conditional,
        'style_filter_conditional': style_filter_conditional,
        'style_header_conditional': style_header_conditional,
        'style_cell_conditional': style_cell_conditional,
    }


def get_app_layout(db_file):
    data = load_data(SUGGESTED_COLUMN_SPECS)
    children = [
        html.H1("Transaction Table"),
        html.Div([
            html.Button("Reload Data", id=RELOAD_BUTTON),
            dcc.ConfirmDialogProvider(
                children=html.Button("Save Changes to DB"),
                id=SAVE_TO_DB_BUTTON_CONFIRM,
                message="Are you sure you want to save changes to the database?"
            ),
        ]),
        dash_table.DataTable(
            id=TRANSACTION_TABLE,
            columns=define_columns(columns=COLUMNS_TO_SHOW, editable=COLUMNS_TO_EDIT),
            data=data.to_dict('records'),
            editable=True,
            # Set dropdowns within columns by dict
            dropdown=COLUMN_DROPDOWNS,
            # style_cell={"textOverflow": "ellipsis"},
            # style_cell={'whiteSpace': 'normal', "textOverflow": "ellipsis",
            #             "minWidth": "5px", "width": "10px", "maxWidth": "1500px", "table-layout": "fixed"},
            tooltip_data=get_tooltip_data(data),
            style_cell={"overflow": "hidden", "textOverflow": "ellipsis", "maxWidth": 300},
            style_header={"whiteSpace": "normal", "height": "auto"},
            style_table={'height': '75vh', 'overflowY': 'auto'},
            **get_conditional_styles(),
            page_action="native",
            page_size=25,
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            sort_by=[{'column_id': DATETIME, 'direction': 'desc'}]
            # row_selectable="multi",  # Can I use this to indicate changes cleanly and only pass rows that need change?
        ),
        # Intermediate trigger if reload button confirmed
        html.Div(
            id="hidden_stuff",
            children=[
                dcc.ConfirmDialog(
                    id=RELOAD_BUTTON_CONFIRM,
                    message="Unsaved changes detected - are you sure you want to reload from the database?"
                ),
                html.Div(
                    id="db-file",
                    children=db_file,
                ),
            ],
            style={'display': 'none'}
        ),
        html.Div(
            children=[
                html.H2("Income Categories:"),
                html.Ul(
                    id="income-categories-list",
                    children=categories_to_children_string(get_income_budget_collection().categories),
                ),
                html.H2("Expense Categories:"),
                html.Ul(
                    id="expense-categories-list",
                    children=categories_to_children_string(get_expense_budget_collection().categories),
                ),
                html.H2("Excluded Categories:"),
                html.Ul(
                    id="excluded-categories-list",
                    children=categories_to_children_string(get_excluded_budget_collection().categories),
                ),
                html.H2("Unbudgeted Categories:"),
                html.Ul(
                    id="unbudgeted-categories-list",
                    children=categories_to_children_string(load_unbudgeted_categories()),
                ),
            ]
        )
    ]

    return html.Div(children)


def categories_to_children_string(categories):
    categories = sorted(categories)
    return f" {CHANGED_DELIMINATOR} ".join(categories)


def get_tooltip_data(data):
    return [
        {
            column: {'value': str(value), 'type': 'markdown'}
            for column, value in row.items() if column == DESCRIPTION
        } for row in data.to_dict('rows')
    ]


# Callbacks
@app.callback(
    Output(RELOAD_BUTTON_CONFIRM, "displayed"),
    [
        Input(RELOAD_BUTTON, "n_clicks"),
    ],
    [
        State(TRANSACTION_TABLE, "data"),
    ]
)
def reload_button(n_clicks, data):
    changed_rows = _get_changed_rows(data)
    return len(changed_rows) > 0


@app.callback(
    Output("unbudgeted-categories-list", "children"),
    [
        Input(TRANSACTION_TABLE, "data")
    ]
)
def update_unbudgeted_categories_shown(data):
    accepted_categories = set(d[CATEGORY] for d in data)
    unbudgeted_categories = get_unbudgeted_categories(accepted_categories)
    return categories_to_children_string(unbudgeted_categories)

@app.callback(
    Output(TRANSACTION_TABLE, "data"),
    [Input(TRANSACTION_TABLE, "data_timestamp"),
     Input(TRANSACTION_TABLE, "active_cell"),
     Input(RELOAD_BUTTON_CONFIRM, "submit_n_clicks"),
     Input(SAVE_TO_DB_BUTTON_CONFIRM, "submit_n_clicks"),
     ],
    [State(TRANSACTION_TABLE, "data"),
     State(TRANSACTION_TABLE, "data_previous"),
     ]
)
def table_data_update_dispatcher(data_timestamp, active_cell, reload_button_confirm, save_to_db_button_confirm, data,
                                 data_previous):
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

    # If we have a Refresh Data button callback, reload the data from the db and exit
    if RELOAD_BUTTON_CONFIRM in ctx.triggered[0]["prop_id"]:
        return load_data(SUGGESTED_COLUMN_SPECS).to_dict("records")

    # Save changes to db, clear the changes, and exit
    if SAVE_TO_DB_BUTTON_CONFIRM in ctx.triggered[0]["prop_id"]:
        _save_changes_to_db(data)

        # Reload new db data
        return load_data(SUGGESTED_COLUMN_SPECS).to_dict("records")

    data_edited = False

    # We have both callbacks that can cause edits (click here and change data somewhere else) and callbacks that react
    # to data changes (see a change in the table and possibly enact another change).  If we want the former to trigger
    # the latter, we need to do it ourselves (the callback wont trigger automatically, and if it did we'd have an
    # infinite loop)

    # These are logic branches that can result in edited data.  If we want them to trigger the later "on-edit" callback,
    # raise the data_edited flag
    if ctx.triggered[0]["prop_id"].endswith(".active_cell"):
        returned = accept_category_on_click_via_active_cell(active_cell, data, SUGGESTED_COLUMNS_TO_WATCH_FOR_ON_CLICK)
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


def _save_changes_to_db(data):
    changes = _get_changed_rows(data)
    if len(changes) == 0:
        raise dash.exceptions.PreventUpdate("No changes to save")
    trx_ids = [c['id'] for c in changes]
    trxs = get_transactions_by_id(ids=trx_ids)
    for c, trx in zip(changes, trxs):
        these_changes = _get_changed_columns(c[CHANGED_COLUMN])

        if these_changes != set([CATEGORY, CATEGORY_ID]):
            raise ValueError("Invalid change - only changes to category column supported")

        if c[CATEGORY] is None:
            # Manually deleted category.  Remove existing accepted category and move on
            trx.category = None
            # trx.category_id = None  # This should be redundant
        elif c[CATEGORY_ID] is None:
            # Manually entered - create new Category and attach
            category = Category(scheme='manual', category=c[CATEGORY])
            trx.category = category
        else:
            # Accepted a suggestion.  Reuse this category by attaching to .category.
            category = get_category_by_id(id=c[CATEGORY_ID])
            trx.category = category
    # To commit these objects, which came from a different session that I no longer have, merge them into a new
    # session. (from https://stackoverflow.com/a/47663833/5394584)
    # Is there a better pattern I could use for passing objects that avoids this?  Start here if current solution
    # gives problems:
    # https://stackoverflow.com/questions/48218065/programmingerror-sqlite-objects-created-in-a-thread-can-only-be-used-in-that-sa
    s = create_session()
    trxs_to_commit = [s.merge(trx) for trx in trxs]
    s.add_all(trxs_to_commit)
    s.commit()
    s.close()


def _get_changed_columns(changed_column_entry: str) -> set:
    """
    Returns a set of column names for the columns that have changed according to changed_column_entry

    This is used to interrogate the CHANGED column in the table

    Args:
        changed_column_entry (str): String denoting columns changed in a row of the table

    Returns:
        (set): Set of column names that changed
    """
    # We only process changes that happen to the category column
    these_changes = [change_col.strip() for change_col in changed_column_entry.split(CHANGED_DELIMINATOR)]
    # Remove repeated values (whether a column changed more than once doesn't matter to us)
    these_changes = set(these_changes)
    # Remove None, which can get in there from time to time but is not a valid column...
    these_changes = these_changes - {None, 'None'}
    return these_changes


def _get_changed_rows(data):
    """
    Returns data rows with non-empty CHANGED_COLUMN

    Args:
        data (list):  List of dicts of data

    Returns:
        list of references to the dicts of data that have changed
    """
    return [row for row in data if row.get(CHANGED_COLUMN, None)]


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
        data[r_changed][changed_column] = f"{data[r_changed].get(changed_column, '')} {CHANGED_DELIMINATOR}{c_changed}"

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
        this_row = _get_active_row(active_cell, rows)

        source_column = active_cell['column_id']
        source_id_column = active_cell['column_id'] + CATEGORY_ID_SUFFIX

        # If cell is empty, ignore (we only overwrite if there is content to overwrite with)
        if not this_row[source_column]:
            return None

        target_column = CATEGORY
        target_id_column = CATEGORY_ID

        # Check if destination already has this content
        if this_row[target_column] == this_row[source_column] or \
           this_row[target_id_column] == this_row[source_id_column]:
            return None
        else:
            # Make a deep copy of rows so we can later compare data to data_previous
            rows_previous = copy.deepcopy(rows)
            this_row[target_column] = this_row[source_column]
            this_row[target_id_column] = this_row[source_id_column]
            return rows, rows_previous, True

    # No edits
    return None


def _get_active_row(active_cell, rows):
    # Get the row we're working on by finding the correct row_id (nomenclature is id in the data, but row_id in
    # active_cell)
    # Use a generator expression to yield the first matching element
    this_row = next((d for d in rows if d['id'] == active_cell['row_id']), None)
    if this_row == None:
        raise ValueError("Cannot find active row")
    return this_row




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

    app.layout = get_app_layout(db_file=args.db)
    ports = range(8850, 8860, 1)
    for port in ports:
        try:
            print(f"TRYING PORT {port}")
            app.run_server(debug=True, port=port)
        except OSError:
            continue
        break
