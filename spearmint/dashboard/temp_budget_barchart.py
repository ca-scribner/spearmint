import datetime

import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

from spearmint.data.db_session import global_init, create_session
from spearmint.services.transaction import get_all_transactions, get_transaction_categories

global_init("../../tests/manual/test.sqlite", echo=False)


MOVING_AVERAGE_SLIDER_TICKS = [1, 2, 3, 6, 12]

DATA = [
    ("2019-01-05 12:24:02", 15),
    ("2019-01-12 12:24:02", 20),
    ("2019-02-05 12:24:02", 12),
    ("2019-03-05 12:24:02", 10),
]
DATA = pd.DataFrame(DATA, columns=['x', 'y'])
DATA['x'] = pd.to_datetime(DATA['x'])

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

def monthly_bar(df, date_column='datetime', y_column='amount', budget=None, moving_average_window=None,
                start_date=None, end_date=None, fig=None, plot_burn_rate=False):

    if fig is None:
        fig = go.Figure()

    # Rearrange data into what we need
    df_monthly = df.groupby(pd.Grouper(key=date_column, freq='MS')).sum()

    if plot_burn_rate:
        df_daily = df.groupby(pd.Grouper(key=date_column, freq='d')).sum()
        # Get the cumulative daily sum, reset every month
        # No key because groupby by default moved datetime to index, and Grouper uses index as default key
        # Use .transform to return a series of the same shape as the input data so I can reincorporate into df_daily
        # ...I think I could leave it out and it would work here because pd.Series.cumsum returns the same shape anyway,
        # but this would also work for something like transform(pd.Series.sum)
        df_daily['cumsum'] = df_daily.groupby(pd.Grouper(freq='MS'))[y_column].transform(pd.Series.cumsum)

        # Make a column of the index for easier groupby
        df_daily[date_column] = df_daily.index

        # Make a datetime that is normalized/shifted to sit inside a bar chart bar
        # (bars are plotted centered on their date)
        df_daily[f'shifted_{date_column}'] = df_daily.groupby(pd.Grouper(freq="MS"))[date_column].transform(_date_shift)

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
    fig.update_xaxes(range=[start_date, end_date], dtick="M1")

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
            df_ma['delta'] = df_ma[y_column] - budget
            df_ma['overunder'] = df_ma.apply(lambda row: "under" if row.loc['delta'] > 0 else "over", axis=1)
            print(f"df_ma = {df_ma}")
            hovertext = df_ma.apply(lambda row: f"${row.loc[y_column]:.2f} (${abs(row.loc['delta']):.2f} {row.loc['overunder']} budget)", axis=1)
            print(f"hovertext (a)= {hovertext}")
            hovertext = hovertext.to_list()

            # hovertext = (df_ma[y_column] - budget).to_list(),
            # hovertext = []
            hoverinfo = "text"
        else:
            hoverinfo = "none",
            hovertext = ""

        def set_color(val):
            if val > budget:
                return "green"
            else:
                return "red"
        print(f"colorlist = {list(map(set_color, df_ma[y_column]))}")
        print(f"hovertext = {hovertext}")
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
                x=df_daily_this_month[f'shifted_{date_column}'],
                y=df_daily_this_month['cumsum'],
                showlegend=False,
                line=dict(
                    dash="dot",
                    color="black",
                    width=2,
                ),
            ))

    return fig


