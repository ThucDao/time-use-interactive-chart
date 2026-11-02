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
    if "age_bcr" not in data_cache:
        print("Upgrading cached data with Bar Chart Race age groups (15-24, 25-64)...")
        data_cache = get_dashboard_data()
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(data_cache, f)
else:
    print("Processing data from scratch. This may take a few seconds...")
    data_cache = get_dashboard_data()
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data_cache, f)

# Canonical category stacking order matching Statistics Canada Tempogram (bottom y=0 to top y=100)
CATEGORY_ORDER = [
    "Sleeping",
    "Personal care",
    "Eating",
    "Travelling",
    "Work",
    "Sell goods or provide services",
    "Education",
    "Caring",
    "Housework",
    "Shopping",
    "Sport",
    "Outdoor activities",
    "Active leisure",
    "Relaxing",
    "TV/Online videos",
    "Passive leisure",
    "Others"
]

def reorder_data_columns(data):
    def reorder_df(df):
        cols = [c for c in CATEGORY_ORDER if c in df.columns] + [c for c in df.columns if c not in CATEGORY_ORDER]
        return df[cols]
    
    reordered = {}
    for key, val in data.items():
        if isinstance(val, tuple):
            reordered[key] = tuple(reorder_df(x) if isinstance(x, pd.DataFrame) else {k: reorder_df(v) for k, v in x.items()} for x in val)
        elif isinstance(val, pd.DataFrame):
            reordered[key] = reorder_df(val)
        elif isinstance(val, dict):
            reordered[key] = {k: reorder_df(v) for k, v in val.items()}
        else:
            reordered[key] = val
    return reordered

data_cache = reorder_data_columns(data_cache)

# High-contrast color palette for all 17 categories (adjacent series have contrasting hues/luminance)
COLORS = {
    "Sleeping": "#1e293b",
    "Personal care": "#f59e0b",
    "Eating": "#059669",
    "Travelling": "#e11d48",
    "Work": "#2563eb",
    "Sell goods or provide services": "#f97316",
    "Education": "#7c3aed",
    "Caring": "#06b6d4",
    "Housework": "#b45309",
    "Shopping": "#84cc16",
    "Sport": "#db2777",
    "Outdoor activities": "#166534",
    "Active leisure": "#facc15",
    "Relaxing": "#3730a3",
    "TV/Online videos": "#ef4444",
    "Passive leisure": "#14b8a6",
    "Others": "#94a3b8"
}

# Standardized activity definitions
ACTIVITY_DEFINITIONS = {
    "Sleeping": "Nighttime sleep, naps, essential rest, and resting during illness.",
    "Personal care": "Bathing, grooming, dressing, personal hygiene, and private health/medical self-care.",
    "Eating": "Consuming meals, snacks, and beverages at home, work, or dining establishments.",
    "Travelling": "Commuting to/from work, school, shopping, socializing, appointments, or errands via transit, car, bicycle, or walking.",
    "Work": "Main or secondary paid employment, farming, business operations, telework, overtime, and work-related duties.",
    "Sell goods or provide services": "Informal commerce, market sales, retail selling, street vending, and independent client services.",
    "Education": "Attending school/university lectures, studying, completing homework, taking courses, and educational training.",
    "Caring": "Caring for children (feeding, playing, homework assistance) and eldercare or assisting sick/disabled family members.",
    "Housework": "Cooking, meal preparation, indoor/outdoor cleaning, laundry, ironing, home repairs, and household organization.",
    "Shopping": "Purchasing groceries, food, clothing, household goods, personal items, and online shopping.",
    "Sport": "Physical exercise, workouts, gym, competitive sports, running, cycling, swimming, and fitness activities.",
    "Outdoor activities": "Walking, hiking, gardening, spending time in nature, parks, and outdoor recreational spaces.",
    "Active leisure": "Video gaming, hobbies, artistic activities, crafts, playing musical instruments, and attending social events.",
    "Relaxing": "Meditating, resting awake, quiet contemplation, daydreaming, and intentional unstructured downtime.",
    "TV/Online videos": "Watching broadcast television, cable, streaming platforms (e.g., Netflix, YouTube), and movies.",
    "Passive leisure": "Reading books, magazines, or news; listening to music or podcasts; and casual social media browsing.",
    "Others": "Unclassified, unspecified, or miscellaneous diary entries not fitting other standardized categories."
}

# ==============================================================================
# CHART GENERATORS
# ==============================================================================

def create_base_layout(title=""):
    return dict(
        margin=dict(l=45, r=20, t=30, b=0),
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
        yaxis=dict(range=[0, 100], showgrid=True, ticksuffix="%"),
        hovermode="x unified",
        hoverlabel=dict(
            namelength=14,
            font_size=8.5,
            font_family="'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor="#95a5a6"
        ),
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
                y1=100,
                xref="x",
                yref="y",
                line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")
            )
        ]
    )

