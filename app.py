import dash
from dash import dcc, html, Input, Output, State, ctx, dash_table, clientside_callback
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
if os.path.exists(CACHE_FILE):
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

# ==============================================================================
# CHART GENERATORS
# ==============================================================================

def create_base_layout(title=""):
    return dict(
        margin=dict(l=40, r=20, t=30, b=0),
        xaxis=dict(rangeslider=dict(visible=True, thickness=0.1), type="date", showgrid=False, tickformat="%H:%M"),
        yaxis=dict(range=[0, 100], showgrid=True),
        hovermode="x unified",
        showlegend=False, # We use custom dash legends
        plot_bgcolor="white",
        paper_bgcolor="white",
        autosize=True,
        # Add an invisible shape for parallel hover sync
        shapes=[dict(type="line", x0=0, x1=0, y0=0, y1=1, xref="paper", yref="paper", line=dict(color="rgba(0,0,0,0)"))]
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
    fig.update_layout(**create_base_layout())
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100])
    # Enable rangeslider for both x-axes since they are side by side
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
    
    # Check if df is not empty AND actually contains non-zero data
    has_65 = not df_dict[('65 years and over',)].empty and df_dict[('65 years and over',)].sum().sum() > 0
    if has_65:
        plot_stacked_area(fig, df_dict[('65 years and over',)], row=2, col=2)
        
    fig.update_layout(**create_base_layout())
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100])
    
    # Configure rangesliders
    fig.update_layout(xaxis_rangeslider_visible=False, xaxis3_rangeslider=dict(visible=True, thickness=0.05))
    
    if has_65:
        fig.update_layout(xaxis2_rangeslider_visible=False, xaxis4_rangeslider=dict(visible=True, thickness=0.05))
    else:
        # Hide the 65+ subplot axes completely
        fig.update_layout(xaxis4_visible=False, yaxis4_visible=False)
        # Enable rangeslider on xaxis2 (since xaxis4 is gone)
        fig.update_layout(xaxis2_rangeslider=dict(visible=True, thickness=0.05))
        # Remove '65+' title from annotations
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
        # Overlay Comparison
        main_name = "Canada" if is_ca else "Vietnam"
        other_name = "Vietnam" if is_ca else "Canada"
        
        y_main = df_main[activity].values
        y_other = df_other[activity].values
        x_vals = df_main.index
        
        # Draw Other Line
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_other, name=f"{other_name} ({activity})",
            mode='lines', line=dict(color='gray', width=2),
            hovertemplate='<b>%{fullData.name}</b>: %{y:.1f}%<extra></extra>'
        ))
        
        # Draw Main Line, fill between lines. Higher = green, Lower = red
        # Plotly fill='tonexty' colors the whole area between. To color differently, we need to split traces or use a simple line and just hope it looks good.
        # A simple approximation for Dash: draw the main line with tonexty, and use a neutral color, or calculate positive/negative areas.
        # Due to Plotly limitations with multi-color fills, we will draw the area where main > other in green, and main < other in red by creating separate traces.
        
        pos_y = np.where(y_main >= y_other, y_main, y_other)
        neg_y = np.where(y_main < y_other, y_main, y_other)

        # Base trace (other)
        fig.add_trace(go.Scatter(x=x_vals, y=y_other, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        
        # Positive fill (Green)
        fig.add_trace(go.Scatter(
            x=x_vals, y=pos_y, fill='tonexty', fillcolor='rgba(46, 204, 113, 0.4)', 
            mode='lines', line=dict(width=0), name="Higher", hoverinfo='skip'
        ))
        
        # Base trace (other)
        fig.add_trace(go.Scatter(x=x_vals, y=y_other, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        
        # Negative fill (Red)
        fig.add_trace(go.Scatter(
            x=x_vals, y=neg_y, fill='tonexty', fillcolor='rgba(231, 76, 60, 0.4)', 
            mode='lines', line=dict(width=0), name="Lower", hoverinfo='skip'
        ))
        
        # Finally, the main line
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_main, name=f"{main_name} ({activity})",
            mode='lines', line=dict(color=COLORS.get(activity, '#000'), width=3),
            hovertemplate='<b>%{fullData.name}</b>: %{y:.1f}%<extra></extra>'
        ))

    fig.update_layout(**create_base_layout())
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100])
    return fig

