import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import pickle

from data_loader import get_dashboard_data

# ==============================================================================
# DATA INITIALIZATION
# ==============================================================================
CACHE_FILE = "processed_data.pkl"
if os.path.exists(CACHE_FILE) and os.environ.get("REGENERATE_CACHE") != "1":
    print("Loading cached data...")
    with open(CACHE_FILE, "rb") as f:
        data_cache = pickle.load(f)
else:
    print("Processing data from scratch. This may take a few seconds...")
    data_cache = get_dashboard_data()
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data_cache, f)

# Colors for activities
COLORS = {
    "Sleeping": "#2c3e50", "Work": "#e74c3c", "Eating": "#f1c40f", 
    "Housework": "#34495e", "Travelling": "#9b59b6", "Personal care": "#e67e22",
    "Caring": "#1abc9c", "Education": "#3498db", "Sport": "#2ecc71",
    "TV/Online videos": "#ff7979", "Passive leisure": "#badc58", 
    "Active leisure": "#22a6b3", "Outdoor activities": "#f6e58d",
    "Sell goods or provide services": "#dff9fb", "Relaxing": "#c7ecee",
    "Shopping": "#e84393", "Others": "#bdc3c7"
}

# Standardized activity definitions
ACTIVITY_DEFINITIONS = {
    "Sleeping": "Nighttime sleep, naps, essential rest, and resting during illness.",
    "Work": "Main or secondary paid employment, farming, business operations, telework, overtime, and work-related duties.",
    "Eating": "Consuming meals, snacks, and beverages at home, work, or dining establishments.",
    "Housework": "Cooking, meal preparation, indoor/outdoor cleaning, laundry, ironing, home repairs, and household organization.",
    "Travelling": "Commuting to/from work, school, shopping, socializing, appointments, or errands via transit, car, bicycle, or walking.",
    "Personal care": "Bathing, grooming, dressing, personal hygiene, and private health/medical self-care.",
    "Caring": "Caring for children (feeding, playing, homework assistance) and eldercare or assisting sick/disabled family members.",
    "Education": "Attending school/university lectures, studying, completing homework, taking courses, and educational training.",
    "Sport": "Physical exercise, workouts, gym, competitive sports, running, cycling, swimming, and fitness activities.",
    "TV/Online videos": "Watching broadcast television, cable, streaming platforms (e.g., Netflix, YouTube), and movies.",
    "Passive leisure": "Reading books, magazines, or news; listening to music or podcasts; and casual social media browsing.",
    "Active leisure": "Video gaming, hobbies, artistic activities, crafts, playing musical instruments, and attending social events.",
    "Outdoor activities": "Walking, hiking, gardening, spending time in nature, parks, and outdoor recreational spaces.",
    "Sell goods or provide services": "Informal commerce, market sales, retail selling, street vending, and independent client services.",
    "Relaxing": "Meditating, resting awake, quiet contemplation, daydreaming, and intentional unstructured downtime.",
    "Shopping": "Purchasing groceries, food, clothing, household goods, personal items, and online shopping.",
    "Others": "Unclassified, unspecified, or miscellaneous diary entries not fitting other standardized categories."
}

# ==============================================================================
# CHART GENERATORS
# ==============================================================================

def create_base_layout(title=""):
    return dict(
        margin=dict(l=40, r=20, t=30, b=0),
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.1),
            type="date",
            showgrid=False,
            tickformat="%H:%M",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1.5,
            spikedash="dot",
            spikecolor="#e74c3c"
        ),
        yaxis=dict(range=[0, 100], showgrid=True),
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        autosize=True,
        shapes=[
            dict(
                type="line",
                x0="2022-01-01 00:00:00",
                x1="2022-01-01 00:00:00",
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")
            )
        ]
    )

def plot_stacked_area(fig, df, row=None, col=None):
    for act in df.columns:
        if act in COLORS:
            trace = go.Scatter(
                x=df.index, y=df[act],
                name=act, mode='lines',
                line=dict(width=0.5, color=COLORS[act]),
                stackgroup='one',
                hovertemplate='<b>%{fullData.name}</b>: %{y:.1f}%<extra></extra>'
            )
            if row and col:
                fig.add_trace(trace, row=row, col=col)
            else:
                fig.add_trace(trace)