app.layout = html.Div(
    children=[
        html.H1(children="My plots"),
        html.Div(children="Some more text in a sub div"),
        dcc.RadioItems(id='monthly-hist-radio'),
        dcc.DatePickerRange(
            id='monthly-hist-date-range',
            start_date=pd.to_datetime("2020-02-01"),
            end_date=pd.to_datetime("2020-09-01"),
            # min_date_allowed=pd.to_datetime("2019-01-01"),
            # max_date_allowed=pd.to_datetime("2020-01-01"),  # Could set to real data range
            display_format="YYYY MMM DD",

        ),
        html.Hr(),
        html.Div(children="Plot burn rate"),
        dcc.RadioItems(
            id='monthly-hist-burn-rate-radio',
            options=[
                {'label': "Yes", 'value': 1},
                {'label': "No", 'value': 0},
            ],
            value=0,
            labelStyle={"display": "inline-block"}
        ),
        html.Hr(),
        # dcc.Slider(
        #     id="monthly-hist-ma-slider",
        #     min=1,
        #     max=12,
        #     step=None,
        #     marks={1: 1, 2: 2, 3: 3, 6: 6, 12: 12},
        #     value=3,
        # ),
        dcc.Slider(
            id="monthly-hist-ma-slider",
            min=1,
            max=12,
            step=None,
            marks={x: str(x) for x in MOVING_AVERAGE_SLIDER_TICKS},
            value=3
        ),
        html.Hr(),
        dcc.Graph(
            id='my-graph',
            # figure= \
            #         bar_with_ma(data, 'x', 'y', budget=4, ma=2)
            #     {
            #     'data': [
            #         {'x': data['x'], 'y': data['y'], 'type': 'bar', 'name': 'my data'},
            #         {'x': data['x'], 'y': data['y']+2, 'type': 'bar', 'name': 'my data + 2'},
            #         {'x': data['x'], 'y': data['y'], 'type': 'scatter', 'name': 'my data as scatter'},
            #         dict(type="line", xref="paper", x0=0, x1=1, yref="y", y0=13, y1=13, name="my line"),  # WHY DOESNT THIS SHOW ON SCREEN?
            #         dict(type="line", xref="x", x0=0, x1=5, yref="y", y0=13, y1=5, name="my other line"),
            #         dict(type="scatter", x=[1, 3], y=[5, 15], name="scatter by dict"),
            #         dict(type="line",
            #              xref="x",
            #              yref="y",
            #              x0=0,
            #              y0=0,
            #              x1=0.5,
            #              y1=0.5,
            #              name="line from interwebs"
            #              )
            #     ],
            #     'layout': {
            #         'title': "Figure title",
            #     }
            # }
        ),
        html.Button("Pull data from db", id="refresh-data-button", n_clicks=0),
    ]
)

@app.callback(Output("monthly-hist-radio", "options"),
              [Input("refresh-data-button", "n_clicks")]
              )
def update_monthly_hist_radio_options(n_clicks):
    categories = get_transaction_categories()
    options = [{"label": cat, "value": cat} for cat in categories]
    return options


@app.callback(Output("my-graph", "figure"),
              [Input("refresh-data-button", "n_clicks"),
               Input("monthly-hist-radio", "value"),
               Input('monthly-hist-date-range', "start_date"),
               Input('monthly-hist-date-range', "end_date"),
               Input("monthly-hist-ma-slider", "value"),
               Input("monthly-hist-burn-rate-radio", "value"),
               ],
              )
def update_figure_using_button(n_clicks, category, start_date, end_date, ma, plot_burn_rate):
    df = get_all_transactions('df')

    df = df.loc[df["category"] == category]

    fig = monthly_bar(df,
                      date_column='datetime',
                      y_column='amount',
                      budget=-1100,
                      moving_average_window=ma,
                      start_date=start_date,
                      end_date=end_date,
                      plot_burn_rate=plot_burn_rate,
                      )
    # fig = monthly_bar_old(df_grouped, 'datetime', 'amount', moving_average_window=ma)
    return fig


# Helpers
def _date_shift(ds, scale_factor=0.8):
    """
    Scales/shifts a date Series such that dates are shifted ~1/2 month back and scaled so each month is * scale factor)
    """
    # Shift +1 second so that MonthBegin of the very first date in a month isn't pushed to the previous month
    month_begin = ds + datetime.timedelta(1) + pd.offsets.MonthBegin(-1)
    month_end = ds + pd.offsets.MonthEnd(0)

    # Make a start date that is shifted half of a scaled month to the left of the beginning of this month
    reference_start = -((month_end - month_begin) * scale_factor / 2) + month_begin
    # Compute the date relative to a month start
    relative_date = (ds - month_begin) * scale_factor
    return relative_date + reference_start




if __name__ == '__main__':
    app.run_server(debug=True)
