"""
API Routes - Chart data and AI endpoints
Organized by dashboard page
"""

import pandas as pd
from flask import Blueprint, jsonify, request, send_file
import io

from data_service import (
    get_filtered_df, get_df, get_general_waste_df,
    get_waste_labels, get_waste_colors,
    calculate_overview_kpis, calculate_shift_kpis,
    # Costs page
    get_cost_by_waste_type, get_cost_trend, get_cost_by_department, get_recycling_vs_landfill_cost,
    # Emissions page
    get_emissions_by_waste_type, get_emissions_trend, get_recycling_vs_landfill, get_emissions_by_source,
    # Departments Page
    get_department_mom_changes
)
from optimization_service import (
    get_optimization_kpis, get_treatment_allocation, get_pareto_frontier, get_routing_table
)
from forecasting_service import (
    get_forecast_kpis, get_forecast_with_bands, get_seasonal_patterns, get_monthly_comparison
)
from ai_service import get_recommendation, chat_with_ai


api_bp = Blueprint('api', __name__)


# ============================================
# UTILITIES
# ============================================

def get_filter_params():
    """Extract filter parameters from request"""
    period = request.args.get('period', 'monthly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    return period, start_date, end_date


# ============================================
# PAGE 1: OVERVIEW
# ============================================

@api_bp.route('/waste-composition')
def waste_composition():
    """Pie chart: waste by type"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    composition = df.groupby('Waste Bag')['Total_Weight_kg'].sum().to_dict()
    labels = get_waste_labels()
    colors = get_waste_colors()
    
    return jsonify({
        'data': composition,
        'labels': {k: labels.get(k, k) for k in composition.keys()},
        'colors': {k: colors.get(k, '#888888') for k in composition.keys()}
    })


@api_bp.route('/combined-waste-trend')
def combined_waste_trend():
    """Line chart: combined hazardous + general waste over time"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    general_df = get_general_waste_df()
    
    if df.empty:
        return jsonify({'labels': [], 'hazardous': [], 'general': [], 'total': []})
    
    haz_monthly = df.groupby(['Year', 'Month'])['Total_Weight_kg'].sum().reset_index()
    haz_monthly['date'] = haz_monthly.apply(lambda x: f"{int(x['Year'])}-{int(x['Month']):02d}", axis=1)
    
    dates = sorted(haz_monthly['date'].unique())
    haz_dict = haz_monthly.set_index('date')['Total_Weight_kg'].to_dict()
    hazardous = [float(round(haz_dict.get(d, 0), 1)) for d in dates]
    
    general = []
    if not general_df.empty and 'Year' in general_df.columns and 'Month_Num' in general_df.columns:
        for d in dates:
            year, month = int(d.split('-')[0]), int(d.split('-')[1])
            gen_match = general_df[(general_df['Year'] == year) & (general_df['Month_Num'] == month)]
            if not gen_match.empty and 'Total Weight (kg)' in gen_match.columns:
                general.append(float(round(gen_match['Total Weight (kg)'].sum(), 1)))
            else:
                general.append(0)
    else:
        general = [0] * len(dates)
    
    total = [float(round(h + g, 1)) for h, g in zip(hazardous, general)]
    
    return jsonify({'labels': dates, 'hazardous': hazardous, 'general': general, 'total': total})


@api_bp.route('/waste-trend')
def waste_trend():
    """Line chart: total waste over time"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'labels': [], 'values': []})
    
    date_range = (df['Date'].max() - df['Date'].min()).days
    
    if date_range <= 60:
        daily = df.groupby('Date')['Total_Weight_kg'].sum().reset_index()
        daily['date_str'] = daily['Date'].dt.strftime('%b %d')
        return jsonify({'labels': daily['date_str'].tolist(), 'values': daily['Total_Weight_kg'].round(1).tolist()})
    else:
        monthly = df.groupby(['Year', 'Month'])['Total_Weight_kg'].sum().reset_index()
        monthly['date'] = monthly.apply(lambda x: f"{int(x['Year'])}-{int(x['Month']):02d}", axis=1)
        return jsonify({'labels': monthly['date'].tolist(), 'values': monthly['Total_Weight_kg'].round(1).tolist()})


@api_bp.route('/waste-by-type-trend')
def waste_by_type_trend():
    """Stacked chart: waste types over time"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    labels = get_waste_labels()
    colors = get_waste_colors()
    
    if df.empty:
        return jsonify({'labels': [], 'datasets': {}, 'waste_labels': labels, 'waste_colors': colors})
    
    date_range = (df['Date'].max() - df['Date'].min()).days
    
    if date_range <= 60:
        daily = df.groupby(['Date', 'Waste Bag'])['Total_Weight_kg'].sum().reset_index()
        daily['date_str'] = daily['Date'].dt.strftime('%b %d')
        dates = sorted(daily['date_str'].unique())
        waste_types = df['Waste Bag'].dropna().unique().tolist()
        
        datasets = {}
        for wt in waste_types:
            wt_data = daily[daily['Waste Bag'] == wt].set_index('date_str')['Total_Weight_kg']
            datasets[wt] = [round(wt_data.get(d, 0), 1) for d in dates]
    else:
        monthly = df.groupby(['Year', 'Month', 'Waste Bag'])['Total_Weight_kg'].sum().reset_index()
        monthly['date'] = monthly.apply(lambda x: f"{int(x['Year'])}-{int(x['Month']):02d}", axis=1)
        dates = sorted(monthly['date'].unique())
        waste_types = df['Waste Bag'].dropna().unique().tolist()
        
        datasets = {}
        for wt in waste_types:
            wt_data = monthly[monthly['Waste Bag'] == wt].set_index('date')['Total_Weight_kg']
            datasets[wt] = [round(wt_data.get(d, 0), 1) for d in dates]
    
    return jsonify({'labels': dates, 'datasets': datasets, 'waste_labels': labels, 'waste_colors': colors})


@api_bp.route('/waste-by-department')
def waste_by_department():
    """Bar chart: waste by department (top 10)"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'labels': [], 'values': []})
    
    dept_waste = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False).head(10)
    return jsonify({'labels': dept_waste.index.tolist(), 'values': dept_waste.round(1).tolist()})


# ============================================
# PAGE 2: DEPARTMENTS
# ============================================

@api_bp.route('/department-mom-changes')
def department_mom_changes():
    """Month-over-month change per department"""
    return jsonify(get_department_mom_changes())


@api_bp.route('/shift-by-department')
def shift_by_department():
    """Grouped bar: shift breakdown per top 10 departments"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'departments': [], 'shift_a': [], 'shift_b': [], 'shift_c': []})
    
    dept_totals = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_depts = dept_totals.head(10).index.tolist()
    df_filtered = df[df['Department'].isin(top_depts)]
    
    shift_a_col = [c for c in df.columns if 'Shift A' in c and 'Weight' in c][0]
    shift_b_col = [c for c in df.columns if 'Shift B' in c and 'Weight' in c][0]
    shift_c_col = [c for c in df.columns if 'Shift C' in c and 'Weight' in c][0]
    
    shift_data = df_filtered.groupby('Department').agg({
        shift_a_col: 'sum', shift_b_col: 'sum', shift_c_col: 'sum'
    }).reindex(top_depts)
    
    return jsonify({
        'departments': top_depts,
        'shift_a': [float(round(v, 1)) for v in shift_data[shift_a_col].values],
        'shift_b': [float(round(v, 1)) for v in shift_data[shift_b_col].values],
        'shift_c': [float(round(v, 1)) for v in shift_data[shift_c_col].values]
    })


@api_bp.route('/department-heatmap')
def department_heatmap():
    """Heatmap: departments x waste types (top 5 + bottom 5)"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'departments': [], 'waste_types': [], 'data': [], 'divider_index': 0})
    
    dept_totals = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_5 = dept_totals.head(5).index.tolist()
    bottom_5 = dept_totals.tail(5).index.tolist()
    selected_depts = top_5 + bottom_5
    
    df_filtered = df[df['Department'].isin(selected_depts)]
    pivot = df_filtered.groupby(['Department', 'Waste Bag'])['Total_Weight_kg'].sum().unstack(fill_value=0)
    pivot = pivot.reindex(selected_depts)
    
    waste_types = pivot.columns.tolist()
    departments = pivot.index.tolist()
    data = [[float(round(pivot.loc[dept, wt], 1)) for wt in waste_types] for dept in departments]
    
    return jsonify({'departments': departments, 'waste_types': waste_types, 'data': data, 'divider_index': 5})


@api_bp.route('/department-month-heatmap')
def department_month_heatmap():
    """Heatmap: departments x months"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'departments': [], 'months': [], 'data': [], 'max_value': 0})
    
    dept_totals = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_depts = dept_totals.head(10).index.tolist()
    df_filtered = df[df['Department'].isin(top_depts)]
    
    df_filtered = df_filtered.copy()
    df_filtered['Month_Label'] = df_filtered['Date'].dt.strftime('%b %Y')
    pivot = df_filtered.groupby(['Department', 'Month_Label'])['Total_Weight_kg'].sum().unstack(fill_value=0)
    pivot = pivot.reindex(top_depts)
    
    months = pivot.columns.tolist()
    departments = pivot.index.tolist()
    data = [[float(round(pivot.loc[dept, m], 1)) for m in months] for dept in departments]
    max_value = float(pivot.values.max()) if pivot.values.size > 0 else 0
    
    return jsonify({'departments': departments, 'months': months, 'data': data, 'max_value': max_value})


@api_bp.route('/department-trend')
def department_trend():
    """Line chart: top 5 + bottom 5 departments over time"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'labels': [], 'datasets': {}, 'top_depts': [], 'bottom_depts': []})
    
    dept_totals = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_5 = dept_totals.head(5).index.tolist()
    bottom_5 = dept_totals.tail(5).index.tolist()
    selected_depts = top_5 + bottom_5
    
    df_filtered = df[df['Department'].isin(selected_depts)]
    monthly = df_filtered.groupby(['Year', 'Month', 'Department'])['Total_Weight_kg'].sum().reset_index()
    monthly['date'] = monthly.apply(lambda x: f"{int(x['Year'])}-{int(x['Month']):02d}", axis=1)
    
    dates = sorted(monthly['date'].unique())
    datasets = {}
    for dept in selected_depts:
        dept_data = monthly[monthly['Department'] == dept].set_index('date')['Total_Weight_kg']
        datasets[dept] = [float(round(dept_data.get(d, 0), 1)) for d in dates]
    
    return jsonify({'labels': dates, 'datasets': datasets, 'top_depts': top_5, 'bottom_depts': bottom_5})


@api_bp.route('/department-table')
def department_table():
    """Table: all departments with total waste"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'departments': []})
    
    dept_waste = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    departments = [{'name': dept, 'total_waste': float(round(waste, 1))} for dept, waste in dept_waste.items()]
    
    return jsonify({'departments': departments})


@api_bp.route('/department-pie')
def department_pie():
    """Pie chart: all departments waste contribution"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'labels': [], 'values': []})
    
    dept_waste = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    return jsonify({'labels': dept_waste.index.tolist(), 'values': [float(round(v, 1)) for v in dept_waste.values]})


@api_bp.route('/department-breakdown')
def department_breakdown():
    """Detailed department data"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'departments': [], 'weights': [], 'costs': [], 'emissions': [], 'bags': []})
    
    dept_data = df.groupby('Department').agg({
        'Total_Weight_kg': 'sum', 'Total_Cost_USD': 'sum',
        'Total_Emissions_kgCO2e': 'sum', 'Total_Bags': 'sum'
    }).sort_values('Total_Weight_kg', ascending=False).head(15)
    
    return jsonify({
        'departments': dept_data.index.tolist(),
        'weights': dept_data['Total_Weight_kg'].round(1).tolist(),
        'costs': dept_data['Total_Cost_USD'].round(2).tolist(),
        'emissions': dept_data['Total_Emissions_kgCO2e'].round(2).tolist(),
        'bags': dept_data['Total_Bags'].astype(int).tolist()
    })


@api_bp.route('/shift-comparison')
def shift_comparison():
    """Bar chart: shift comparison"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_shift_kpis(period, start_date, end_date)
    
    if not kpis:
        return jsonify({'labels': [], 'weights': [], 'bags': []})
    
    return jsonify({
        'labels': ['Shift A', 'Shift B', 'Shift C'],
        'weights': [kpis['shift_a_weight'], kpis['shift_b_weight'], kpis['shift_c_weight']],
        'bags': [kpis['shift_a_bags'], kpis['shift_b_bags'], kpis['shift_c_bags']]
    })


# ============================================
# PAGE 3: HAZARDOUS
# ============================================

@api_bp.route('/hazardous-by-department')
def hazardous_by_department():
    """Bar chart: Red + Blue waste per department (top 10)"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'departments': [], 'red': [], 'blue': []})
    
    hazardous_df = df[df['Waste Bag'].isin(['Red', 'Blue'])]
    dept_totals = hazardous_df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_depts = dept_totals.head(10).index.tolist()
    
    dept_red = hazardous_df[hazardous_df['Waste Bag'] == 'Red'].groupby('Department')['Total_Weight_kg'].sum()
    dept_blue = hazardous_df[hazardous_df['Waste Bag'] == 'Blue'].groupby('Department')['Total_Weight_kg'].sum()
    
    return jsonify({
        'departments': top_depts,
        'red': [float(round(dept_red.get(d, 0), 1)) for d in top_depts],
        'blue': [float(round(dept_blue.get(d, 0), 1)) for d in top_depts]
    })


@api_bp.route('/bag-count-vs-weight')
def bag_count_vs_weight():
    """Clustered bar: bag count vs weight per waste type"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'types': [], 'bags': [], 'weights': []})
    
    waste_types = ['Yellow', 'Red', 'Blue']
    bags, weights = [], []
    
    for wt in waste_types:
        wt_df = df[df['Waste Bag'] == wt]
        bags.append(int(wt_df['Total_Bags'].sum()))
        weights.append(float(round(wt_df['Total_Weight_kg'].sum(), 1)))
    
    return jsonify({'types': waste_types, 'bags': bags, 'weights': weights})


@api_bp.route('/avg-weight-per-bag')
def avg_weight_per_bag():
    """Table: average weight per bag by waste type"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'data': []})
    
    labels = get_waste_labels()
    data = []
    
    for wt in ['Yellow', 'Red', 'Blue']:
        wt_df = df[df['Waste Bag'] == wt]
        total_bags = wt_df['Total_Bags'].sum()
        total_weight = wt_df['Total_Weight_kg'].sum()
        avg_weight = total_weight / total_bags if total_bags > 0 else 0
        data.append({'type': labels.get(wt, wt), 'bags': int(total_bags), 'avg_kg': round(avg_weight, 2)})
    
    # Total row
    total_bags = df['Total_Bags'].sum()
    total_weight = df['Total_Weight_kg'].sum()
    data.append({'type': 'Total', 'bags': int(total_bags), 'avg_kg': round(total_weight / total_bags if total_bags > 0 else 0, 2)})
    
    return jsonify({'data': data})


@api_bp.route('/hazardous-trend')
def hazardous_trend():
    """Line chart: hazardous waste types over time"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'labels': [], 'datasets': {}})
    
    labels = get_waste_labels()
    colors = get_waste_colors()
    
    monthly = df.groupby(['Year', 'Month', 'Waste Bag'])['Total_Weight_kg'].sum().reset_index()
    monthly['date'] = monthly.apply(lambda x: f"{int(x['Year'])}-{int(x['Month']):02d}", axis=1)
    dates = sorted(monthly['date'].unique())
    
    datasets = {}
    for wt in ['Yellow', 'Red', 'Blue']:
        wt_data = monthly[monthly['Waste Bag'] == wt].set_index('date')['Total_Weight_kg']
        datasets[wt] = [float(round(wt_data.get(d, 0), 1)) for d in dates]
    
    return jsonify({'labels': dates, 'datasets': datasets, 'waste_labels': labels, 'waste_colors': colors})


@api_bp.route('/emissions-breakdown')
def emissions_breakdown():
    """Pie chart: Transport vs Disposal emissions"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'labels': [], 'values': []})
    
    transport = float(round(df['Transport_Emissions_kgCO2e'].sum(), 1))
    disposal = float(round(df['Disposal_Emissions_kgCO2e'].sum(), 1))
    
    return jsonify({'labels': ['Transport', 'Disposal'], 'values': [transport, disposal]})


# ============================================
# PAGE 4: COSTS
# ============================================

@api_bp.route('/cost-by-waste-type')
def cost_by_waste_type():
    """Donut: cost by waste stream"""
    period, start_date, end_date = get_filter_params()
    return jsonify(get_cost_by_waste_type(period, start_date, end_date))


@api_bp.route('/cost-trend')
def cost_trend():
    """Line: cost trend over time (2024-2025)"""
    return jsonify(get_cost_trend())


@api_bp.route('/cost-by-department')
def cost_by_department():
    """Horizontal bar: top 10 departments by cost"""
    period, start_date, end_date = get_filter_params()
    return jsonify(get_cost_by_department(period, start_date, end_date))


@api_bp.route('/recycling-vs-landfill-cost')
def recycling_vs_landfill_cost():
    """Clustered bar: recycling vs landfill cost"""
    return jsonify(get_recycling_vs_landfill_cost())


# ============================================
# PAGE 5: EMISSIONS
# ============================================

@api_bp.route('/emissions-by-waste-type')
def emissions_by_waste_type():
    """Stacked bar: emissions by waste type"""
    period, start_date, end_date = get_filter_params()
    return jsonify(get_emissions_by_waste_type(period, start_date, end_date))


@api_bp.route('/emissions-trend')
def emissions_trend():
    """Line: emissions trend (2024-2025)"""
    return jsonify(get_emissions_trend())


@api_bp.route('/recycling-vs-landfill')
def recycling_vs_landfill():
    """Grouped bar: recycling vs landfill emissions"""
    return jsonify(get_recycling_vs_landfill())


@api_bp.route('/emissions-by-source')
def emissions_by_source():
    """Stacked area: emissions by source"""
    return jsonify(get_emissions_by_source())


# ============================================
# PAGE 6: TRENDS & FORECASTING
# ============================================

@api_bp.route('/forecast-kpis')
def forecast_kpis():
    """KPIs for forecasting page"""
    return jsonify(get_forecast_kpis())


@api_bp.route('/forecast-with-bands')
def forecast_with_bands():
    """Daily forecast with P10-P90 confidence bands"""
    return jsonify(get_forecast_with_bands())


@api_bp.route('/seasonal-patterns')
def seasonal_patterns():
    """Monthly waste by year (2022-2025)"""
    return jsonify(get_seasonal_patterns())


@api_bp.route('/monthly-comparison')
def monthly_comparison():
    """2025 actual vs 2026 forecast by month"""
    return jsonify(get_monthly_comparison())


@api_bp.route('/forecast-trend')
def forecast_trend():
    """Line chart: actual vs predicted waste (legacy)"""
    import numpy as np
    
    df = get_df()
    if df.empty:
        return jsonify({'labels': [], 'actual': [], 'predicted': []})
    
    monthly = df.groupby(['Year', 'Month'])['Total_Weight_kg'].sum().reset_index()
    monthly['date'] = monthly.apply(lambda x: f"{int(x['Year'])}-{int(x['Month']):02d}", axis=1)
    monthly['month_num'] = range(len(monthly))
    
    if len(monthly) < 3:
        return jsonify({'labels': [], 'actual': [], 'predicted': []})
    
    x, y = monthly['month_num'].values, monthly['Total_Weight_kg'].values
    n = len(x)
    m = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
    b = (np.sum(y) - m * np.sum(x)) / n
    
    predicted = [float(round(m * i + b, 1)) for i in range(n + 1)]
    actual = [float(round(v, 1)) for v in y.tolist()] + [None]
    
    labels = monthly['date'].tolist()
    last_year, last_month = int(monthly.iloc[-1]['Year']), int(monthly.iloc[-1]['Month'])
    next_label = f"{last_year + 1}-01" if last_month == 12 else f"{last_year}-{last_month + 1:02d}"
    labels.append(next_label)
    
    return jsonify({'labels': labels, 'actual': actual, 'predicted': predicted})


@api_bp.route('/seasonal-heatmap')
def seasonal_heatmap():
    """Heatmap: month x year waste patterns"""
    df = get_df()
    
    if df.empty:
        return jsonify({'years': [], 'months': [], 'data': []})
    
    pivot = df.groupby(['Year', 'Month'])['Total_Weight_kg'].sum().unstack(fill_value=0)
    years = [int(y) for y in pivot.index.tolist()]
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    data = []
    for year in pivot.index:
        row = [float(round(pivot.loc[year, m], 1)) if m in pivot.columns else 0 for m in range(1, 13)]
        data.append(row)
    
    return jsonify({'years': years, 'months': months, 'data': data})


# ============================================
# PAGE 7: OPTIMIZATION
# ============================================

@api_bp.route('/optimization-kpis')
def optimization_kpis():
    """KPIs for selected optimization strategy"""
    strategy = request.args.get('strategy', 'recommended')
    return jsonify(get_optimization_kpis(strategy))


@api_bp.route('/optimization-allocation')
def optimization_allocation():
    """Treatment allocation data for stacked bar chart"""
    strategy = request.args.get('strategy', 'recommended')
    return jsonify(get_treatment_allocation(strategy))


@api_bp.route('/optimization-pareto')
def optimization_pareto():
    """Pareto frontier points for selected strategy"""
    strategy = request.args.get('strategy', 'recommended')
    return jsonify(get_pareto_frontier(strategy))


@api_bp.route('/optimization-routing')
def optimization_routing():
    """Routing table data"""
    strategy = request.args.get('strategy', 'recommended')
    return jsonify(get_routing_table(strategy))


# ============================================
# AI ENDPOINTS
# ============================================

@api_bp.route('/ai-recommendation', methods=['POST'])
def ai_recommendation():
    """Get AI recommendation based on screenshot and KPIs"""
    data = request.json
    context = data.get('context', data.get('page', 'overview'))
    period = data.get('period', 'monthly')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    screenshot = data.get('screenshot')  # ADD THIS
    
    kpis = calculate_overview_kpis(period, start_date, end_date)
    recommendation = get_recommendation(
        kpis, 
        context,
        screenshot_base64=screenshot,  # ADD THIS
        period=period
    )
    
    return jsonify({'recommendation': recommendation})


@api_bp.route('/ai-chat', methods=['POST'])
def ai_chat():
    """Handle user questions to AI with screenshot support"""
    data = request.json
    question = data.get('question', '')
    context = data.get('context', data.get('page', 'overview'))
    period = data.get('period', 'monthly')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    screenshot = data.get('screenshot')  # ADD THIS
    
    if not question.strip():
        return jsonify({'response': 'Please enter a question.'}), 400
    
    kpis = calculate_overview_kpis(period, start_date, end_date)
    response = chat_with_ai(
        kpis, 
        question, 
        context,
        screenshot_base64=screenshot,  # ADD THIS
        period=period
    )
    
    return jsonify({'response': response})


# ============================================
# EXPORTS
# ============================================

@api_bp.route('/export/department-heatmap')
def export_department_heatmap():
    """Export department heatmap as Excel"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'error': 'No data available'}), 404
    
    dept_totals = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_5 = dept_totals.head(5).index.tolist()
    bottom_5 = dept_totals.tail(5).index.tolist()
    selected_depts = top_5 + bottom_5
    
    df_filtered = df[df['Department'].isin(selected_depts)]
    pivot = df_filtered.groupby(['Department', 'Waste Bag'])['Total_Weight_kg'].sum().unstack(fill_value=0)
    pivot = pivot.reindex(selected_depts)
    pivot['Total'] = pivot.sum(axis=1)
    pivot = pivot.reset_index()
    pivot.insert(1, 'Category', ['Top 5']*5 + ['Bottom 5']*5)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pivot.to_excel(writer, sheet_name='Department Waste by Type', index=False)
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=f"department_waste_by_type_{period}.xlsx")


@api_bp.route('/export/department-trend')
def export_department_trend():
    """Export department trend as Excel"""
    period, start_date, end_date = get_filter_params()
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return jsonify({'error': 'No data available'}), 404
    
    dept_totals = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_5 = dept_totals.head(5).index.tolist()
    bottom_5 = dept_totals.tail(5).index.tolist()
    selected_depts = top_5 + bottom_5
    
    df_filtered = df[df['Department'].isin(selected_depts)]
    monthly = df_filtered.groupby(['Year', 'Month', 'Department'])['Total_Weight_kg'].sum().reset_index()
    monthly['Date'] = monthly.apply(lambda x: f"{int(x['Year'])}-{int(x['Month']):02d}", axis=1)
    
    pivot = monthly.pivot(index='Date', columns='Department', values='Total_Weight_kg').fillna(0)
    pivot = pivot[selected_depts]
    pivot = pivot.reset_index()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pivot.to_excel(writer, sheet_name='Department Waste Trend', index=False)
        summary = pd.DataFrame({
            'Department': selected_depts,
            'Category': ['Top 5']*5 + ['Bottom 5']*5,
            'Total Waste (kg)': [dept_totals[d] for d in selected_depts]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=f"department_waste_trend_{period}.xlsx")


@api_bp.route('/export/optimization-routing')
def export_optimization_routing():
    """Export routing table as Excel"""
    strategy = request.args.get('strategy', 'recommended')
    rows = get_routing_table(strategy)
    
    df = pd.DataFrame(rows)
    df.columns = ['Waste Stream', 'Volume (kg/yr)', 'Treatment', 'Annual Cost ($)', 
                  'CO₂e (kg)', 'Flexibility', 'Compliant']
    df['Compliant'] = df['Compliant'].apply(lambda x: '✓ Compliant' if x else '✗ Non-compliant')
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Optimization Routing', index=False)
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=f"optimization_routing_{strategy}.xlsx")