def create_overview_chart(df):
    fig = go.Figure()
    plot_stacked_area(fig, df)
    fig.update_layout(**create_base_layout())
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100])
    return fig

def create_gender_chart(df_dict):
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05, subplot_titles=("Male", "Female"))
    plot_stacked_area(fig, df_dict[('Male',)], row=1, col=1)
    plot_stacked_area(fig, df_dict[('Female',)], row=1, col=2)
    layout = create_base_layout()
    layout['shapes'] = [
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=1, xref="x", yref="paper", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")),
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=1, xref="x2", yref="paper", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot"))
    ]
    fig.update_layout(**layout)
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(xaxis_rangeslider=dict(visible=True, thickness=0.05), 
                      xaxis2_rangeslider=dict(visible=True, thickness=0.05))
    return fig

def create_age_chart(df_dict):
    fig = make_subplots(rows=2, cols=2, shared_yaxes=True, shared_xaxes=True, 
                        vertical_spacing=0.08, horizontal_spacing=0.05,
                        subplot_titles=("15-34", "35-54", "55-64", "65+"))
    plot_stacked_area(fig, df_dict[('15 to 34 years',)], row=1, col=1)
    plot_stacked_area(fig, df_dict[('35 to 54 years',)], row=1, col=2)
    plot_stacked_area(fig, df_dict[('55 to 64 years',)], row=2, col=1)
    
    has_65 = not df_dict[('65 years and over',)].empty and df_dict[('65 years and over',)].sum().sum() > 0
    if has_65:
        plot_stacked_area(fig, df_dict[('65 years and over',)], row=2, col=2)
        
    layout = create_base_layout()
    layout['shapes'] = [
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=1, xref="x", yref="paper", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")),
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=1, xref="x2", yref="paper", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")),
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=1, xref="x3", yref="paper", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")),
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=1, xref="x4", yref="paper", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot"))
    ]
    fig.update_layout(**layout)
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100])
    
    fig.update_layout(xaxis_rangeslider_visible=False, xaxis3_rangeslider=dict(visible=True, thickness=0.05))
    if has_65:
        fig.update_layout(xaxis2_rangeslider_visible=False, xaxis4_rangeslider=dict(visible=True, thickness=0.05))
    else:
        fig.update_layout(xaxis4_visible=False, yaxis4_visible=False)
        fig.update_layout(xaxis2_rangeslider=dict(visible=True, thickness=0.05))
        for ann in fig.layout.annotations:
            if ann.text == "65+":
                ann.text = ""
                
    return fig

