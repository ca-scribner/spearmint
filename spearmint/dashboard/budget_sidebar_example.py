import json
import operator
from functools import reduce
from typing import Union

import dash
import dash_html_components as html
from dash.dependencies import Input, Output, ALL, State

import dash_bootstrap_components as dbc

from spearmint.dashboard.budget_sidebar_elements import register_sidebar_list_click, \
    make_sidebar_ul, get_leaves_below_sidebar_obj, get_checked_leaves
from spearmint.services.budget import get_expense_budget_collection


fake_data = get_expense_budget_collection().categories_flat_dict
external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config['suppress_callback_exceptions'] = True


app.callback(
    Output("sidebar-ul", "children"),
    [Input({"type": "list_item", "id": ALL}, 'n_clicks'), ],
    [State("sidebar-ul", "children")]
)(register_sidebar_list_click)

@app.callback(
    Output("checked-items-p", "children"),
    [Input("sidebar-ul", "children")],
)
def watch_sidebar_children(ul_children):
    leaves = get_leaves_below_sidebar_obj(ul_children, path_to_obj=tuple())
    checked_leaves = get_checked_leaves(leaves)
    return ", ".join(checked_leaves)


# SIDEBAR_STYLE = {
#     "position": "fixed",
#     "top": 0,
#     "left": 0,
#     "bottom": 0,
#     "width": "16rem",
#     "padding": "2rem 1rem",
#     "background-color": "#f8f9fa",
# }

# Define the dash app layout
app.layout = html.Div([
    html.H1("Dash App with Sidebar using Dash Boostrap Components"),
    dbc.Container(
        [
            dbc.Row(
                children=[
                    dbc.Col(
                            children=html.Div([
                                make_sidebar_ul(fake_data, "Expenses")
                            ]),
                            id="sidebar-div",
                            # width=3,  # Static width
                            lg=3, md=4, xs=6,  # Responsive widths
                            # style=SIDEBAR_STYLE,
                            ),
                    dbc.Col(
                            children=[
                                 html.P(id="checked-items-p"),
                             ],
                            id='content-col',
                            lg=9, md=8, xs=6,
                    ),
                ],
                # no_gutters=True,
            ),
        ],
        fluid=True,  # Rows fill the entire width.  Otherwise I get a huge margin to the left of the sidebar
    ),
])


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