def create_ridgeline_plot(df):
    fig = go.Figure()
    spacing = 40
    activities = [a for a in df.columns if a in COLORS]
    
    for i, act in enumerate(activities[::-1]):
        base_y = i * spacing
        fig.add_trace(go.Scatter(
            x=df.index, y=[base_y] * len(df),
            mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df[act] + base_y,
            fill='tonexty', name=act, mode='lines',
            line=dict(color='white', width=1),
            fillcolor=COLORS[act], opacity=0.85
        ))

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=30),
        xaxis=dict(showgrid=False, type="date", tickformat="%H:%M"),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="white"
    )
    return fig

def create_surprise_chart(df_ca, df_vn):
    """ Animated horizontal bar race showing top activities """
    # Since animation in Dash Plotly can be heavy over 1440 frames, we sample every 15 mins (96 frames)
    times = df_ca.index[::15]
    
    # Precompute top activities for CA and VN
    ca_tops = []
    vn_tops = []
    for t in times:
        ca_sort = df_ca.loc[t].sort_values(ascending=False)
        vn_sort = df_vn.loc[t].sort_values(ascending=False)
        ca_tops.append(ca_sort)
        vn_tops.append(vn_sort)
        
    frames = []
    for i, t in enumerate(times):
        ca_row = ca_tops[i]
        vn_row = vn_tops[i]
        
        # Subplot 1: Top 1, Subplot 2: Top 2, Subplot 3: Top 3
        frame_data = []
        for rank in range(3):
            ca_act = ca_row.index[rank]
            ca_val = ca_row.iloc[rank]
            vn_act = vn_row.index[rank]
            vn_val = vn_row.iloc[rank]
            
            frame_data.append(go.Bar(
                x=[ca_val, vn_val],
                y=['Canada', 'Vietnam'],
                orientation='h',
                marker_color=[COLORS.get(ca_act, 'gray'), COLORS.get(vn_act, 'gray')],
                text=[f"{ca_act} ({ca_val:.1f}%)", f"{vn_act} ({vn_val:.1f}%)"],
                textposition='inside',
                xaxis=f'x{rank+1}', yaxis=f'y{rank+1}'
            ))
        frames.append(go.Frame(data=frame_data, name=str(t.strftime("%H:%M"))))

    fig = make_subplots(rows=3, cols=1, shared_xaxes=False, subplot_titles=("Top 1 Activity", "Top 2 Activity", "Top 3 Activity"))
    
    # Add initial traces
    for rank in range(3):
        fig.add_trace(go.Bar(
            x=[ca_tops[0].iloc[rank], vn_tops[0].iloc[rank]],
            y=['Canada', 'Vietnam'], orientation='h',
            marker_color=[COLORS.get(ca_tops[0].index[rank], 'gray'), COLORS.get(vn_tops[0].index[rank], 'gray')],
            text=[f"{ca_tops[0].index[rank]}", f"{vn_tops[0].index[rank]}"],
            textposition='inside'
        ), row=rank+1, col=1)

    fig.update_layout(
        updatemenus=[dict(type="buttons", buttons=[dict(label="Play", method="animate", args=[None, dict(frame=dict(duration=100, redraw=True), fromcurrent=True)])])],
        sliders=[dict(steps=[dict(method='animate', args=[[f.name], dict(mode='immediate', frame=dict(duration=100, redraw=True))], label=f.name) for f in frames])],
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False,
        plot_bgcolor="white"
    )
    for i in range(1, 4):
        fig['layout'][f'xaxis{i}'].update(range=[0, 100])
    
    fig.frames = frames
    return fig

# ==============================================================================
# DASH APP
# ==============================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
app.title = "Time Use Dashboard"