def create_isolated_chart(df_main, df_other, activity, compare_mode, is_ca):
    fig = go.Figure()
    
    if compare_mode == "separate":
        fig.add_trace(go.Scatter(
            x=df_main.index, y=df_main[activity],
            name=activity, mode='lines',
            line=dict(color=COLORS.get(activity, '#000')),
            fill='tozeroy', fillcolor=COLORS.get(activity, '#000'),
            opacity=0.6, hovertemplate='<b>%{fullData.name}</b>: %{y:.1f}%<extra></extra>'
        ))
    else:
        main_name = "Canada" if is_ca else "Vietnam"
        other_name = "Vietnam" if is_ca else "Canada"
        
        y_main = df_main[activity].values
        y_other = df_other[activity].values
        x_vals = df_main.index
        
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_other, name=f"{other_name} ({activity})",
            mode='lines', line=dict(color='gray', width=2),
            hovertemplate='<b>%{fullData.name}</b>: %{y:.1f}%<extra></extra>'
        ))
        
        pos_y = np.where(y_main >= y_other, y_main, y_other)
        neg_y = np.where(y_main < y_other, y_main, y_other)

        fig.add_trace(go.Scatter(x=x_vals, y=y_other, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(
            x=x_vals, y=pos_y, fill='tonexty', fillcolor='rgba(46, 204, 113, 0.4)', 
            mode='lines', line=dict(width=0), name="Higher", hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(x=x_vals, y=y_other, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(
            x=x_vals, y=neg_y, fill='tonexty', fillcolor='rgba(231, 76, 60, 0.4)', 
            mode='lines', line=dict(width=0), name="Lower", hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_main, name=f"{main_name} ({activity})",
            mode='lines', line=dict(color=COLORS.get(activity, '#000'), width=3),
            hovertemplate='<b>%{fullData.name}</b>: %{y:.1f}%<extra></extra>'
        ))

    fig.update_layout(**create_base_layout())
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100])
    return fig

def create_surprise_chart(df, country_name):
    """ Animated horizontal bar chart showing top 5 activities for country_name over the 24h timeline """
    times = df.index[::15]
    top_n = 5
    
    tops = [df.loc[t].sort_values(ascending=True).tail(top_n) for t in times]
    
    frames = []
    for i, t in enumerate(times):
        row = tops[i]
        acts = list(row.index)
        vals = list(row.values)
        colors = [COLORS.get(a, '#3498db') for a in acts]
        texts = [f" {a} ({v:.1f}%)" for a, v in zip(acts, vals)]
        
        frames.append(go.Frame(
            data=[go.Bar(
                x=vals,
                y=acts,
                orientation='h',
                marker=dict(color=colors, line=dict(color='white', width=1)),
                text=texts,
                textposition='auto',
                textfont=dict(size=11),
                hovertemplate='<b>%{y}</b>: %{x:.1f}%<extra></extra>'
            )],
            name=t.strftime("%H:%M")
        ))
        
    initial_row = tops[0]
    initial_acts = list(initial_row.index)
    initial_vals = list(initial_row.values)
    initial_colors = [COLORS.get(a, '#3498db') for a in initial_acts]
    initial_texts = [f" {a} ({v:.1f}%)" for a, v in zip(initial_acts, initial_vals)]
    
    fig = go.Figure(
        data=[go.Bar(
            x=initial_vals,
            y=initial_acts,
            orientation='h',
            marker=dict(color=initial_colors, line=dict(color='white', width=1)),
            text=initial_texts,
            textposition='auto',
            textfont=dict(size=11),
            hovertemplate='<b>%{y}</b>: %{x:.1f}%<extra></extra>'
        )],
        layout=go.Layout(
            title=dict(text=f"Top 5 Activities in {country_name}", font=dict(size=14, color="#2c3e50")),
            xaxis=dict(range=[0, 100], title="Share of Population (%)", showgrid=True),
            yaxis=dict(showgrid=False),
            margin=dict(l=110, r=20, t=40, b=60),
            plot_bgcolor="white",
            paper_bgcolor="white",
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                x=0.0, y=-0.22,
                xanchor="left", yanchor="top",
                buttons=[
                    dict(label="▶ Play", method="animate", args=[None, dict(frame=dict(duration=150, redraw=True), fromcurrent=True, transition=dict(duration=50))]),
                    dict(label="⏸ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])
                ]
            )],
            sliders=[dict(
                active=0,
                x=0.22, y=-0.22,
                len=0.76,
                xanchor="left", yanchor="top",
                currentvalue=dict(prefix="Time: ", font=dict(size=12, color="#2c3e50"), visible=True),
                steps=[dict(method='animate', args=[[f.name], dict(mode='immediate', frame=dict(duration=100, redraw=True))], label=f.name) for f in frames]
            )]
        ),
        frames=frames
    )
    return fig

# ==============================================================================
# DASH APP
# ==============================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
app.title = "Time Use Dashboard"

