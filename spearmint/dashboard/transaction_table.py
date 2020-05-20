import argparse
import copy
from pprint import pprint
import pandas as pd

import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import State, Input, Output
import dash_table

from spearmint.data.db_session import global_init
from spearmint.services.budget import get_expense_budget_collection
from spearmint.services.transaction import get_all_transactions


# Column to keep track of any edits in the table
CHANGED_COLUMN = "__changed"

# "unique" padding for start and end of each column specified in the changed column to make them more unique.  Otherwise
# if we had columns of "Product Description" and "Description", "Description" might get triggered by both
CHANGED_PAD_START = "__"
CHANGED_PAD_END = "__"

COLUMNS_TO_SHOW = ['id', 'datetime', 'amount', 'category', 'description']
COLUMNS_TO_EDIT = ['category']
COLUMN_DROPDOWNS = {
    # "category": {
    #     "options": [{"label": v, "value": v} for v in get_expense_budget_collection()]
    # }
}
COLUMNS_TO_HIDE = [CHANGED_COLUMN]

app = dash.Dash(__name__)


def define_columns(columns, editable):
    return [{"name": c, "id": c, "editable": c in editable} for c in columns]


def get_data(additional_columns):
    """
    Gets data from the db and adds any extra columns

    Args:
        additional_columns (list): List of string column names to add to the dataframe.  Useful for items that are
                                   on-screen but not in the database

    Returns:
        (dict): Returns the dataframe in df.to_dict('records') format
    """
    df = get_all_transactions('df')

    if additional_columns:
        for c in additional_columns:
            if c in df:
                raise ValueError(f"Column {c} already exists!  Cannot add hidden column that overlaps with main data")
            df[c] = None

    return df.to_dict('records')


def get_app_layout():
    children = [
        html.H1("Transaction Table"),
        dash_table.DataTable(
            id='transaction-table',
            columns=define_columns(columns=COLUMNS_TO_SHOW, editable=COLUMNS_TO_EDIT),
            data=get_data(additional_columns=COLUMNS_TO_HIDE),
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