def plot_stacked_area(fig, df, row=None, col=None):
    ordered_acts = [act for act in CATEGORY_ORDER if act in df.columns] + [act for act in df.columns if act not in CATEGORY_ORDER]
    for act in ordered_acts:
        if act in COLORS:
            trace = go.Scatter(
                x=df.index, y=df[act],
                name=act, mode='lines',
                line=dict(width=0.5, color=COLORS[act]),
                stackgroup='one',
                hovertemplate='%{fullData.name}: <b>%{y:.1f}%</b><extra></extra>'
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
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    return fig

def hex_to_rgba(hex_color, alpha=0.2):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"

def add_isolated_traces(fig, df_main, df_other, activity, compare_mode, is_ca, row=None, col=None):
    def _add(tr):
        if row and col:
            fig.add_trace(tr, row=row, col=col)
        else:
            fig.add_trace(tr)

    if df_main is None or df_main.empty or activity not in df_main.columns:
        return

    if compare_mode == "separate" or df_other is None or df_other.empty or activity not in df_other.columns:
        _add(go.Scatter(
            x=df_main.index, y=df_main[activity],
            name=activity, mode='lines',
            line=dict(color=COLORS.get(activity, '#000')),
            fill='tozeroy', fillcolor=hex_to_rgba(COLORS.get(activity, '#000000'), 0.6),
            hovertemplate='%{fullData.name}: <b>%{y:.1f}%</b><extra></extra>'
        ))
    else:
        main_name = "Canada" if is_ca else "Vietnam"
        other_name = "Vietnam" if is_ca else "Canada"
        
        y_main = df_main[activity].values
        y_other = df_other[activity].values
        x_vals = df_main.index
        
        _add(go.Scatter(
            x=x_vals, y=y_other, name=f"{other_name} ({activity})",
            mode='lines', line=dict(color='gray', width=2),
            hovertemplate='%{fullData.name}: <b>%{y:.1f}%</b><extra></extra>'
        ))
        
        pos_y = np.where(y_main >= y_other, y_main, y_other)
        neg_y = np.where(y_main < y_other, y_main, y_other)

        _add(go.Scatter(x=x_vals, y=y_other, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        _add(go.Scatter(
            x=x_vals, y=pos_y, fill='tonexty', fillcolor='rgba(46, 204, 113, 0.4)', 
            mode='lines', line=dict(width=0), name="Higher", hoverinfo='skip'
        ))
        _add(go.Scatter(x=x_vals, y=y_other, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
        _add(go.Scatter(
            x=x_vals, y=neg_y, fill='tonexty', fillcolor='rgba(231, 76, 60, 0.4)', 
            mode='lines', line=dict(width=0), name="Lower", hoverinfo='skip'
        ))
        _add(go.Scatter(
            x=x_vals, y=y_main, name=f"{main_name} ({activity})",
            mode='lines', line=dict(color=COLORS.get(activity, '#000'), width=3),
            hovertemplate='%{fullData.name}: <b>%{y:.1f}%</b><extra></extra>'
        ))

def create_gender_chart(df_dict, df_other_dict=None, selected_act="Show All", compare_mode="separate", is_ca=True):
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05, subplot_titles=("Male", "Female"))
    if selected_act != "Show All" and selected_act in COLORS:
        add_isolated_traces(fig, df_dict[('Male',)], df_other_dict[('Male',)] if df_other_dict else None, selected_act, compare_mode, is_ca, row=1, col=1)
        add_isolated_traces(fig, df_dict[('Female',)], df_other_dict[('Female',)] if df_other_dict else None, selected_act, compare_mode, is_ca, row=1, col=2)
    else:
        plot_stacked_area(fig, df_dict[('Male',)], row=1, col=1)
        plot_stacked_area(fig, df_dict[('Female',)], row=1, col=2)
    layout = create_base_layout()
    layout['shapes'] = [
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=100, xref="x", yref="y", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")),
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=100, xref="x2", yref="y2", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot"))
    ]
    fig.update_layout(**layout)
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    fig.update_layout(xaxis_rangeslider=dict(visible=True, thickness=0.05), 
                      xaxis2_rangeslider=dict(visible=True, thickness=0.05))
    return fig

def create_age_chart(df_dict, df_other_dict=None, selected_act="Show All", compare_mode="separate", is_ca=True):
    fig = make_subplots(rows=2, cols=2, shared_yaxes=True, shared_xaxes=True, 
                        vertical_spacing=0.08, horizontal_spacing=0.05,
                        subplot_titles=("15-34", "35-54", "55-64", "65+"))
    has_65 = ('65 years and over',) in df_dict and not df_dict[('65 years and over',)].empty and df_dict[('65 years and over',)].sum().sum() > 0

    if selected_act != "Show All" and selected_act in COLORS:
        add_isolated_traces(fig, df_dict[('15 to 34 years',)], df_other_dict[('15 to 34 years',)] if df_other_dict else None, selected_act, compare_mode, is_ca, row=1, col=1)
        add_isolated_traces(fig, df_dict[('35 to 54 years',)], df_other_dict[('35 to 54 years',)] if df_other_dict else None, selected_act, compare_mode, is_ca, row=1, col=2)
        add_isolated_traces(fig, df_dict[('55 to 64 years',)], df_other_dict[('55 to 64 years',)] if df_other_dict else None, selected_act, compare_mode, is_ca, row=2, col=1)
        if has_65:
            other_65 = df_other_dict.get(('65 years and over',)) if df_other_dict else None
            has_other_65 = other_65 is not None and not other_65.empty and other_65.sum().sum() > 0
            add_isolated_traces(fig, df_dict[('65 years and over',)], other_65 if has_other_65 else None, selected_act, compare_mode, is_ca, row=2, col=2)
    else:
        plot_stacked_area(fig, df_dict[('15 to 34 years',)], row=1, col=1)
        plot_stacked_area(fig, df_dict[('35 to 54 years',)], row=1, col=2)
        plot_stacked_area(fig, df_dict[('55 to 64 years',)], row=2, col=1)
        if has_65:
            plot_stacked_area(fig, df_dict[('65 years and over',)], row=2, col=2)
        
    layout = create_base_layout()
    shapes = [
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=100, xref="x", yref="y", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")),
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=100, xref="x2", yref="y2", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot")),
        dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=100, xref="x3", yref="y3", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot"))
    ]
    if has_65:
        shapes.append(
            dict(type="line", x0="2022-01-01 00:00:00", x1="2022-01-01 00:00:00", y0=0, y1=100, xref="x4", yref="y4", line=dict(color="rgba(0,0,0,0)", width=2, dash="dot"))
        )
    layout['shapes'] = shapes
    fig.update_layout(**layout)
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    
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
    add_isolated_traces(fig, df_main, df_other, activity, compare_mode, is_ca)
    fig.update_layout(**create_base_layout())
    fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    return fig

def create_surprise_chart(tab_mode, is_ca, selected_act="Show All", compare_mode="separate", is_mobile=False, sub_view=None):
    """
    Animated horizontal bar chart race showing ALL 17 activity categories.
    Supports:
    - Overview, By Gender (Male, Female), and By Age (15-24, 25-64; excluding 65+)
    - Highlighting a selected category while dimming other categories in the race
    - Side-by-side vs. Overlay comparison when a category is selected
    """
    country_name = "Canada" if is_ca else "Vietnam"
    other_country_name = "Vietnam" if is_ca else "Canada"
    other_short = "VN" if is_ca else "CA"
    df_ca_ov, df_vn_ov = data_cache['overview']

    if tab_mode == "gender":
        df_m_dict = data_cache['gender'][0] if is_ca else data_cache['gender'][1]
        df_o_dict = data_cache['gender'][1] if is_ca else data_cache['gender'][0]
        if is_mobile:
            sv = sub_view if sub_view in ["Male", "Female"] else "Male"
            panels = [(sv, df_m_dict[(sv,)], df_o_dict[(sv,)])]
        else:
            panels = [
                ("Male", df_m_dict[('Male',)], df_o_dict[('Male',)]),
                ("Female", df_m_dict[('Female',)], df_o_dict[('Female',)])
            ]
        subtitle_suffix = "By Gender"
    elif tab_mode == "age":
        df_m_dict = data_cache['age_bcr'][0] if is_ca else data_cache['age_bcr'][1]
        df_o_dict = data_cache['age_bcr'][1] if is_ca else data_cache['age_bcr'][0]
        if is_mobile:
            sv = sub_view if sub_view in ["15 to 24 years", "25 to 64 years"] else "15 to 24 years"
            lbl = "15-24" if sv == "15 to 24 years" else "25-64"
            panels = [(lbl, df_m_dict[(sv,)], df_o_dict[(sv,)])]
        else:
            panels = [
                ("15-24", df_m_dict[('15 to 24 years',)], df_o_dict[('15 to 24 years',)]),
                ("25-64", df_m_dict[('25 to 64 years',)], df_o_dict[('25 to 64 years',)])
            ]
        subtitle_suffix = "By Age (15-24 vs 25-64)"
    else:
        df_m = df_ca_ov if is_ca else df_vn_ov
        df_o = df_vn_ov if is_ca else df_ca_ov
        panels = [("Overview", df_m, df_o)]
        subtitle_suffix = "Overview"

    is_isolated = (selected_act != "Show All" and selected_act in COLORS)
    is_overlay = (is_isolated and compare_mode == "overlay")
    is_two_col = (len(panels) == 2)
    text_font_size = 8.0 if is_two_col else 9.5

    times = panels[0][1].index[::15]  # 96 frames sampled every 15 minutes across 24h

    def build_panel_traces(t, df_m, df_o, col_idx):
        xaxis_ref = "x" if col_idx == 1 else f"x{col_idx}"
        yaxis_ref = "y" if col_idx == 1 else f"y{col_idx}"
        row_m = df_m.loc[t].sort_values(ascending=True)
        acts = list(row_m.index)
        vals = [float(v) for v in row_m.values]

        if not is_isolated:
            colors = [COLORS.get(a, '#3498db') for a in acts]
            line_colors = ['white' for _ in acts]
            line_widths = [0.5 for _ in acts]
            texts = [f" {v:.1f}%" for v in vals]
            return [go.Bar(
                x=vals,
                y=acts,
                xaxis=xaxis_ref,
                yaxis=yaxis_ref,
                orientation='h',
                marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                text=texts,
                textposition='outside',
                cliponaxis=False,
                textfont=dict(size=text_font_size, color='#2c3e50'),
                hovertemplate=f'<b>%{{y}}</b> ({country_name}): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )]
        elif not is_overlay:
            # Side-by-side with selected category highlighted and other categories dimmed
            colors = [
                COLORS.get(a, '#3498db') if a == selected_act else hex_to_rgba(COLORS.get(a, '#3498db'), 0.18)
                for a in acts
            ]
            line_colors = ['#0f172a' if a == selected_act else 'rgba(255,255,255,0.5)' for a in acts]
            line_widths = [1.5 if a == selected_act else 0.5 for a in acts]
            texts = [f" <b>{v:.1f}%</b>" if a == selected_act else f" {v:.1f}%" for a, v in zip(acts, vals)]
            return [go.Bar(
                x=vals,
                y=acts,
                xaxis=xaxis_ref,
                yaxis=yaxis_ref,
                orientation='h',
                marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                text=texts,
                textposition='outside',
                cliponaxis=False,
                textfont=dict(size=text_font_size, color='#0f172a'),
                hovertemplate=f'<b>%{{y}}</b> ({country_name}): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )]
        else:
            # Overlay comparison: highlight selected category, dim other 16 categories, and overlay other country's bar on selected_act
            other_val = float(df_o.loc[t, selected_act]) if (df_o is not None and not df_o.empty and selected_act in df_o.columns) else 0.0
            colors = [
                COLORS.get(a, '#3498db') if a == selected_act else hex_to_rgba(COLORS.get(a, '#3498db'), 0.18)
                for a in acts
            ]
            line_colors = ['#0f172a' if a == selected_act else 'rgba(255,255,255,0.5)' for a in acts]
            line_widths = [1.5 if a == selected_act else 0.5 for a in acts]
            main_texts = []
            overlay_texts = []
            overlay_x = []
            for a, v in zip(acts, vals):
                if a == selected_act:
                    overlay_x.append(other_val)
                    comp_label = f" <b>{v:.1f}%</b> ({other_short}: {other_val:.1f}%)"
                    if v >= other_val:
                        main_texts.append(comp_label)
                        overlay_texts.append("")
                    else:
                        main_texts.append("")
                        overlay_texts.append(comp_label)
                else:
                    overlay_x.append(None)
                    main_texts.append(f" {v:.1f}%")
                    overlay_texts.append("")

            trace_main = go.Bar(
                x=vals,
                y=acts,
                xaxis=xaxis_ref,
                yaxis=yaxis_ref,
                name=f"{country_name} ({selected_act})",
                orientation='h',
                width=0.82,
                marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                text=main_texts,
                textposition='outside',
                cliponaxis=False,
                textfont=dict(size=text_font_size, color='#0f172a'),
                hovertemplate=f'<b>%{{y}}</b> ({country_name}): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )
            trace_other = go.Bar(
                x=overlay_x,
                y=acts,
                xaxis=xaxis_ref,
                yaxis=yaxis_ref,
                name=f"{other_country_name} ({selected_act})",
                orientation='h',
                width=0.38,
                marker=dict(color='rgba(15, 23, 42, 0.86)', line=dict(color='#ffffff', width=1.2)),
                text=overlay_texts,
                textposition='outside',
                cliponaxis=False,
                textfont=dict(size=text_font_size, color='#0f172a'),
                hovertemplate=f'<b>%{{y}}</b> ({other_country_name} overlay): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )
            return [trace_main, trace_other]

    frames = []
    for t in times:
        frame_traces = []
        for idx, (_, df_m, df_o) in enumerate(panels, start=1):
            frame_traces.extend(build_panel_traces(t, df_m, df_o, idx))
        frames.append(go.Frame(
            data=frame_traces,
            traces=list(range(len(frame_traces))),
            name=t.strftime("%H:%M")
        ))

    initial_traces = []
    for idx, (_, df_m, df_o) in enumerate(panels, start=1):
        initial_traces.extend(build_panel_traces(times[0], df_m, df_o, idx))

    label_alias = {}
    if is_two_col:
        label_alias["Sell goods or provide services"] = "Sell goods/services"
    if is_isolated:
        disp = label_alias.get(selected_act, selected_act)
        label_alias[selected_act] = f"▶ {disp}"

    title_str = f"All 17 Activities in {country_name} — {subtitle_suffix}"
    if is_isolated:
        mode_lbl = f"Overlay vs. {other_country_name}" if is_overlay else "Highlighted"
        title_str += f" [{selected_act}: {mode_lbl}]"

    slider_cfg = [dict(
        active=0,
        x=0.0, y=-0.08,
        len=1.0,
        xanchor="left", yanchor="top",
        currentvalue=dict(prefix="Time: ", font=dict(size=11, color="#2c3e50"), visible=True),
        steps=[dict(method='animate', args=[[f.name], dict(mode='immediate', frame=dict(duration=100, redraw=True))], label=f.name) for f in frames]
    )]

    if is_two_col:
        fig = make_subplots(
            rows=1, cols=2,
            shared_yaxes=False,
            horizontal_spacing=0.25,
            subplot_titles=(panels[0][0], panels[1][0])
        )
        for tr in initial_traces:
            fig.add_trace(tr)
        fig.update_layout(
            title=dict(text=title_str, font=dict(size=12.5, color="#2c3e50")),
            barmode='overlay',
            xaxis=dict(range=[0, 118], title="Share (%)", showgrid=True, dtick=25, tickfont=dict(size=8.5)),
            xaxis2=dict(range=[0, 118], title="Share (%)", showgrid=True, dtick=25, tickfont=dict(size=8.5)),
            yaxis=dict(showgrid=False, tickfont=dict(size=8.0), automargin=True, labelalias=label_alias),
            yaxis2=dict(showgrid=False, tickfont=dict(size=8.0), automargin=True, labelalias=label_alias),
            margin=dict(l=10, r=25, t=42, b=45),
            plot_bgcolor="white",
            paper_bgcolor="white",
            sliders=slider_cfg
        )
        fig.frames = frames
    else:
        fig = go.Figure(
            data=initial_traces,
            layout=go.Layout(
                title=dict(text=title_str, font=dict(size=12.5, color="#2c3e50")),
                barmode='overlay',
                xaxis=dict(range=[0, 115], title="Share of Population (%)", showgrid=True, dtick=20),
                yaxis=dict(showgrid=False, tickfont=dict(size=9.5), automargin=True, labelalias=label_alias),
                margin=dict(l=10, r=25, t=35, b=45),
                plot_bgcolor="white",
                paper_bgcolor="white",
                sliders=slider_cfg
            ),
            frames=frames
        )
    return fig

# ==============================================================================
# DASH APP
# ==============================================================================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
app.title = "Time Use Dashboard"
server = app.server  # Expose Flask server for Gunicorn on Render / production

# Ensure precise fit to screen & responsive layout
app.index_string = r'''
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
            .legend-btn { font-size: 0.75rem; padding: 2px 6px; border: none; border-radius: 12px; cursor: pointer; color: white; transition: transform 0.1s, opacity 0.15s;}
            .main-row { height: calc(100vh - 60px); margin: 0; padding: 10px; }
            .col-card { height: 100%; padding: 5px; }
            .card-header-title { white-space: nowrap !important; overflow: hidden; text-overflow: ellipsis; }
            .btn-compact { white-space: nowrap !important; }
            .bcr-controls { display: none; }

            /* Frozen / disabled state for compare-mode dropdown */
            select#compare-mode:disabled {
                background-color: #cbd5e1 !important;
                color: #64748b !important;
                opacity: 0.65 !important;
                cursor: not-allowed !important;
                border-color: #94a3b8 !important;
            }

            /* Clickable y-axis category labels in Bar Chart Race */
            .bcr-mode #chart-ca .ytick text,
            .bcr-mode #chart-ca .y2tick text,
            .bcr-mode #chart-vn .ytick text,
            .bcr-mode #chart-vn .y2tick text {
                pointer-events: all !important;
                cursor: pointer !important;
            }
            .bcr-mode #chart-ca .ytick text:hover,
            .bcr-mode #chart-ca .y2tick text:hover,
            .bcr-mode #chart-vn .ytick text:hover,
            .bcr-mode #chart-vn .y2tick text:hover {
                font-weight: 700 !important;
                fill: #2563eb !important;
                text-decoration: underline;
            }
            
            /* Compact unified hover tooltip box (< 50% chart width, compact height) */
            .hoverlayer .hovertext {
                max-width: 170px !important;
            }
            .hoverlayer .hovertext text {
                font-size: 8.5px !important;
                font-weight: 500 !important;
                line-height: 1.15 !important;
            }
            .hoverlayer .hovertext rect,
            .hoverlayer .hovertext path {
                max-width: 170px !important;
                rx: 4px !important;
                ry: 4px !important;
                opacity: 0.94 !important;
            }

            @media (max-width: 767px) {
                .main-row { flex-direction: column; height: auto !important; overflow-y: auto; }
                .col-card { height: 500px !important; margin-bottom: 15px; }
                .legend-container { display: none !important; }
                .hovertext text { font-size: 9px !important; }
                html, body { overflow: auto !important; height: auto !important; }
            }
        </style>
        <script>
            document.addEventListener('click', function(e) {
                const tickText = e.target.closest('#chart-ca .ytick text, #chart-ca .y2tick text, #chart-vn .ytick text, #chart-vn .y2tick text');
                if (!tickText) return;
                let rawLabel = (tickText.textContent || '').trim();
                rawLabel = rawLabel.replace(/^▶\s*/, '').trim();
                const aliasMap = {
                    "Sell goods/services": "Sell goods or provide services"
                };
                const act = aliasMap[rawLabel] || rawLabel;
                const validActs = [
                    "Sleeping", "Personal care", "Eating", "Travelling",
                    "Work", "Sell goods or provide services", "Education",
                    "Caring", "Housework", "Shopping",
                    "Sport", "Outdoor activities", "Active leisure",
                    "Relaxing", "TV/Online videos", "Passive leisure",
                    "Others"
                ];
                if (validActs.includes(act) && window.dash_clientside && window.dash_clientside.set_props) {
                    window.dash_clientside.set_props('bcr-yaxis-clicked', {data: {act: act, ts: Date.now()}});
                }
            });
        </script>
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
            # 11. Chart Type Title at the leftmost
            html.Span("Tempogram", id="chart-type-title", className="fw-bold fs-5 text-white me-3 align-self-center", style={"whiteSpace": "nowrap"}),
            
            # 12. Tabs Container (Overview, By Gender, By Age)
            html.Div(
                id="tabs-container",
                children=[
                    dbc.Tabs(
                        id="view-tabs",
                        active_tab="overview",
                        children=[
                            dbc.Tab(label="Overview", tab_id="overview"),
                            dbc.Tab(label="By Gender", tab_id="gender"),
                            dbc.Tab(label="By Age", tab_id="age"),
                        ],
                        className="me-2"
                    )
                ]
            ),
            
            # 5 & 13. Hover / Animation Mode Dropdown
            dbc.Select(
                id="hover-mode",
                options=[
                    {"label": "Independent hover", "value": "independent"},
                    {"label": "Synced hover", "value": "parallel"}
                ],
                value="independent",
                size="sm",
                style={"width": "185px", "display": "inline-block", "marginRight": "8px"}
            ),
            
            # 3 & 8. Comparison Mode Dropdown (frozen by default until a category is selected) + Note
            html.Div([
                dbc.Select(
                    id="compare-mode",
                    options=[
                        {"label": "Side-by-side", "value": "separate"},
                        {"label": "Overlay comparison", "value": "overlay"}
                    ],
                    value="separate",
                    disabled=True,
                    size="sm",
                    style={"width": "160px", "display": "inline-block", "flexShrink": "0"}
                ),
                html.Small(
                    "Click a category in the legend to unlock.",
                    id="compare-mode-note",
                    className="text-light ms-2",
                    style={
                        "fontSize": "0.72rem",
                        "lineHeight": "1.15",
                        "maxWidth": "200px",
                        "opacity": "0.9",
                        "display": "inline-block"
                    }
                )
            ], className="d-flex align-items-center")
        ], className="d-flex align-items-center"),
        
        # Right-side action buttons
        html.Div([
            # 9, 10, 12. Switch Button (Before Definitions button with equal distance)
            dbc.Button(
                "SWITCH to Bar Chart Race",
                id="btn-surprise",
                color="warning",
                size="sm",
                className="rounded-pill shadow-sm",
                style={"marginLeft": "12px", "marginRight": "12px", "whiteSpace": "nowrap"}
            ),
            dbc.Button(
                "About",
                id="btn-definitions",
                color="info",
                size="sm",
                className="shadow-sm",
                style={"whiteSpace": "nowrap"}
            )
        ], className="d-flex align-items-center ms-auto")
    ], fluid=True),
    color="primary",
    dark=True,
    style={"height": "60px"}
)

def get_text_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#2c3e50" if luminance > 0.6 else "#ffffff"

# Render Custom Legend function
def render_legend(country_id):
    buttons = []
    for act, color in COLORS.items():
        buttons.append(html.Button(
            act, 
            id={"type": "legend-btn", "act": act, "country": country_id}, 
            className="legend-btn", 
            style={"backgroundColor": color, "color": get_text_color(color)}
        ))
    return html.Div(buttons, className="legend-container")

app.layout = html.Div(id="app-root", className="tempogram-mode", children=[
    dcc.Store(id='current-view', data='tempogram'),
    dcc.Store(id='selected-activity', data='Show All'),
    dcc.Store(id='bcr-yaxis-clicked', data=None),
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
                        dcc.Graph(id="chart-ca", clear_on_unhover=True, config={'displayModeBar': False}, style={"height": "100%", "width": "100%"})
                    ]),
                    html.Div(id="table-container-ca", className="graph-container", style={"display": "none"}),
                    # 6. BCR controls row (Play button at most left of chart)
                    html.Div(id="bcr-controls-ca", className="bcr-controls align-items-center py-1 px-1", style={"display": "none"}, children=[
                        dbc.Button("▶ Play", id="btn-play-ca", size="sm", color="primary", className="rounded-pill shadow-sm px-3", style={"width": "90px", "flexShrink": "0"}),
                        html.Small("24-Hour Timeline (00:00 - 23:45)", className="text-muted ms-3 fst-italic")
                    ]),
                    # 4. Legend container
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
                        dcc.Graph(id="chart-vn", clear_on_unhover=True, config={'displayModeBar': False}, style={"height": "100%", "width": "100%"})
                    ]),
                    html.Div(id="table-container-vn", className="graph-container", style={"display": "none"}),
                    # 6. BCR controls row (Play button at most left of chart)
                    html.Div(id="bcr-controls-vn", className="bcr-controls align-items-center py-1 px-1", style={"display": "none"}, children=[
                        dbc.Button("▶ Play", id="btn-play-vn", size="sm", color="primary", className="rounded-pill shadow-sm px-3", style={"width": "90px", "flexShrink": "0"}),
                        html.Small("24-Hour Timeline (00:00 - 23:45)", className="text-muted ms-3 fst-italic")
                    ]),
                    # 4. Legend container
                    html.Div(id="legend-container-vn", children=[render_legend("vn")])
                ])
            ])
        ])
    ]),
    
    # About & Definitions Modal
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
        dbc.ModalFooter([
            html.Small(
                [
                    "Made by ",
                    html.Strong("Thuc (Thomas) Dao"),
                    " | Data: Statistics Canada & World Bank (2022)"
                ],
                className="text-muted me-auto",
                style={"fontSize": "0.85rem"}
            ),
            dbc.Button("Close", id="btn-close-definitions", className="ms-auto", color="secondary", size="sm")
        ])
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

# Show All Visibility & Compare Mode Dropdown Freeze/Unfreeze
@app.callback(
    [
        Output("btn-show-all-ca", "style"),
        Output("btn-show-all-vn", "style"),
        Output("compare-mode", "disabled"),
        Output("compare-mode", "value")
    ],
    Input("selected-activity", "data"),
    State("compare-mode", "value")
)
def toggle_show_all_and_compare_mode(selected_act, current_compare):
    if not selected_act or selected_act == "Show All":
        style = {"display": "none"}
        return style, style, True, "separate"
    else:
        style = {"display": "inline-block", "whiteSpace": "nowrap", "padding": "2px 8px", "fontSize": "0.75rem"}
        return style, style, False, (current_compare or "separate")

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
    [Input("current-view", "data"), Input("view-tabs", "active_tab"), Input("is-mobile", "data"),
     Input({"type": "nav-link", "view": dash.ALL}, "n_clicks")],
    [State("mobile-sub-view", "data")]
)
def update_mobile_nav(chart_mode, active_tab, is_mobile, n_clicks_list, current_sub):
    tab_mode = active_tab or "overview"
    if not is_mobile or tab_mode not in ["gender", "age"]:
        return None, None, {"display": "none"}, {"display": "none"}, current_sub
        
    if ctx.triggered_id and isinstance(ctx.triggered_id, dict):
        new_view = ctx.triggered_id.get("view")
        if new_view:
            current_sub = new_view
        
    if tab_mode == "gender":
        if current_sub not in ["Male", "Female"]:
            current_sub = "Male"
    elif tab_mode == "age":
        if chart_mode == "surprise":
            if current_sub not in ["15 to 24 years", "25 to 64 years"]:
                current_sub = "15 to 24 years"
        else:
            if current_sub not in ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]:
                current_sub = "15 to 34 years"
        
    nav_style = {"display": "flex", "justifyContent": "space-between", "alignItems": "center", "fontWeight": "bold", "marginBottom": "5px", "padding": "0 10px"}
    
    def render_nav(sub):
        if tab_mode == "gender":
            left = html.Span("< Male", id={"type": "nav-link", "view": "Male"}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "left"}) if sub == "Female" else html.Span("", style={"flex": "1"})
            right = html.Span("Female >", id={"type": "nav-link", "view": "Female"}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "right"}) if sub == "Male" else html.Span("", style={"flex": "1"})
            title = html.Span("Female" if sub == "Female" else "Male", style={"flex": "1", "textAlign": "center"})
            return [left, title, right]
            
        elif tab_mode == "age":
            if chart_mode == "surprise":
                ages = ["15 to 24 years", "25 to 64 years"]
                labels = ["15-24", "25-64"]
            else:
                ages = ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]
                labels = ["15-34", "35-54", "55-64", "65+"]
            idx = ages.index(sub)
            max_idx = len(ages) - 1
            
            left = html.Span(f"< {labels[idx-1]}", id={"type": "nav-link", "view": ages[idx-1]}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "left"}) if idx > 0 else html.Span("", style={"flex": "1"})
            right = html.Span(f"{labels[idx+1]} >", id={"type": "nav-link", "view": ages[idx+1]}, style={"cursor": "pointer", "color": "#3498db", "flex": "1", "textAlign": "right"}) if idx < max_idx else html.Span("", style={"flex": "1"})
            title = html.Span(labels[idx], style={"flex": "1", "textAlign": "center"})
            return [left, title, right]
            
    content = render_nav(current_sub)
    return content, content, nav_style, nav_style, current_sub

# Category Selection Handler (Tempogram Legend, Bar Chart Race y-axis labels / bars, and Show All buttons)
@app.callback(
    Output('selected-activity', 'data'),
    [
        Input({'type': 'legend-btn', 'act': dash.ALL, 'country': dash.ALL}, 'n_clicks'),
        Input('btn-show-all-ca', 'n_clicks'),
        Input('btn-show-all-vn', 'n_clicks'),
        Input('bcr-yaxis-clicked', 'data'),
        Input('chart-ca', 'clickData'),
        Input('chart-vn', 'clickData')
    ],
    [
        State('selected-activity', 'data'),
        State('current-view', 'data')
    ],
    prevent_initial_call=True
)
def handle_legend_click(n_clicks_list, ca_clicks, vn_clicks, bcr_yaxis_data, ca_click_data, vn_click_data, current_selected, chart_mode):
    if not ctx.triggered:
        return dash.no_update
    btn_id = ctx.triggered_id
    if btn_id in ["btn-show-all-ca", "btn-show-all-vn"]:
        return "Show All"
    if isinstance(btn_id, dict):
        clicked_act = btn_id.get('act')
        if clicked_act:
            return "Show All" if clicked_act == current_selected else clicked_act
    if btn_id == "bcr-yaxis-clicked" and isinstance(bcr_yaxis_data, dict):
        clicked_act = bcr_yaxis_data.get("act")
        if clicked_act in COLORS:
            return "Show All" if clicked_act == current_selected else clicked_act
    if btn_id in ["chart-ca", "chart-vn"] and chart_mode == "surprise":
        click_payload = ca_click_data if btn_id == "chart-ca" else vn_click_data
        if click_payload and click_payload.get("points"):
            clicked_act = click_payload["points"][0].get("y")
            if clicked_act in COLORS:
                return "Show All" if clicked_act == current_selected else clicked_act
    return dash.no_update

# 3, 4, 5, 8, 9, 10, 11, 12, 13: Unified View & State Synchronization
@app.callback(
    [
        Output("current-view", "data"),
        Output("app-root", "className"),
        Output("chart-type-title", "children"),
        Output("tabs-container", "style"),
        Output("btn-surprise", "children"),
        Output("btn-surprise", "color"),
        Output("hover-mode", "options"),
        Output("compare-mode-note", "children"),
        Output("legend-container-ca", "style"),
        Output("legend-container-vn", "style"),
        Output("bcr-controls-ca", "style"),
        Output("bcr-controls-vn", "style"),
    ],
    [Input("btn-surprise", "n_clicks")],
    [State("current-view", "data")],
    prevent_initial_call=False
)
def sync_view_state(surp_click, current_view):
    trig = ctx.triggered_id
    
    # Toggle between Bar Chart Race and Tempogram
    if trig == "btn-surprise":
        is_surprise = (current_view != "surprise")
    else:
        is_surprise = (current_view == "surprise")
        
    tabs_style = {"display": "block"}

    if is_surprise:
        # Bar Chart Race Active
        new_view = "surprise"
        root_class = "bcr-mode"
        title = "Bar Chart Race"
        btn_text = "SWITCH to Tempogram"
        btn_color = "warning"
        hover_options = [
            {"label": "Independent animation", "value": "independent"},
            {"label": "Synced animation", "value": "parallel"}
        ]
        compare_note = "Click a category in the vertical axis to unlock"
        legend_style = {"display": "none"}
        bcr_style = {"display": "flex", "alignItems": "center"}
    else:
        # Tempogram Active
        new_view = "tempogram"
        root_class = "tempogram-mode"
        title = "Tempogram"
        btn_text = "SWITCH to Bar Chart Race"
        btn_color = "warning"
        hover_options = [
            {"label": "Independent hover", "value": "independent"},
            {"label": "Synced hover", "value": "parallel"}
        ]
        compare_note = "Click a category in the legend to unlock."
        legend_style = {
            "display": "flex", "flexWrap": "wrap", "justifyContent": "center",
            "gap": "5px", "padding": "5px", "maxHeight": "80px", "overflowY": "auto"
        }
        bcr_style = {"display": "none"}
        
    return (
        new_view, root_class, title, tabs_style, btn_text, btn_color,
        hover_options, compare_note, legend_style, legend_style,
        bcr_style, bcr_style
    )

# Chart Updater
@app.callback(
    [Output("chart-ca", "figure"), Output("chart-vn", "figure")],
    [
        Input("current-view", "data"),
        Input("view-tabs", "active_tab"),
        Input("selected-activity", "data"),
        Input("compare-mode", "value"),
        Input("is-mobile", "data"),
        Input("mobile-sub-view", "data")
    ]
)
def update_figures(chart_mode, active_tab, selected_act, compare_mode, is_mobile, sub_view):
    tab_mode = active_tab or "overview"
    df_ca_ov, df_vn_ov = data_cache['overview']
    
    def get_fig(is_ca):
        df_ov = df_ca_ov if is_ca else df_vn_ov
        df_other_ov = df_vn_ov if is_ca else df_ca_ov
        
        if chart_mode == "surprise":
            return create_surprise_chart(
                tab_mode=tab_mode,
                is_ca=is_ca,
                selected_act=selected_act,
                compare_mode=compare_mode,
                is_mobile=is_mobile,
                sub_view=sub_view
            )

        # Tempogram Mode
        if tab_mode == "overview":
            if selected_act != "Show All" and selected_act in COLORS:
                return create_isolated_chart(df_ov, df_other_ov, selected_act, compare_mode, is_ca)
            return create_overview_chart(df_ov)
        elif tab_mode == "gender":
            df_dict = data_cache['gender'][0] if is_ca else data_cache['gender'][1]
            df_other_dict = data_cache['gender'][1] if is_ca else data_cache['gender'][0]
            if is_mobile:
                sv = sub_view if sub_view in ["Male", "Female"] else "Male"
                if selected_act != "Show All" and selected_act in COLORS:
                    return create_isolated_chart(df_dict[(sv,)], df_other_dict[(sv,)], selected_act, compare_mode, is_ca)
                fig = go.Figure()
                plot_stacked_area(fig, df_dict[(sv,)])
                fig.update_layout(**create_base_layout())
                fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
                fig.update_yaxes(range=[0, 100], ticksuffix="%")
                return fig
            else:
                return create_gender_chart(df_dict, df_other_dict, selected_act, compare_mode, is_ca)
        elif tab_mode == "age":
            df_dict = data_cache['age'][0] if is_ca else data_cache['age'][1]
            df_other_dict = data_cache['age'][1] if is_ca else data_cache['age'][0]
            if is_mobile:
                sv = sub_view if sub_view in ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"] else "15 to 34 years"
                has_data = not df_dict[(sv,)].empty and df_dict[(sv,)].sum().sum() > 0
                if selected_act != "Show All" and selected_act in COLORS and has_data:
                    other_df = df_other_dict.get((sv,))
                    has_other = other_df is not None and not other_df.empty and other_df.sum().sum() > 0
                    return create_isolated_chart(df_dict[(sv,)], other_df if has_other else None, selected_act, compare_mode, is_ca)
                fig = go.Figure()
                if has_data:
                    plot_stacked_area(fig, df_dict[(sv,)])
                fig.update_layout(**create_base_layout())
                fig.update_xaxes(tickformat="%H:%M", hoverformat="%H:%M")
                fig.update_yaxes(range=[0, 100], ticksuffix="%")
                return fig
            else:
                return create_age_chart(df_dict, df_other_dict, selected_act, compare_mode, is_ca)
        return go.Figure()
        
    return get_fig(True), get_fig(False)

# Data Table View Toggle
@app.callback(
    [Output("chart-container-ca", "style"), Output("table-container-ca", "style"), Output("table-container-ca", "children"), Output("btn-toggle-ca", "children"),
     Output("chart-container-vn", "style"), Output("table-container-vn", "style"), Output("table-container-vn", "children"), Output("btn-toggle-vn", "children")],
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
            return {"display": "none"}, {"display": "block", "height": "100%"}, table, "View Chart"
        else:
            return {"display": "block", "height": "100%"}, {"display": "none"}, None, "View Data"

    ca_chart, ca_table, ca_children, ca_text = get_toggle_state(btn_ca, df_ca_ov)
    vn_chart, vn_table, vn_children, vn_text = get_toggle_state(btn_vn, df_vn_ov)
    return ca_chart, ca_table, ca_children, ca_text, vn_chart, vn_table, vn_children, vn_text


# 1 & 2: Sync Hover & Tooltip Synchronization
app.clientside_callback(
    """
    function(hoverCa, hoverVn, hoverMode) {
        if (hoverMode !== 'parallel') return window.dash_clientside.no_update;
        
        const tr = window.dash_clientside.callback_context.triggered;
        if (!tr || !tr.length) return window.dash_clientside.no_update;
        const prop_id = tr[0].prop_id;
        
        if (window.__isSyncHovering) return window.dash_clientside.no_update;
        
        const gdCa = document.querySelector('#chart-ca .js-plotly-plot');
        const gdVn = document.querySelector('#chart-vn .js-plotly-plot');
        
        if (!window.Plotly || !gdCa || !gdVn) return window.dash_clientside.no_update;
        
        const isCa = (prop_id === 'chart-ca.hoverData');
        const hoverData = isCa ? hoverCa : hoverVn;
        const sourceGd = isCa ? gdCa : gdVn;
        const targetGd = isCa ? gdVn : gdCa;
        
        // Handle unhover (when mouse leaves, hoverData is null or empty)
        if (!hoverData || !hoverData.points || !hoverData.points.length) {
            try {
                window.Plotly.Fx.unhover(targetGd);
                const shapes = (targetGd.layout && targetGd.layout.shapes) ? targetGd.layout.shapes : [];
                if (shapes.length > 0) {
                    const updates = {};
                    for (let i = 0; i < shapes.length; i++) {
                        updates['shapes[' + i + '].line.color'] = 'rgba(0,0,0,0)';
                    }
                    window.Plotly.relayout(targetGd, updates);
                }
            } catch(e) {}
            return window.dash_clientside.no_update;
        }
        
        const pt = hoverData.points[0];
        const xVal = pt.x;
        const ptIdx = (typeof pt.pointNumber !== 'undefined') ? pt.pointNumber : pt.pointIndex;
        const curveNum = pt.curveNumber;
        
        // Identify which subplot/xaxis was hovered on source chart
        const sourceTrace = (sourceGd && sourceGd.data && typeof curveNum !== 'undefined') ? sourceGd.data[curveNum] : null;
        const activeXAxis = (sourceTrace && sourceTrace.xaxis) ? sourceTrace.xaxis : 'x';
        
        // Find matching traces in target chart that belong to the SAME subplot/xaxis
        const targetIndices = [];
        if (targetGd && targetGd.data) {
            for (let i = 0; i < targetGd.data.length; i++) {
                const trX = targetGd.data[i].xaxis || 'x';
                if (trX === activeXAxis) {
                    targetIndices.push(i);
                }
            }
        }
        
        window.__isSyncHovering = true;
        try {
            // 1. Draw synchronized vertical guide line ONLY on the matching subplot of target
            const shapes = (targetGd.layout && targetGd.layout.shapes) ? targetGd.layout.shapes : [];
            if (shapes.length > 0) {
                const updates = {};
                for (let i = 0; i < shapes.length; i++) {
                    const sXRef = shapes[i].xref || 'x';
                    if (sXRef === activeXAxis && targetIndices.length > 0) {
                        updates['shapes[' + i + '].x0'] = xVal;
                        updates['shapes[' + i + '].x1'] = xVal;
                        updates['shapes[' + i + '].line.color'] = 'rgba(231, 76, 60, 0.9)';
                    } else {
                        updates['shapes[' + i + '].line.color'] = 'rgba(0,0,0,0)';
                    }
                }
                window.Plotly.relayout(targetGd, updates);
            }
            
            // 2. Trigger unified hover tooltip box on target chart for this corresponding subplot
            if (targetIndices.length > 0 && typeof ptIdx !== 'undefined') {
                const firstTr = targetGd.data[targetIndices[0]];
                const targetSubplotId = (firstTr.xaxis || 'x') + (firstTr.yaxis || 'y');
                const pts = targetIndices.map(idx => ({ curveNumber: idx, pointNumber: ptIdx }));
                window.Plotly.Fx.hover(targetGd, pts, targetSubplotId);
            } else {
                window.Plotly.Fx.unhover(targetGd);
            }
        } catch(err) {
            console.warn('Sync hover error:', err);
        } finally {
            setTimeout(() => { window.__isSyncHovering = false; }, 30);
        }
        
        return window.dash_clientside.no_update;
    }
    """,
    Output("dummy-resize-trigger", "children"),
    [
        Input("chart-ca", "hoverData"),
        Input("chart-vn", "hoverData")
    ],
    State("hover-mode", "value"),
    prevent_initial_call=True
)


# 5 & 6: Bar Chart Race Play/Pause & Animation Synchronization
app.clientside_callback(
    """
    function(caClicks, vnClicks, currentView, activeTab, selectedAct, compareMode, animMode, caText, vnText) {
        const tr = window.dash_clientside.callback_context.triggered;
        if (!tr || !tr.length) return [caText || "▶ Play", "primary", vnText || "▶ Play", "primary"];
        
        const prop_id = tr[0].prop_id;
        const triggeredId = prop_id.split('.')[0];
        
        // Reset buttons when view, tab, selected category, or compare mode changes (since figure is recreated)
        if (['current-view', 'view-tabs', 'selected-activity', 'compare-mode'].includes(triggeredId)) {
            return ["▶ Play", "primary", "▶ Play", "primary"];
        }
        
        const gdCa = document.querySelector('#chart-ca .js-plotly-plot');
        const gdVn = document.querySelector('#chart-vn .js-plotly-plot');
        const isParallel = (animMode === 'parallel');
        
        const animOptions = {
            frame: { duration: 180, redraw: true },
            fromcurrent: true,
            transition: { duration: 50, easing: 'linear' }
        };
        const pauseOptions = { mode: 'immediate' };
        
        if (triggeredId === 'btn-play-ca') {
            const isPlaying = (caText === '⏸ Pause');
            if (isPlaying) {
                if (gdCa && window.Plotly) window.Plotly.animate(gdCa, [null], pauseOptions);
                if (isParallel && gdVn && window.Plotly) {
                    window.Plotly.animate(gdVn, [null], pauseOptions);
                    return ["▶ Play", "primary", "▶ Play", "primary"];
                }
                return ["▶ Play", "primary", vnText, vnText === '⏸ Pause' ? "secondary" : "primary"];
            } else {
                if (gdCa && window.Plotly) window.Plotly.animate(gdCa, null, animOptions);
                if (isParallel && gdVn && window.Plotly) {
                    window.Plotly.animate(gdVn, null, animOptions);
                    return ["⏸ Pause", "secondary", "⏸ Pause", "secondary"];
                }
                return ["⏸ Pause", "secondary", vnText, vnText === '⏸ Pause' ? "secondary" : "primary"];
            }
        } else if (triggeredId === 'btn-play-vn') {
            const isPlaying = (vnText === '⏸ Pause');
            if (isPlaying) {
                if (gdVn && window.Plotly) window.Plotly.animate(gdVn, [null], pauseOptions);
                if (isParallel && gdCa && window.Plotly) {
                    window.Plotly.animate(gdCa, [null], pauseOptions);
                    return ["▶ Play", "primary", "▶ Play", "primary"];
                }
                return [caText, caText === '⏸ Pause' ? "secondary" : "primary", "▶ Play", "primary"];
            } else {
                if (gdVn && window.Plotly) window.Plotly.animate(gdVn, null, animOptions);
                if (isParallel && gdCa && window.Plotly) {
                    window.Plotly.animate(gdCa, null, animOptions);
                    return ["⏸ Pause", "secondary", "⏸ Pause", "secondary"];
                }
                return [caText, caText === '⏸ Pause' ? "secondary" : "primary", "⏸ Pause", "secondary"];
            }
        }
        return [caText, "primary", vnText, "primary"];
    }
    """,
    [
        Output("btn-play-ca", "children"),
        Output("btn-play-ca", "color"),
        Output("btn-play-vn", "children"),
        Output("btn-play-vn", "color")
    ],
    [
        Input("btn-play-ca", "n_clicks"),
        Input("btn-play-vn", "n_clicks"),
        Input("current-view", "data"),
        Input("view-tabs", "active_tab"),
        Input("selected-activity", "data"),
        Input("compare-mode", "value")
    ],
    [
        State("hover-mode", "value"),
        State("btn-play-ca", "children"),
        State("btn-play-vn", "children")
    ],
    prevent_initial_call=True
)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