# Ensure precise fit to screen & responsive layout
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            html, body { margin: 0; padding: 0; height: 100vh; overflow: hidden; background-color: #ecf0f1; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            #react-entry-point { height: 100%; display: flex; flex-direction: column; }
            .card { height: 100%; display: flex; flex-direction: column; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-radius: 8px;}
            .card-body { flex-grow: 1; padding: 10px; display: flex; flex-direction: column; min-height: 0; }
            .graph-container { flex-grow: 1; min-height: 0; position: relative; }
            .legend-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 5px; padding: 5px; max-height: 80px; overflow-y: auto;}
            .legend-btn { font-size: 0.75rem; padding: 2px 6px; border: none; border-radius: 12px; cursor: pointer; color: white;}
            .main-row { height: calc(100vh - 60px); margin: 0; padding: 10px; }
            .col-card { height: 100%; padding: 5px; }
            .card-header-title { white-space: nowrap !important; overflow: hidden; text-overflow: ellipsis; }
            .btn-compact { white-space: nowrap !important; }
            @media (max-width: 767px) {
                .main-row { flex-direction: column; height: auto !important; overflow-y: auto; }
                .col-card { height: 500px !important; margin-bottom: 15px; }
                .legend-container { display: none !important; }
                .hovertext text { font-size: 10px !important; }
                html, body { overflow: auto !important; height: auto !important; }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
'''

# Navbar
navbar = dbc.Navbar(
    dbc.Container([
        html.Div([
            dbc.Tabs(
                id="view-tabs",
                active_tab="overview",
                children=[
                    dbc.Tab(label="Overview", tab_id="overview"),
                    dbc.Tab(label="By Gender", tab_id="gender"),
                    dbc.Tab(label="By Age", tab_id="age"),
                ],
                className="me-2"
            ),
            dbc.Button("Surprise Chart", id="btn-surprise", outline=True, color="light", size="sm", className="me-3 rounded-pill"),
            dbc.Select(
                id="hover-mode",
                options=[{"label": "Indep. Hover", "value": "independent"}, {"label": "Sync Hover", "value": "parallel"}],
                value="independent", size="sm", style={"width": "120px", "display": "inline-block", "marginRight": "10px"}
            ),
            dbc.Select(
                id="compare-mode",
                options=[{"label": "Sep. Isolate", "value": "separate"}, {"label": "Overlay Isolate", "value": "overlay"}],
                value="separate", size="sm", style={"width": "130px", "display": "inline-block"}
            )
        ], className="d-flex align-items-center"),
        dbc.Button("Definitions", id="btn-definitions", color="info", size="sm", className="ms-auto")
    ], fluid=True),
    color="primary", dark=True, style={"height": "60px"}
)

# Render Custom Legend function
def render_legend(country_id):
    buttons = []
    for act, color in COLORS.items():
        buttons.append(html.Button(act, id={"type": "legend-btn", "act": act, "country": country_id}, className="legend-btn", style={"backgroundColor": color}))
    return html.Div(buttons, className="legend-container")

app.layout = html.Div([
    dcc.Store(id='current-view', data='overview'),
    dcc.Store(id='selected-activity', data='Show All'),
    dcc.Store(id='is-mobile', data=False),
    dcc.Store(id='mobile-sub-view', data='Male'),
    html.Div(id="dummy-resize-trigger", style={"display": "none"}),
    navbar,
    dbc.Row(className="main-row", children=[
        # CANADA CARD
        dbc.Col(className="col-card", xs=12, md=6, children=[
            dbc.Card([
                dbc.CardHeader(className="d-flex justify-content-between align-items-center py-2 px-3 flex-nowrap", children=[
                    html.H5("Daily Time Use in Canada", className="m-0 fw-bold card-header-title", style={
                        "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis",
                        "fontSize": "clamp(0.85rem, 1.25vw, 1.15rem)", "flex": "1"
                    }),
                    html.Div([
                        dbc.Button("Show All", id="btn-show-all-ca", size="sm", color="dark", className="me-1 btn-compact", style={"display": "none", "whiteSpace": "nowrap", "padding": "2px 8px", "fontSize": "0.75rem"}),
                        dbc.Button("View Data", id="btn-toggle-ca", size="sm", outline=True, color="secondary", className="btn-compact", style={"whiteSpace": "nowrap", "padding": "2px 8px", "fontSize": "0.75rem"})
                    ], className="d-flex align-items-center flex-shrink-0 ms-2")
                ]),
                dbc.CardBody([
                    html.Div(id="chart-container-ca", className="graph-container", children=[
                        html.Div(id="mobile-nav-ca", style={"display": "none"}),
                        dcc.Graph(id="chart-ca", config={'displayModeBar': False}, style={"height": "100%", "width": "100%"})
                    ]),
                    html.Div(id="table-container-ca", className="graph-container", style={"display": "none"}),
                    html.Div(id="legend-container-ca", children=[render_legend("ca")])
                ])
            ])
        ]),
        # VIETNAM CARD
        dbc.Col(className="col-card", xs=12, md=6, children=[
            dbc.Card([
                dbc.CardHeader(className="d-flex justify-content-between align-items-center py-2 px-3 flex-nowrap", children=[
                    html.H5("Daily Time Use in Vietnam", className="m-0 fw-bold card-header-title", style={
                        "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis",
                        "fontSize": "clamp(0.85rem, 1.25vw, 1.15rem)", "flex": "1"
                    }),
                    html.Div([
                        dbc.Button("Show All", id="btn-show-all-vn", size="sm", color="dark", className="me-1 btn-compact", style={"display": "none", "whiteSpace": "nowrap", "padding": "2px 8px", "fontSize": "0.75rem"}),
                        dbc.Button("View Data", id="btn-toggle-vn", size="sm", outline=True, color="secondary", className="btn-compact", style={"whiteSpace": "nowrap", "padding": "2px 8px", "fontSize": "0.75rem"})
                    ], className="d-flex align-items-center flex-shrink-0 ms-2")
                ]),
                dbc.CardBody([
                    html.Div(id="chart-container-vn", className="graph-container", children=[
                        html.Div(id="mobile-nav-vn", style={"display": "none"}),
                        dcc.Graph(id="chart-vn", config={'displayModeBar': False}, style={"height": "100%", "width": "100%"})
                    ]),
                    html.Div(id="table-container-vn", className="graph-container", style={"display": "none"}),
                    html.Div(id="legend-container-vn", children=[render_legend("vn")])
                ])
            ])
        ])
    ]),
    
    # Definitions Modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Activity Definitions (Standardized 2022 Surveys)"), close_button=True),
        dbc.ModalBody([
            html.P("Activities from Statistics Canada and World Bank Vietnam Time Use Surveys have been harmonized into 17 standardized categories:", className="text-muted mb-3"),
            html.Div([
                html.Div([
                    html.Span(style={
                        "display": "inline-block", "width": "14px", "height": "14px", "borderRadius": "50%",
                        "backgroundColor": COLORS.get(act, "#999"), "border": "1px solid #bdc3c7",
                        "marginRight": "10px", "flexShrink": "0"
                    }),
                    html.Strong(act, style={"minWidth": "170px", "marginRight": "10px", "color": "#2c3e50"}),
                    html.Span(desc, className="text-secondary")
                ], className="d-flex align-items-center py-2 border-bottom", style={"fontSize": "0.88rem"})
                for act, desc in ACTIVITY_DEFINITIONS.items()
            ], style={"maxHeight": "60vh", "overflowY": "auto"})
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="btn-close-definitions", className="ms-auto", color="secondary", size="sm")
        )
    ], id="modal-definitions", size="lg", is_open=False, centered=True)
])

# ==============================================================================
# CALLBACKS
# ==============================================================================

@app.callback(
    Output("modal-definitions", "is_open"),
    [Input("btn-definitions", "n_clicks"), Input("btn-close-definitions", "n_clicks")],
    State("modal-definitions", "is_open"),
    prevent_initial_call=True
)
def toggle_modal(n_open, n_close, is_open):
    return not is_open

# Show All Visibility
@app.callback(
    [Output("btn-show-all-ca", "style"), Output("btn-show-all-vn", "style")],
    Input("selected-activity", "data")
)
def toggle_show_all(selected_act):
    if selected_act == "Show All":
        style = {"display": "none"}
    else:
        style = {"display": "inline-block", "whiteSpace": "nowrap", "padding": "2px 8px", "fontSize": "0.75rem"}
    return style, style

# Mobile Width Detection
app.clientside_callback(
    """
    function(active_tab) {
        return window.innerWidth <= 767;
    }
    """,
    Output("is-mobile", "data"),
    Input("view-tabs", "active_tab")
)

# Mobile Navigation Headers
@app.callback(
    [Output("mobile-nav-ca", "children"), Output("mobile-nav-vn", "children"),
     Output("mobile-nav-ca", "style"), Output("mobile-nav-vn", "style"),
     Output("mobile-sub-view", "data")],
    [Input("current-view", "data"), Input("is-mobile", "data"),
     Input({"type": "nav-link", "view": dash.ALL}, "n_clicks")],
    [State("mobile-sub-view", "data")]
)
def update_mobile_nav(view_mode, is_mobile, n_clicks_list, current_sub):
    if not is_mobile or view_mode not in ["gender", "age"]:
        return None, None, {"display": "none"}, {"display": "none"}, current_sub
        
    if ctx.triggered_id and isinstance(ctx.triggered_id, dict):
        new_view = ctx.triggered_id.get("view")
        if new_view: current_sub = new_view
        
    if view_mode == "gender" and current_sub not in ["Male", "Female"]:
        current_sub = "Male"
    elif view_mode == "age" and current_sub not in ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]:
        current_sub = "15 to 34 years"
        
    nav_style = {"display": "flex", "justifyContent": "space-between", "alignItems": "center", "fontWeight": "bold", "marginBottom": "5px", "padding": "0 10px"}
    
    def render_nav(sub):
        if view_mode == "gender":
            left = html.Span("< Male", id={"type": "nav-link", "view": "Male"}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "left"}) if sub == "Female" else html.Span("", style={"flex": "1"})
            right = html.Span("Female >", id={"type": "nav-link", "view": "Female"}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "right"}) if sub == "Male" else html.Span("", style={"flex": "1"})
            title = html.Span("Female" if sub == "Female" else "Male", style={"flex": "1", "textAlign": "center"})
            return [left, title, right]
            
        elif view_mode == "age":
            ages = ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]
            labels = ["15-34", "35-54", "55-64", "65+"]
            idx = ages.index(sub)
            
            left = html.Span(f"< {labels[idx-1]}", id={"type": "nav-link", "view": ages[idx-1]}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "left"}) if idx > 0 else html.Span("", style={"flex": "1"})
            right = html.Span(f"{labels[idx+1]} >", id={"type": "nav-link", "view": ages[idx+1]}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "right"}) if idx < 3 else html.Span("", style={"flex": "1"})
            title = html.Span(labels[idx], style={"flex": "1", "textAlign": "center"})
            return [left, title, right]
            
    content = render_nav(current_sub)
    return content, content, nav_style, nav_style, current_sub

# Legend Click Handler
@app.callback(
    Output('selected-activity', 'data'),
    [Input({'type': 'legend-btn', 'act': dash.ALL, 'country': dash.ALL}, 'n_clicks'),
     Input('btn-show-all-ca', 'n_clicks'), Input('btn-show-all-vn', 'n_clicks')],
    prevent_initial_call=True
)
def handle_legend_click(n_clicks_list, ca_clicks, vn_clicks):
    if not ctx.triggered:
        return dash.no_update
    btn_id = ctx.triggered_id
    if btn_id in ["btn-show-all-ca", "btn-show-all-vn"]:
        return "Show All"
    if isinstance(btn_id, dict):
        return btn_id['act']
    return dash.no_update

# Tab and Button State Sync
@app.callback(
    [Output("current-view", "data"), Output("btn-surprise", "color")],
    [Input("view-tabs", "active_tab"), Input("btn-surprise", "n_clicks")]
)
def sync_view_state(active_tab, surp_click):
    trig = ctx.triggered_id
    if trig == "btn-surprise":
        return "surprise", "warning"
    else:
        # Default back to standard tabs
        return active_tab or "overview", "light"

# Chart Updater
@app.callback(
    [Output("chart-ca", "figure"), Output("chart-vn", "figure")],
    [Input("current-view", "data"), Input("selected-activity", "data"), Input("compare-mode", "value"),
     Input("is-mobile", "data"), Input("mobile-sub-view", "data")]
)
def update_figures(view_mode, selected_act, compare_mode, is_mobile, sub_view):
    df_ca_ov, df_vn_ov = data_cache['overview']
    
    def get_fig(is_ca):
        country_name = "Canada" if is_ca else "Vietnam"
        df_ov = df_ca_ov if is_ca else df_vn_ov
        
        if selected_act != "Show All":
            return create_isolated_chart(df_ov, df_vn_ov if is_ca else df_ca_ov, selected_act, compare_mode, is_ca)
        else:
            if view_mode == "overview":
                return create_overview_chart(df_ov)
            elif view_mode == "gender":
                df_dict = data_cache['gender'][0] if is_ca else data_cache['gender'][1]
                if is_mobile:
                    fig = go.Figure()
                    plot_stacked_area(fig, df_dict[(sub_view, )])
                    fig.update_layout(**create_base_layout())
                    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
                    fig.update_yaxes(range=[0, 100])
                    return fig
                else:
                    return create_gender_chart(df_dict)
            elif view_mode == "age":
                df_dict = data_cache['age'][0] if is_ca else data_cache['age'][1]
                if is_mobile:
                    fig = go.Figure()
                    has_data = not df_dict[(sub_view, )].empty and df_dict[(sub_view, )].sum().sum() > 0
                    if has_data:
                        plot_stacked_area(fig, df_dict[(sub_view, )])
                    fig.update_layout(**create_base_layout())
                    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
                    fig.update_yaxes(range=[0, 100])
                    return fig
                else:
                    return create_age_chart(df_dict)
            elif view_mode == "surprise":
                return create_surprise_chart(df_ov, country_name)
        return go.Figure()
        
    return get_fig(True), get_fig(False)

# Data Table View Toggle
@app.callback(
    [Output("chart-container-ca", "style"), Output("table-container-ca", "style"), Output("table-container-ca", "children"), Output("legend-container-ca", "style"), Output("btn-toggle-ca", "children"),
     Output("chart-container-vn", "style"), Output("table-container-vn", "style"), Output("table-container-vn", "children"), Output("legend-container-vn", "style"), Output("btn-toggle-vn", "children")],
    [Input("btn-toggle-ca", "n_clicks"), Input("btn-toggle-vn", "n_clicks")]
)
def toggle_data_view(btn_ca, btn_vn):
    df_ca_ov, df_vn_ov = data_cache['overview']
    
    def get_toggle_state(btn, df):
        show_data = btn and btn % 2 == 1
        if show_data:
            table = dash_table.DataTable(
                data=df.reset_index().assign(index=lambda x: x['index'].dt.strftime('%H:%M')).to_dict('records'),
                columns=[{"name": i, "id": i} for i in df.reset_index().columns],
                page_size=100, style_table={'height': '100%', 'overflowY': 'auto'}, fixed_rows={'headers': True}
            )
            return {"display": "none"}, {"display": "block", "height": "100%"}, table, {"display": "none"}, "View Chart"
        else:
            return {"display": "block", "height": "100%"}, {"display": "none"}, None, {"display": "block"}, "View Data"

    ca_chart, ca_table, ca_children, ca_leg, ca_text = get_toggle_state(btn_ca, df_ca_ov)
    vn_chart, vn_table, vn_children, vn_leg, vn_text = get_toggle_state(btn_vn, df_vn_ov)
    return ca_chart, ca_table, ca_children, ca_leg, ca_text, vn_chart, vn_table, vn_children, vn_leg, vn_text


# Sync Hover via Clientside Callback (Parallel Interaction)
app.clientside_callback(
    """
    function(hoverCa, hoverVn, parallelMode) {
        if (parallelMode !== 'parallel') return window.dash_clientside.no_update;
        
        const tr = window.dash_clientside.callback_context.triggered;
        if (!tr || !tr.length) return window.dash_clientside.no_update;
        const prop_id = tr[0].prop_id;
        
        const isCa = prop_id === 'chart-ca.hoverData';
        const targetId = isCa ? 'chart-vn' : 'chart-ca';
        const hoverData = isCa ? hoverCa : hoverVn;
        
        if (!hoverData || !hoverData.points || !hoverData.points.length) return window.dash_clientside.no_update;
        
        const xVal = hoverData.points[0].x;
        const targetContainer = document.getElementById(targetId);
        if (!targetContainer) return window.dash_clientside.no_update;
        
        // Find actual Plotly graph DOM element
        const gd = targetContainer.querySelector('.js-plotly-plot') || targetContainer;
        if (!gd || !gd._fullLayout || typeof window.Plotly === 'undefined') return window.dash_clientside.no_update;
        
        const shapes = (gd.layout && gd.layout.shapes) ? gd.layout.shapes : [];
        if (shapes.length > 0) {
            const updates = {};
            for (let i = 0; i < shapes.length; i++) {
                updates['shapes[' + i + '].x0'] = xVal;
                updates['shapes[' + i + '].x1'] = xVal;
                updates['shapes[' + i + '].line.color'] = 'rgba(231, 76, 60, 0.9)';
            }
            try {
                window.Plotly.relayout(gd, updates);
            } catch (err) {
                console.warn('Sync hover relayout error:', err);
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("dummy-resize-trigger", "children"),
    Input("chart-ca", "hoverData"),
    Input("chart-vn", "hoverData"),
    State("hover-mode", "value"),
    prevent_initial_call=True
)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