# Ensure precise fit to screen
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
            @media (max-width: 767px) {
                .main-row { flex-direction: column; }
                .col-card { height: 50%; }
                .legend-container { display: none !important; }
                .hovertext text { font-size: 10px !important; }
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
            dbc.Button("Special Chart", id="btn-special", outline=True, color="light", size="sm", className="me-2 rounded-pill"),
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
                dbc.CardHeader(className="d-flex justify-content-between align-items-center py-1", children=[
                    html.Div(style={"width": "160px"}),
                    html.H5("Daily Time Use in Canada", className="m-0 fw-bold text-center", style={"flex": "1"}),
                    html.Div([
                        dbc.Button("Show All", id="btn-show-all-ca", size="sm", color="dark", className="me-2"),
                        dbc.Button("View Data", id="btn-toggle-ca", size="sm", outline=True, color="secondary")
                    ], className="d-flex", style={"width": "160px", "justifyContent": "flex-end"})
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
                dbc.CardHeader(className="d-flex justify-content-between align-items-center py-1", children=[
                    html.Div(style={"width": "160px"}),
                    html.H5("Daily Time Use in Vietnam", className="m-0 fw-bold text-center", style={"flex": "1"}),
                    html.Div([
                        dbc.Button("Show All", id="btn-show-all-vn", size="sm", color="dark", className="me-2"),
                        dbc.Button("View Data", id="btn-toggle-vn", size="sm", outline=True, color="secondary")
                    ], className="d-flex", style={"width": "160px", "justifyContent": "flex-end"})
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
        dbc.ModalHeader(dbc.ModalTitle("Activity Definitions")),
        dbc.ModalBody([
            html.Ul([html.Li(f"{k}: Description for {k}") for k in COLORS.keys()])
        ]),
    ], id="modal-definitions", size="lg", is_open=False, centered=True)
])

# ==============================================================================
# CALLBACKS
# ==============================================================================

@app.callback(
    Output("modal-definitions", "is_open"),
    Input("btn-definitions", "n_clicks"),
    State("modal-definitions", "is_open"),
)
def toggle_modal(n, is_open):
    if n: return not is_open
    return is_open

# Show All Visibility
@app.callback(
    [Output("btn-show-all-ca", "style"), Output("btn-show-all-vn", "style")],
    Input("selected-activity", "data")
)
def toggle_show_all(selected_act):
    style = {"display": "none"} if selected_act == "Show All" else {"display": "block"}
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
    [Output("current-view", "data"), Output("btn-special", "color"), Output("btn-surprise", "color")],
    [Input("view-tabs", "active_tab"), Input("btn-special", "n_clicks"), Input("btn-surprise", "n_clicks")]
)
def sync_view_state(active_tab, spec_click, surp_click):
    trig = ctx.triggered_id
    if trig == "btn-special":
        return "special", "warning", "light"
    elif trig == "btn-surprise":
        return "surprise", "light", "warning"
    else:
        # Default back to standard tabs
        return active_tab or "overview", "light", "light"

# Chart Updater
@app.callback(
    [Output("chart-ca", "figure"), Output("chart-vn", "figure")],
    [Input("current-view", "data"), Input("selected-activity", "data"), Input("compare-mode", "value"),
     Input("is-mobile", "data"), Input("mobile-sub-view", "data")]
)
def update_figures(view_mode, selected_act, compare_mode, is_mobile, sub_view):
    df_ca_ov, df_vn_ov = data_cache['overview']
    
    def get_fig(is_ca):
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
            elif view_mode == "special":
                return create_ridgeline_plot(df_ov)
            elif view_mode == "surprise":
                return create_surprise_chart(df_ca_ov, df_vn_ov) if is_ca else go.Figure()
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
# Draws a vertical line on the other chart
app.clientside_callback(
    """
    function(hoverCa, hoverVn, parallelMode) {
        if (parallelMode !== 'parallel') return window.dash_clientside.no_update;
        
        const tr = window.dash_clientside.callback_context.triggered;
        if(!tr || !tr.length) return window.dash_clientside.no_update;
        const prop_id = tr[0].prop_id;
        
        let targetId = prop_id === 'chart-ca.hoverData' ? 'chart-vn' : 'chart-ca';
        let hoverData = prop_id === 'chart-ca.hoverData' ? hoverCa : hoverVn;
        
        if(!hoverData || !hoverData.points || !hoverData.points[0]) return window.dash_clientside.no_update;
        
        const x = hoverData.points[0].x;
        const targetGraph = document.getElementById(targetId);
        
        if(targetGraph) {
            Plotly.relayout(targetGraph, {
                'shapes[0]': {
                    type: 'line', x0: x, x1: x, y0: 0, y1: 1, yref: 'paper',
                    line: {color: 'black', width: 2, dash: 'dot'}
                }
            });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("hover-mode", "id"), # Dummy output
    Input("chart-ca", "hoverData"),
    Input("chart-vn", "hoverData"),
    State("hover-mode", "value"),
    prevent_initial_call=True
)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
