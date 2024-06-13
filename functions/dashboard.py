import dash
import numpy as np
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
import numexpr as ne
import plotly.express as px
from db import PlantDataBase
import plotly.graph_objects as go


class DashApp:
    def __init__(self, db):
        self.db = db
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
        self.meta_all = db.query_all_metadata()
        self.dropdown_options = self.generate_dropdown_options()
        self.plot_config = {
            'displayModeBar': False
        }
        self.color_sequence = px.colors.qualitative.G10
        self.plot_template = 'plotly_white'
        self.create_layout()
        self.register_callbacks()

    def create_layout(self):
        self.app.layout = html.Div(
            style={'width': '100%', 'overflowX': 'hidden'},
            children=[
                dcc.Tabs(id='tabs', children=[
                    dcc.Tab(label='Univariate', children=[
                        self.create_layout_selection_row('univariate'),
                        dbc.Row([
                            dbc.Col([
                                dcc.Graph(id='line-graph', config=self.plot_config)
                            ], width=8),
                            dbc.Col([
                                dcc.Graph(id='avg-day-graph', config=self.plot_config)
                            ], width=4)
                        ]),
                        dbc.Row([
                            dcc.Graph(id='heatmap-graph', config=self.plot_config)
                        ])
                    ]),
                    dcc.Tab(label='Bivariate', children=[
                        self.create_layout_selection_row('bivariate'),
                        dbc.Row([
                            dbc.Col([
                                dcc.Graph(id='scatter-graph', config=self.plot_config)
                            ], width=4),
                            dbc.Col([
                                dbc.Row([
                                    dcc.Graph(id='bivariate-line-graph', config=self.plot_config)
                                ])
                            ], width=8)
                        ])
                    ]),
                    dcc.Tab(label='View and Delete Metadata', children=[
                        html.Div([
                            dash_table.DataTable(
                                style_table={
                                    'overflowX': 'auto', 'maxWidth': '99%', 'margin': 'auto', 'marginTop': '10px'
                                },
                                id='metadata-table',
                                columns=[{"name": i, "id": i} for i in self.meta_all.columns],
                                data=self.meta_all.to_dict('records'),
                                row_selectable='multi',
                                selected_rows=[],
                                page_size=25,
                                editable=False,
                                filter_action="native",
                                sort_action="native"
                            ),
                            html.Button('Delete Selected Rows', id='delete-button', n_clicks=0)
                        ])
                    ]),
                    dcc.Tab(label='Calculate', children=[
                        self.create_measurement_selection(),
                        html.Div(
                            id='calculate-selected',
                            style={'margin': '10px'}
                        ),
                        html.Hr(),
                        dbc.Row([
                            dbc.Col([
                                html.Label('Enter an expression using column names', style={'align': 'center'}),
                            ], width=3),
                            dbc.Col([
                                dcc.Input(
                                    id='calculate-expression',
                                    type='text',
                                    value='',
                                    placeholder='Enter expression here (e.g. (m_0 + m_1) * m_2)',
                                    style={'width': '100%'}
                                ),
                            ], width=4),
                            dbc.Col([
                                dcc.Input(
                                    id='calculate-start-date-input',
                                    type='text',
                                    placeholder='Enter preview start date (YYYY-MM-DD)',
                                    value='2023-01-01',
                                    style={'marginRight': '10px', 'width': '100%'}
                                )
                            ], width=2),
                            dbc.Col([
                                dcc.Input(
                                    id='calculate-end-date-input',
                                    type='text',
                                    placeholder='Enter preview end date (YYYY-MM-DD)',
                                    value='2023-03-01',
                                    style={'marginRight': '10px', 'width': '100%'}
                                )
                            ], width=2),
                            dbc.Col([
                                html.Button(
                                    'Calculate',
                                    id='calculate-button',
                                    style={'marginRight': '10px', 'width': '100%'}
                                ),
                            ], width=1)
                        ]),
                        dcc.Graph(id='output-plot', config=self.plot_config)
                    ])
                ])
            ]
        )

    def generate_dropdown_options(self):
        return [
            {
                'label': f"{row['object_description']} - {row['object_name']} \
                        ({row['unit']} | {row['start_date']} - {row['end_date']} | \
                        {row['msr']}.{row['msr_attribute']})",
                'value': row['series_id']
            }
            for index, row in self.meta_all.iterrows()
        ]

    def create_measurement_selection(self):
        return dbc.Row([
            dcc.Dropdown(
                id='calculate-measurement-dropdown',
                options=self.dropdown_options,
                value=self.meta_all['series_id'][0],
                multi=True
            )
        ])

    def create_layout_selection_row(self, graph_type):

        if graph_type == 'univariate':
            dropdowns = dbc.Row([
                dcc.Dropdown(
                    id='univariate-measurement-dropdown',
                    options=self.dropdown_options,
                    value=self.meta_all['series_id'][0]
                )
            ])
        elif graph_type == 'bivariate':
            dropdowns = dbc.Row([
                dcc.Dropdown(
                    id='bivariate-measurement-dropdown-1',
                    options=self.dropdown_options,
                    value=self.meta_all['series_id'][0]
                ),
                dcc.Dropdown(
                    id='bivariate-measurement-dropdown-2',
                    options=self.dropdown_options,
                    value=self.meta_all['series_id'][0]
                )
            ])
        else:
            raise ValueError('graph_type must be either univariate or bivariate')

        return dbc.Row([
            dbc.Col([
                dropdowns
            ], width=7),
            dbc.Col([
                dcc.Input(
                    id=f'{graph_type}-start-date-input',
                    type='text',
                    placeholder='Enter start date (YYYY-MM-DD)',
                    value='2023-01-01',
                    style={'marginRight': '10px', 'width': '100%'}
                )
            ], width=2),
            dbc.Col([
                dcc.Input(
                    id=f'{graph_type}-end-date-input',
                    type='text',
                    placeholder='Enter end date (YYYY-MM-DD)',
                    value='2023-03-01',
                    style={'marginRight': '10px', 'width': '100%'}
                )
            ], width=2),
            dbc.Col([
                html.Button('Update', id=f'{graph_type}-update-button')
            ], width=1)
        ])

    def register_callbacks(self):

        @self.app.callback(
            [
                Output('line-graph', 'figure'),
                Output('heatmap-graph', 'figure'),
                Output('avg-day-graph', 'figure'),
            ],
            [
                Input('univariate-measurement-dropdown', 'value'),
                Input('univariate-update-button', 'n_clicks')
            ],
            [
                State('univariate-start-date-input', 'value'),
                State('univariate-end-date-input', 'value')
            ]
        )
        def update_univariate_graphs(selected_measurement, n_clicks, start_date, end_date):
            meta_row, df, df_pivot = self.query_and_prepare_data(selected_measurement, start_date, end_date)

            line_graph = self.create_line_graph(df, meta_row)
            heatmap_graph = self.create_heatmap_graph(df_pivot)
            avg_day_graph = self.create_avg_day_graph(df, meta_row)

            return line_graph, heatmap_graph, avg_day_graph

        @self.app.callback(
            Output('calculate-selected', 'children'),
            Input('calculate-measurement-dropdown', 'value')
        )
        def update_calculate_selection(selected_measurements):
            df, meta = self.db.query_multiple(selected_measurements)

            selection_printout = []
            for _, row in meta.iterrows():
                selection_printout.append(
                    html.P([
                        html.Strong(html.Mark(row['name'])),
                        f": {row['object_description']} - {row['object_name']} \
                        ({row['unit']} | {row['start_date']} - {row['end_date']} | \
                        {row['msr']}.{row['msr_attribute']})"
                    ])
                )

            return selection_printout

        @self.app.callback(
            Output('output-plot', 'figure'),
            [
                Input('calculate-button', 'n_clicks')
            ],
            [
                State('calculate-measurement-dropdown', 'value'),
                State('calculate-expression', 'value'),
                State('calculate-start-date-input', 'value'),
                State('calculate-end-date-input', 'value')
            ]
        )
        def update_output_plot(n_clicks, selected_measurements, calculate_expression, start_date, end_date):
            df, meta = self.db.query_multiple(selected_measurements)
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

            try:
                df['calculated'] = ne.evaluate(calculate_expression, local_dict=df)
                fig = px.line(df, x='date', y='calculated')
                fig.update_layout(
                    template=self.plot_template,
                    xaxis_title='Date',
                    yaxis_title='Calculated Value',
                    showlegend=False
                )
            except Exception as e:
                fig = {
                    'data': [],
                    'layout': {
                        'title': 'Error',
                        'annotations': [{
                            'text': str(e),
                            'showarrow': False
                        }]
                    }
                }

            return fig

        @self.app.callback(
            [
                Output('scatter-graph', 'figure'),
                Output('bivariate-line-graph', 'figure')
            ],
            [
                Input('bivariate-measurement-dropdown-1', 'value'),
                Input('bivariate-measurement-dropdown-2', 'value'),
                Input('bivariate-update-button', 'n_clicks')
            ],
            [
                State('bivariate-start-date-input', 'value'),
                State('bivariate-end-date-input', 'value')
            ]
        )
        def update_multivariate_graphs(selected_measurement_1, selected_measurement_2, n_clicks, start_date, end_date):
            meta_rows, df = self.query_multiple_measurements(
                [selected_measurement_1, selected_measurement_2], start_date, end_date
            )

            scatter_graph = self.create_scatter_graph(df, meta_rows)
            line_graph = self.create_bivariate_line_graph(df, meta_rows)
            return [scatter_graph, line_graph]

        @self.app.callback(
            [
                Output('metadata-table', 'data'),
                Output('metadata-table', 'selected_rows'),
            ],
            Input('delete-button', 'n_clicks'),
            State('metadata-table', 'selected_rows'),
            State('metadata-table', 'data')
        )
        def delete_rows(n_clicks, selected_rows, rows):
            if n_clicks > 0:
                # Extract the series_ids of the selected rows
                selected_ids = [rows[i]['series_id'] for i in selected_rows]
                for series_id in selected_ids:
                    self.db.delete_measurements(series_id)

                # Refresh the data table
                self.meta_all = self.db.query_all_metadata()
                return self.meta_all.to_dict('records'), []
            return rows, []

        @self.app.callback(
            [
                Output('univariate-measurement-dropdown', 'options'),
                Output('bivariate-measurement-dropdown-1', 'options'),
                Output('bivariate-measurement-dropdown-2', 'options'),
                Output('calculate-measurement-dropdown', 'options')
            ],
            [
                Input('metadata-table', 'data')
            ]
        )
        def update_dropdown_options(data):
            options = self.generate_dropdown_options()
            return options, options, options, options

    def query_and_prepare_data(self, selected_measurement, start_date, end_date):
        meta_row = self.meta_all[self.meta_all['series_id'] == selected_measurement]
        df = self.db.query_data(selected_measurement, start_date, end_date)
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S')
        df['day'] = df['date'].dt.date
        df['hour'] = df['date'].dt.hour + df['date'].dt.minute / 60
        df_pivot = df.pivot_table(index=['hour'], columns=['day'], values='mean')

        return meta_row, df, df_pivot

    def query_multiple_measurements(self, selected_measurements, start_date, end_date):
        df = pd.DataFrame()
        meta_rows = pd.DataFrame()

        for i, selected_measurement in enumerate(selected_measurements):
            name = f"m_{i}"

            meta_row = self.meta_all[self.meta_all['series_id'] == selected_measurement].copy()
            m_df = self.db.query_data(selected_measurement, start_date, end_date)
            m_df['date'] = pd.to_datetime(m_df['date'], format='%Y-%m-%d %H:%M:%S')

            meta_row.loc[:, 'index'] = name
            meta_rows = pd.concat([meta_rows, meta_row])

            m_df.loc[:, name] = m_df['mean']
            if df.empty:
                df = m_df[['date', name]]
            else:
                df = pd.merge(df, m_df[['date', name]], on='date', how='outer')

        return meta_rows, df

    def create_avg_day_graph(self, df, meta_row):
        mean_day = df.groupby('hour')['mean'].mean()
        fig = px.line(mean_day, color_discrete_sequence=self.color_sequence)
        fig.update_layout(
            template=self.plot_template,
            xaxis_title='Hour',
            yaxis_title=f'Mean Value in {meta_row["unit"].values[0]}',
            showlegend=False
        )

        return fig

    def create_line_graph(self, df, meta_row):
        fig = px.line(df, x='date', y='mean', color_discrete_sequence=self.color_sequence)
        fig.update_layout(
            template=self.plot_template,
            xaxis_title='Date',
            yaxis_title=f'Value in {meta_row["unit"].values[0]}',
            showlegend=False
        )
        return fig

    def create_bivariate_line_graph(self, df, meta_rows):
        fig = go.Figure()

        for i, (index, row) in enumerate(meta_rows.iterrows()):
            secondary_y = i > 0

            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[row['index']],
                mode='lines',
                name=row['object_name'],
                yaxis='y2' if secondary_y else 'y1',
                line=dict(color=self.color_sequence[i % len(self.color_sequence)])
            ))

        fig.update_layout(
            template=self.plot_template,
            xaxis_title='Date',
            yaxis=dict(
                title=meta_rows.iloc[0]['object_name'] + ' (' + meta_rows.iloc[0]['unit'] + ')',
            ),
            yaxis2=dict(
                title=meta_rows.iloc[1]['object_name'] + ' (' + meta_rows.iloc[1]['unit'] + ')',
                overlaying='y',
                side='right'
            ),
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.2,
                xanchor='center',
                x=0.5
            )
        )

        return fig

    def create_heatmap_graph(self, df):
        fig = px.imshow(df, aspect='auto')
        fig.update_layout(
            template=self.plot_template,
            xaxis_title='Day',
            yaxis_title='Hour',
        )

        return fig

    def create_scatter_graph(self, df, meta_rows):
        first_row = meta_rows.iloc[0]
        second_row = meta_rows.iloc[1]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df[first_row['index']],
            y=df[second_row['index']],
            mode='markers',
            marker=dict(color=self.color_sequence[0])
        ))

        m, b = np.polyfit(df[first_row['index']], df[second_row['index']], 1)
        fig.add_trace(go.Scatter(
            x=df[first_row['index']],
            y=m * df[first_row['index']] + b,
            mode='lines',
            line=dict(color=self.color_sequence[1])
        ))

        fig.update_layout(
            template=self.plot_template,
            xaxis_title=f"{first_row['object_name']} ({first_row['unit']})",
            yaxis_title=f"{second_row['object_name']} ({second_row['unit']})",
            showlegend=False
        )

        return fig

    def run(self):
        self.app.run_server(debug=True)


if __name__ == '__main__':
    db = PlantDataBase('db/test.db')
    dash_app = DashApp(db)
    dash_app.run()
