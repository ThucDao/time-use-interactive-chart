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
    acts = list(CATEGORY_ORDER)

    tick_labels = []
    for a in acts:
        lbl = "Sell goods/services" if (is_two_col and a == "Sell goods or provide services") else a
        if is_isolated and a == selected_act:
            lbl = f"▶ {lbl}"
        tick_labels.append(lbl)

    def get_vals_and_ranks(df_m, t):
        vals = [
            float(df_m.loc[t, a]) if (df_m is not None and not df_m.empty and a in df_m.columns) else 0.0
            for a in acts
        ]
        # Rank 0 = smallest at bottom, Rank 16 = largest at top; stable tie-breaker preserves CATEGORY_ORDER
        order = sorted(range(len(acts)), key=lambda i: (round(vals[i], 4), -i))
        ranks = [0.0] * len(acts)
        for rank_pos, cat_idx in enumerate(order):
            ranks[cat_idx] = float(rank_pos) + cat_idx * 1e-5
        return vals, ranks

    def build_panel_traces(t, df_m, df_o, col_idx):
        xaxis_ref = "x" if col_idx == 1 else f"x{col_idx}"
        yaxis_ref = "y" if col_idx == 1 else f"y{col_idx}"
        vals, ranks = get_vals_and_ranks(df_m, t)

        if not is_isolated:
            colors = [COLORS.get(a, '#3498db') for a in acts]
            line_colors = ['white' for _ in acts]
            line_widths = [0.5 for _ in acts]
            texts = [f" {v:.1f}%" for v in vals]
            return [go.Bar(
                x=vals,
                y=ranks,
                base=0,
                width=0.76,
                customdata=acts,
                xaxis=xaxis_ref,
                yaxis=yaxis_ref,
                orientation='h',
                marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                text=texts,
                textposition='outside',
                cliponaxis=False,
                textfont=dict(size=text_font_size, color='#2c3e50'),
                hovertemplate=f'<b>%{{customdata}}</b> ({country_name}): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )], ranks
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
                y=ranks,
                base=0,
                width=0.76,
                customdata=acts,
                xaxis=xaxis_ref,
                yaxis=yaxis_ref,
                orientation='h',
                marker=dict(color=colors, line=dict(color=line_colors, width=line_widths)),
                text=texts,
                textposition='outside',
                cliponaxis=False,
                textfont=dict(size=text_font_size, color='#0f172a'),
                hovertemplate=f'<b>%{{customdata}}</b> ({country_name}): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )], ranks
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
                y=ranks,
                base=0,
                customdata=acts,
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
                hovertemplate=f'<b>%{{customdata}}</b> ({country_name}): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )
            trace_other = go.Bar(
                x=overlay_x,
                y=ranks,
                base=0,
                customdata=acts,
                xaxis=xaxis_ref,
                yaxis=yaxis_ref,
                name=f"{other_country_name} ({selected_act})",
                orientation='h',
                width=0.38,
                marker=dict(color='#ffffff', line=dict(color='#334155', width=1.5)),
                text=overlay_texts,
                textposition='outside',
                cliponaxis=False,
                textfont=dict(size=text_font_size, color='#0f172a'),
                hovertemplate=f'<b>%{{customdata}}</b> ({other_country_name} overlay): %{{x:.1f}}%<extra></extra>',
                showlegend=False
            )
            return [trace_main, trace_other], ranks

    frames = []
    for t in times:
        frame_traces = []
        frame_ranks = []
        for idx, (_, df_m, df_o) in enumerate(panels, start=1):
            p_traces, p_ranks = build_panel_traces(t, df_m, df_o, idx)
            frame_traces.extend(p_traces)
            frame_ranks.append(p_ranks)
        if is_two_col:
            frame_layout = go.Layout(
                yaxis=dict(tickmode="array", tickvals=frame_ranks[0], ticktext=tick_labels),
                yaxis2=dict(tickmode="array", tickvals=frame_ranks[1], ticktext=tick_labels)
            )
        else:
            frame_layout = go.Layout(
                yaxis=dict(tickmode="array", tickvals=frame_ranks[0], ticktext=tick_labels)
            )
        frames.append(go.Frame(
            data=frame_traces,
            layout=frame_layout,
            traces=list(range(len(frame_traces))),
            name=t.strftime("%H:%M")
        ))

    initial_traces = []
    initial_ranks = []
    for idx, (_, df_m, df_o) in enumerate(panels, start=1):
        p_traces, p_ranks = build_panel_traces(times[0], df_m, df_o, idx)
        initial_traces.extend(p_traces)
        initial_ranks.append(p_ranks)

    title_str = f"All 17 Activities in {country_name} — {subtitle_suffix}"
    if is_isolated:
        mode_lbl = f"Overlay vs. {other_country_name}" if is_overlay else "Highlighted"
        title_str += f" [{selected_act}: {mode_lbl}]"

    slider_cfg = [dict(
        active=0,
        x=0.0, y=-0.08,
        len=1.0,
        xanchor="left", yanchor="top",
        transition=dict(duration=0),
        currentvalue=dict(prefix="Time: ", font=dict(size=11, color="#2c3e50"), visible=True),
        steps=[
            dict(
                method='animate',
                args=[[f.name], dict(mode='immediate', frame=dict(duration=0, redraw=True), transition=dict(duration=0))],
                label=f.name
            )
            for f in frames
        ]
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
            yaxis=dict(
                type="linear", range=[-0.65, 16.65],
                tickmode="array", tickvals=initial_ranks[0], ticktext=tick_labels,
                showgrid=False, zeroline=False, tickfont=dict(size=8.0), automargin=True
            ),
            yaxis2=dict(
                type="linear", range=[-0.65, 16.65],
                tickmode="array", tickvals=initial_ranks[1], ticktext=tick_labels,
                showgrid=False, zeroline=False, tickfont=dict(size=8.0), automargin=True
            ),
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
                yaxis=dict(
                    type="linear", range=[-0.65, 16.65],
                    tickmode="array", tickvals=initial_ranks[0], ticktext=tick_labels,
                    showgrid=False, zeroline=False, tickfont=dict(size=9.5), automargin=True
                ),
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

            /* Modern Segmented Pill Tabs in Navbar */
            #tabs-container .nav,
            #tabs-container .nav-tabs,
            #view-tabs {
                background: rgba(8, 35, 20, 0.42) !important;
                padding: 4px !important;
                border-radius: 999px !important;
                border: 1px solid rgba(255, 255, 255, 0.28) !important;
                box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.25) !important;
                display: inline-flex !important;
                align-items: center !important;
                gap: 4px !important;
                margin-bottom: 0 !important;
            }
            #tabs-container .nav-item,
            #view-tabs .nav-item {
                margin-bottom: 0 !important;
            }
            #tabs-container .nav-link,
            #view-tabs .nav-link {
                border: none !important;
                border-radius: 999px !important;
                padding: 5px 15px !important;
                font-size: 0.82rem !important;
                font-weight: 600 !important;
                letter-spacing: 0.015em !important;
                color: rgba(255, 255, 255, 0.85) !important;
                background: transparent !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
                line-height: 1.25 !important;
                white-space: nowrap !important;
                cursor: pointer !important;
            }
            #tabs-container .nav-link:hover:not(.active),
            #view-tabs .nav-link:hover:not(.active) {
                color: #ffffff !important;
                background: rgba(255, 255, 255, 0.16) !important;
            }
            #tabs-container .nav-link.active,
            #view-tabs .nav-link.active {
                background: linear-gradient(180deg, #ffffff 0%, #dcfce7 100%) !important;
                color: #14532d !important;
                font-weight: 700 !important;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.28) !important;
            }

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
                style={"width": "190px", "display": "inline-block", "marginRight": "8px", "flexShrink": "0"}
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
                    style={"width": "170px", "display": "inline-block", "flexShrink": "0"}
                ),
                html.Small(
                    "← To unlock, select a category\nin the legend.",
                    id="compare-mode-note",
                    className="text-light ms-2",
                    style={
                        "fontSize": "0.72rem",
                        "lineHeight": "1.15",
                        "whiteSpace": "pre-line",
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
    dark=True,
    style={
        "height": "60px",
        "background": "linear-gradient(90deg, #14532d 0%, #166534 55%, #15803d 100%)",
        "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.15)"
    }
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

ALL_TIME_OPTIONS = [
    {"label": f"{h:02d}:{m:02d}", "value": f"{h:02d}:{m:02d}"}
    for h in range(24) for m in range(60)
]

def render_table_section(country_id):
    return [
        # Column Filters Bar
        html.Div(
            id=f"table-filters-{country_id}",
            className="table-filter-bar",
            children=[
                # 1. Time of day range filter
                html.Div(
                    id=f"filter-time-wrap-{country_id}",
                    className="table-filter-item",
                    style={"display": "flex", "flexDirection": "column", "width": "28%", "flex": "0 0 28%"},
                    children=[
                        html.Div("Time of day", className="table-filter-label"),
                        html.Div(
                            className="table-filter-control-row",
                            children=[
                                dcc.Dropdown(
                                    id=f"filter-time-start-{country_id}",
                                    options=ALL_TIME_OPTIONS,
                                    value="00:00",
                                    clearable=False,
                                    searchable=True,
                                    className="table-filter-dropdown time-filter-dropdown flex-grow-1"
                                ),
                                html.Span("–", className="table-filter-sep"),
                                dcc.Dropdown(
                                    id=f"filter-time-end-{country_id}",
                                    options=ALL_TIME_OPTIONS,
                                    value="23:59",
                                    clearable=False,
                                    searchable=True,
                                    className="table-filter-dropdown time-filter-dropdown flex-grow-1"
                                )
                            ]
                        )
                    ]
                ),
                # 2a. Gender multi-select filter (shown on By Gender, left of Activity group)
                html.Div(
                    id=f"filter-gender-wrap-{country_id}",
                    className="table-filter-item",
                    style={"display": "none"},
                    children=[
                        html.Div("Gender", className="table-filter-label"),
                        html.Div(
                            className="table-filter-control-row",
                            children=[
                                dcc.Dropdown(
                                    id=f"filter-gender-{country_id}",
                                    options=[{"label": g, "value": g} for g in ["Male", "Female"]],
                                    value=[],
                                    multi=True,
                                    placeholder="All genders...",
                                    className="table-filter-dropdown w-100"
                                )
                            ]
                        )
                    ]
                ),
                # 2b. Age group multi-select filter (shown on By Age, left of Activity group)
                html.Div(
                    id=f"filter-age-wrap-{country_id}",
                    className="table-filter-item",
                    style={"display": "none"},
                    children=[
                        html.Div("Age group", className="table-filter-label"),
                        html.Div(
                            className="table-filter-control-row",
                            children=[
                                dcc.Dropdown(
                                    id=f"filter-age-{country_id}",
                                    options=[
                                        {"label": a, "value": a}
                                        for a in ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]
                                    ],
                                    value=[],
                                    multi=True,
                                    placeholder="All age groups...",
                                    className="table-filter-dropdown w-100"
                                )
                            ]
                        )
                    ]
                ),
                # 3. Activity group multi-select filter
                html.Div(
                    id=f"filter-act-wrap-{country_id}",
                    className="table-filter-item",
                    style={"display": "flex", "flexDirection": "column", "width": "46%", "flex": "0 0 46%"},
                    children=[
                        html.Div("Activity group", className="table-filter-label"),
                        html.Div(
                            className="table-filter-control-row",
                            children=[
                                dcc.Dropdown(
                                    id=f"filter-act-{country_id}",
                                    options=[{"label": a, "value": a} for a in CATEGORY_ORDER],
                                    value=[],
                                    multi=True,
                                    placeholder="All activities...",
                                    className="table-filter-dropdown w-100"
                                )
                            ]
                        )
                    ]
                ),
                # 4. Percentage range filter
                html.Div(
                    id=f"filter-pct-wrap-{country_id}",
                    className="table-filter-item",
                    style={"display": "flex", "flexDirection": "column", "width": "26%", "flex": "0 0 26%"},
                    children=[
                        html.Div("Percentage (%)", className="table-filter-label"),
                        html.Div(
                            className="table-filter-control-row",
                            children=[
                                dbc.Input(
                                    id=f"filter-pct-min-{country_id}",
                                    type="number",
                                    min=0,
                                    max=100,
                                    step=0.1,
                                    placeholder="Min",
                                    size="sm",
                                    className="table-filter-input flex-grow-1"
                                ),
                                html.Span("–", className="table-filter-sep"),
                                dbc.Input(
                                    id=f"filter-pct-max-{country_id}",
                                    type="number",
                                    min=0,
                                    max=100,
                                    step=0.1,
                                    placeholder="Max",
                                    size="sm",
                                    className="table-filter-input flex-grow-1"
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        dash_table.DataTable(
            id=f"datatable-{country_id}",
            data=[],
            columns=[],
            page_action="custom",
            page_current=0,
            page_size=17,
            page_count=1,
            sort_action="custom",
            sort_mode="single",
            sort_by=[],
            cell_selectable=False,
            style_as_list_view=True,
            style_table={
                "flex": "1",
                "minHeight": "0",
                "overflowY": "auto",
                "overflowX": "hidden",
                "backgroundColor": "#ffffff"
            },
            style_header={
                "backgroundColor": "#ffffff",
                "fontWeight": "700",
                "color": "#212529",
                "borderTop": "none",
                "borderLeft": "none",
                "borderRight": "none",
                "borderBottom": "2px solid #dee2e6",
                "textAlign": "left",
                "padding": "9px 12px",
                "fontFamily": "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
                "fontSize": "0.86rem"
            },
            style_cell={
                "textAlign": "left",
                "padding": "7px 12px",
                "fontFamily": "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
                "fontSize": "0.86rem",
                "color": "#333333",
                "borderLeft": "none",
                "borderRight": "none",
                "borderTop": "none",
                "borderBottom": "1px solid #e9ecef",
                "backgroundColor": "#ffffff",
                "whiteSpace": "normal",
                "height": "auto"
            },
            style_cell_conditional=[
                {"if": {"column_id": "Time of day"}, "width": "28%", "minWidth": "28%", "maxWidth": "28%"},
                {"if": {"column_id": "Activity group"}, "width": "46%", "minWidth": "46%", "maxWidth": "46%"},
                {"if": {"column_id": "Percentage"}, "width": "26%", "minWidth": "26%", "maxWidth": "26%", "textAlign": "right"}
            ],
            style_data_conditional=[
                {
                    "if": {"row_index": "even"},
                    "backgroundColor": "#f9f9f9"
                },
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#ffffff"
                },
                {
                    "if": {"column_id": "Percentage"},
                    "textAlign": "right"
                }
            ]
        )
    ]


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
                    html.Div(id="table-container-ca", className="graph-container", style={"display": "none"}, children=render_table_section("ca")),
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
                    html.Div(id="table-container-vn", className="graph-container", style={"display": "none"}, children=render_table_section("vn")),
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
                    html.Strong(
                        "Sell goods or\nprovide services" if act == "Sell goods or provide services" else act,
                        style={"width": "170px", "minWidth": "170px", "flexShrink": "0", "whiteSpace": "pre-line", "marginRight": "10px", "color": "#2c3e50"}
                    ),
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
            pt = click_payload["points"][0]
            clicked_act = pt.get("customdata") if pt.get("customdata") in COLORS else pt.get("y")
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
    [
        Input("btn-surprise", "n_clicks"),
        Input("btn-toggle-ca", "n_clicks"),
        Input("btn-toggle-vn", "n_clicks")
    ],
    [State("current-view", "data")],
    prevent_initial_call=False
)
def sync_view_state(surp_click, btn_ca, btn_vn, current_view):
    trig = ctx.triggered_id
    
    # Toggle between Bar Chart Race and Tempogram
    if trig == "btn-surprise":
        is_surprise = (current_view != "surprise")
    else:
        is_surprise = (current_view == "surprise")
        
    tabs_style = {"display": "block"}
    show_data_ca = bool(btn_ca and btn_ca % 2 == 1)
    show_data_vn = bool(btn_vn and btn_vn % 2 == 1)

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
        compare_note = "← To unlock, select a category\non the vertical axis."
        legend_style_ca = {"display": "none"}
        legend_style_vn = {"display": "none"}
        bcr_style_ca = {"display": "none"} if show_data_ca else {"display": "flex", "alignItems": "center"}
        bcr_style_vn = {"display": "none"} if show_data_vn else {"display": "flex", "alignItems": "center"}
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
        compare_note = "← To unlock, select a category\nin the legend."
        base_legend_style = {
            "display": "flex", "flexWrap": "wrap", "justifyContent": "center",
            "gap": "5px", "padding": "5px", "maxHeight": "80px", "overflowY": "auto"
        }
        legend_style_ca = {"display": "none"} if show_data_ca else base_legend_style
        legend_style_vn = {"display": "none"} if show_data_vn else base_legend_style
        bcr_style_ca = {"display": "none"}
        bcr_style_vn = {"display": "none"}
        
    return (
        new_view, root_class, title, tabs_style, btn_text, btn_color,
        hover_options, compare_note, legend_style_ca, legend_style_vn,
        bcr_style_ca, bcr_style_vn
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

# Long-format table cache for fast View Data rendering
_long_table_cache = {}

def _get_long_table_df(is_ca, chart_mode, tab_mode):
    tab_key = tab_mode or "overview"
    mode_key = "surprise" if (chart_mode == "surprise" and tab_key == "age") else "tempogram"
    cache_key = (bool(is_ca), mode_key, tab_key)
    if cache_key in _long_table_cache:
        return _long_table_cache[cache_key]

    idx_country = 0 if is_ca else 1
    df_ov = data_cache["overview"][idx_country]
    times = df_ov.index.strftime("%H:%M").to_numpy()
    acts = [a for a in CATEGORY_ORDER if a in df_ov.columns]
    n_acts = len(acts)
    n_times = len(times)

    if tab_key == "overview":
        col_time = np.repeat(times, n_acts)
        col_act = np.tile(acts, n_times)
        col_pct = df_ov[acts].to_numpy().ravel()
        long_df = pd.DataFrame({
            "Time of day": col_time,
            "Activity group": col_act,
            "_pct": col_pct,
            "_pct_round": np.round(col_pct, 1)
        })
        # Sort by Time of day first (asc), then by Percentage (desc)
        long_df = long_df.sort_values(
            by=["Time of day", "_pct"],
            ascending=[True, False],
            kind="mergesort"
        ).reset_index(drop=True)
        cols = [
            {"name": "Time of day", "id": "Time of day"},
            {"name": "Activity group", "id": "Activity group"},
            {"name": "Percentage", "id": "Percentage"}
        ]
    elif tab_key == "gender":
        df_dict = data_cache["gender"][idx_country]
        groups = ["Male", "Female"]
        n_groups = len(groups)
        col_time = np.repeat(times, n_groups * n_acts)
        col_group = np.tile(np.repeat(groups, n_acts), n_times)
        col_group_ord = np.tile(np.repeat(np.arange(n_groups), n_acts), n_times)
        col_act = np.tile(acts, n_times * n_groups)
        pct_vals = np.stack([df_dict[(g,)][acts].to_numpy() for g in groups], axis=1).ravel()
        long_df = pd.DataFrame({
            "Time of day": col_time,
            "Gender": col_group,
            "Activity group": col_act,
            "_group_ord": col_group_ord,
            "_pct": pct_vals,
            "_pct_round": np.round(pct_vals, 1)
        })
        # Sort by Time of day first (asc), then by Gender (Male, Female), then by Percentage (desc)
        long_df = long_df.sort_values(
            by=["Time of day", "_group_ord", "_pct"],
            ascending=[True, True, False],
            kind="mergesort"
        ).reset_index(drop=True)
        cols = [
            {"name": "Time of day", "id": "Time of day"},
            {"name": "Gender", "id": "Gender"},
            {"name": "Activity group", "id": "Activity group"},
            {"name": "Percentage", "id": "Percentage"}
        ]
    else:  # age
        if mode_key == "surprise":
            df_dict = data_cache["age_bcr"][idx_country]
            candidate_groups = ["15 to 24 years", "25 to 64 years"]
        else:
            df_dict = data_cache["age"][idx_country]
            candidate_groups = ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]
        groups = [
            g for g in candidate_groups
            if (g,) in df_dict and not df_dict[(g,)].empty and df_dict[(g,)].sum().sum() > 0
        ]
        n_groups = len(groups)
        col_time = np.repeat(times, n_groups * n_acts)
        col_group = np.tile(np.repeat(groups, n_acts), n_times)
        col_group_ord = np.tile(np.repeat(np.arange(n_groups), n_acts), n_times)
        col_act = np.tile(acts, n_times * n_groups)
        pct_vals = np.stack([df_dict[(g,)][acts].to_numpy() for g in groups], axis=1).ravel()
        long_df = pd.DataFrame({
            "Time of day": col_time,
            "Age group": col_group,
            "Activity group": col_act,
            "_group_ord": col_group_ord,
            "_pct": pct_vals,
            "_pct_round": np.round(pct_vals, 1)
        })
        # Sort by Time of day first (asc), then by Age group, then by Percentage (desc)
        long_df = long_df.sort_values(
            by=["Time of day", "_group_ord", "_pct"],
            ascending=[True, True, False],
            kind="mergesort"
        ).reset_index(drop=True)
        cols = [
            {"name": "Time of day", "id": "Time of day"},
            {"name": "Age group", "id": "Age group"},
            {"name": "Activity group", "id": "Activity group"},
            {"name": "Percentage", "id": "Percentage"}
        ]

    _long_table_cache[cache_key] = (long_df, cols)
    return long_df, cols


def _format_pct(v):
    val = round(float(v), 1)
    if val == 0:
        val = 0.0
    return f"{val:.1f}%"


def _build_table_slice(
    is_ca, chart_mode, tab_mode, page_current, page_size, sort_by,
    time_start="00:00", time_end="23:59", filter_gender=None, filter_age=None,
    filter_act=None, pct_min=None, pct_max=None, reset_page=False
):
    base_df, cols = _get_long_table_df(is_ca, chart_mode, tab_mode)
    work_df = base_df

    # 1. Time of day range filter
    t_start = time_start or "00:00"
    t_end = time_end or "23:59"
    if t_start > t_end:
        t_start, t_end = t_end, t_start
    if t_start != "00:00" or t_end != "23:59":
        work_df = work_df[(work_df["Time of day"] >= t_start) & (work_df["Time of day"] <= t_end)]

    # 2. Gender multi-select filter
    if (tab_mode or "overview") == "gender" and filter_gender:
        work_df = work_df[work_df["Gender"].isin(filter_gender)]

    # 3. Age group multi-select filter
    if (tab_mode or "overview") == "age" and filter_age:
        work_df = work_df[work_df["Age group"].isin(filter_age)]

    # 4. Activity group multi-select filter
    if filter_act:
        work_df = work_df[work_df["Activity group"].isin(filter_act)]

    # 5. Percentage range filter
    if pct_min is not None and pct_min != "":
        try:
            work_df = work_df[work_df["_pct_round"] >= float(pct_min)]
        except (ValueError, TypeError):
            pass
    if pct_max is not None and pct_max != "":
        try:
            work_df = work_df[work_df["_pct_round"] <= float(pct_max)]
        except (ValueError, TypeError):
            pass

    if sort_by and len(sort_by) > 0:
        col_id = sort_by[0].get("column_id")
        asc = (sort_by[0].get("direction") == "asc")
        sort_col = "_pct" if col_id == "Percentage" else col_id
        if sort_col in work_df.columns:
            work_df = work_df.sort_values(by=sort_col, ascending=asc, kind="mergesort")

    p_size = page_size or 17
    page_count = max(1, (len(work_df) + p_size - 1) // p_size)
    p_curr = 0 if reset_page else min(max(0, page_current or 0), page_count - 1)

    start = p_curr * p_size
    end = start + p_size
    slice_df = work_df.iloc[start:end].copy()
    slice_df["Percentage"] = [_format_pct(v) for v in slice_df["_pct"]]
    col_ids = [c["id"] for c in cols]
    records = slice_df[col_ids].to_dict("records")
    return records, cols, page_count, p_curr


# Data Table Filter Visibility, Column Width Alignment & Age Group Options Updater
@app.callback(
    [
        Output("filter-time-wrap-ca", "style"),
        Output("filter-gender-wrap-ca", "style"),
        Output("filter-age-wrap-ca", "style"),
        Output("filter-act-wrap-ca", "style"),
        Output("filter-pct-wrap-ca", "style"),
        Output("datatable-ca", "style_cell_conditional"),
        Output("filter-age-ca", "options"),
        Output("filter-age-ca", "value"),
        Output("filter-time-wrap-vn", "style"),
        Output("filter-gender-wrap-vn", "style"),
        Output("filter-age-wrap-vn", "style"),
        Output("filter-act-wrap-vn", "style"),
        Output("filter-pct-wrap-vn", "style"),
        Output("datatable-vn", "style_cell_conditional"),
        Output("filter-age-vn", "options"),
        Output("filter-age-vn", "value")
    ],
    [
        Input("current-view", "data"),
        Input("view-tabs", "active_tab")
    ],
    [
        State("filter-age-ca", "value"),
        State("filter-age-vn", "value")
    ]
)
def sync_table_filter_visibility(chart_mode, active_tab, age_val_ca, age_val_vn):
    tab_key = active_tab or "overview"

    def col_box(pct):
        return {"display": "flex", "flexDirection": "column", "width": pct, "flex": f"0 0 {pct}"}

    if tab_key == "gender":
        w_time, w_mid, w_act, w_pct = "27%", "21%", "30%", "22%"
        time_style = col_box(w_time)
        gender_style = col_box(w_mid)
        age_style = {"display": "none"}
        act_style = col_box(w_act)
        pct_style = col_box(w_pct)
        cell_cond = [
            {"if": {"column_id": "Time of day"}, "width": w_time, "minWidth": w_time, "maxWidth": w_time},
            {"if": {"column_id": "Gender"}, "width": w_mid, "minWidth": w_mid, "maxWidth": w_mid},
            {"if": {"column_id": "Activity group"}, "width": w_act, "minWidth": w_act, "maxWidth": w_act},
            {"if": {"column_id": "Percentage"}, "width": w_pct, "minWidth": w_pct, "maxWidth": w_pct, "textAlign": "right"}
        ]
    elif tab_key == "age":
        w_time, w_mid, w_act, w_pct = "27%", "24%", "27%", "22%"
        time_style = col_box(w_time)
        gender_style = {"display": "none"}
        age_style = col_box(w_mid)
        act_style = col_box(w_act)
        pct_style = col_box(w_pct)
        cell_cond = [
            {"if": {"column_id": "Time of day"}, "width": w_time, "minWidth": w_time, "maxWidth": w_time},
            {"if": {"column_id": "Age group"}, "width": w_mid, "minWidth": w_mid, "maxWidth": w_mid},
            {"if": {"column_id": "Activity group"}, "width": w_act, "minWidth": w_act, "maxWidth": w_act},
            {"if": {"column_id": "Percentage"}, "width": w_pct, "minWidth": w_pct, "maxWidth": w_pct, "textAlign": "right"}
        ]
    else:
        w_time, w_act, w_pct = "28%", "46%", "26%"
        time_style = col_box(w_time)
        gender_style = {"display": "none"}
        age_style = {"display": "none"}
        act_style = col_box(w_act)
        pct_style = col_box(w_pct)
        cell_cond = [
            {"if": {"column_id": "Time of day"}, "width": w_time, "minWidth": w_time, "maxWidth": w_time},
            {"if": {"column_id": "Activity group"}, "width": w_act, "minWidth": w_act, "maxWidth": w_act},
            {"if": {"column_id": "Percentage"}, "width": w_pct, "minWidth": w_pct, "maxWidth": w_pct, "textAlign": "right"}
        ]

    if chart_mode == "surprise":
        ages_ca = ["15 to 24 years", "25 to 64 years"]
        ages_vn = ["15 to 24 years", "25 to 64 years"]
    else:
        ages_ca = ["15 to 34 years", "35 to 54 years", "55 to 64 years", "65 years and over"]
        ages_vn = ["15 to 34 years", "35 to 54 years", "55 to 64 years"]

    opts_ca = [{"label": a, "value": a} for a in ages_ca]
    opts_vn = [{"label": a, "value": a} for a in ages_vn]
    valid_ca = [v for v in (age_val_ca or []) if v in ages_ca]
    valid_vn = [v for v in (age_val_vn or []) if v in ages_vn]

    return (
        time_style, gender_style, age_style, act_style, pct_style, cell_cond, opts_ca, valid_ca,
        time_style, gender_style, age_style, act_style, pct_style, cell_cond, opts_vn, valid_vn
    )


# Data Table View Toggle
@app.callback(
    [Output("chart-container-ca", "style"), Output("table-container-ca", "style"), Output("btn-toggle-ca", "children"),
     Output("chart-container-vn", "style"), Output("table-container-vn", "style"), Output("btn-toggle-vn", "children")],
    [Input("btn-toggle-ca", "n_clicks"), Input("btn-toggle-vn", "n_clicks")]
)
def toggle_data_view(btn_ca, btn_vn):
    def get_toggle_state(btn):
        show_data = bool(btn and btn % 2 == 1)
        if show_data:
            return (
                {"display": "none"},
                {
                    "display": "flex",
                    "flexDirection": "column",
                    "height": "100%",
                    "backgroundColor": "white",
                    "overflow": "hidden"
                },
                "View Chart"
            )
        else:
            return {"display": "block", "height": "100%"}, {"display": "none"}, "View Data"

    ca_chart, ca_table, ca_text = get_toggle_state(btn_ca)
    vn_chart, vn_table, vn_text = get_toggle_state(btn_vn)
    return ca_chart, ca_table, ca_text, vn_chart, vn_table, vn_text


# Data Table Content & Server-Side Pagination/Sorting/Filtering
@app.callback(
    [
        Output("datatable-ca", "data"),
        Output("datatable-ca", "columns"),
        Output("datatable-ca", "page_count"),
        Output("datatable-ca", "page_current"),
        Output("datatable-vn", "data"),
        Output("datatable-vn", "columns"),
        Output("datatable-vn", "page_count"),
        Output("datatable-vn", "page_current")
    ],
    [
        Input("current-view", "data"),
        Input("view-tabs", "active_tab"),
        Input("datatable-ca", "page_current"),
        Input("datatable-ca", "page_size"),
        Input("datatable-ca", "sort_by"),
        Input("filter-time-start-ca", "value"),
        Input("filter-time-end-ca", "value"),
        Input("filter-gender-ca", "value"),
        Input("filter-age-ca", "value"),
        Input("filter-act-ca", "value"),
        Input("filter-pct-min-ca", "value"),
        Input("filter-pct-max-ca", "value"),
        Input("datatable-vn", "page_current"),
        Input("datatable-vn", "page_size"),
        Input("datatable-vn", "sort_by"),
        Input("filter-time-start-vn", "value"),
        Input("filter-time-end-vn", "value"),
        Input("filter-gender-vn", "value"),
        Input("filter-age-vn", "value"),
        Input("filter-act-vn", "value"),
        Input("filter-pct-min-vn", "value"),
        Input("filter-pct-max-vn", "value")
    ]
)
def update_datatables(
    chart_mode, active_tab,
    page_ca, size_ca, sort_ca, t_start_ca, t_end_ca, f_gender_ca, f_age_ca, f_act_ca, p_min_ca, p_max_ca,
    page_vn, size_vn, sort_vn, t_start_vn, t_end_vn, f_gender_vn, f_age_vn, f_act_vn, p_min_vn, p_max_vn
):
    trig = ctx.triggered_id
    reset_ca = trig in [
        "current-view", "view-tabs",
        "filter-time-start-ca", "filter-time-end-ca",
        "filter-gender-ca", "filter-age-ca", "filter-act-ca",
        "filter-pct-min-ca", "filter-pct-max-ca"
    ]
    reset_vn = trig in [
        "current-view", "view-tabs",
        "filter-time-start-vn", "filter-time-end-vn",
        "filter-gender-vn", "filter-age-vn", "filter-act-vn",
        "filter-pct-min-vn", "filter-pct-max-vn"
    ]

    ca_data, ca_cols, ca_pcount, ca_pcurr = _build_table_slice(
        True, chart_mode, active_tab, page_ca, size_ca, sort_ca,
        time_start=t_start_ca, time_end=t_end_ca,
        filter_gender=f_gender_ca, filter_age=f_age_ca, filter_act=f_act_ca,
        pct_min=p_min_ca, pct_max=p_max_ca, reset_page=reset_ca
    )
    vn_data, vn_cols, vn_pcount, vn_pcurr = _build_table_slice(
        False, chart_mode, active_tab, page_vn, size_vn, sort_vn,
        time_start=t_start_vn, time_end=t_end_vn,
        filter_gender=f_gender_vn, filter_age=f_age_vn, filter_act=f_act_vn,
        pct_min=p_min_vn, pct_max=p_max_vn, reset_page=reset_vn
    )
    return ca_data, ca_cols, ca_pcount, ca_pcurr, vn_data, vn_cols, vn_pcount, vn_pcurr


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
    dash.ClientsideFunction(namespace="bcr", function_name="playPause"),
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
