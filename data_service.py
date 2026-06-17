"""
Data Service - Medical Waste Dashboard
Central data processing logic organized by dashboard page
"""

import pandas as pd
import os
from datetime import datetime, timedelta


# ============================================
# CONFIGURATION & CONSTANTS
# ============================================

WASTE_TYPES = ['Yellow', 'Blue', 'Red']

WASTE_LABELS = {
    'Yellow': 'Infectious & Anatomical (Yellow)',
    'Red': 'Highly Infectious (Red)',
    'Blue': 'Chemotherapy (Blue)'
}

WASTE_COLORS = {
    'Yellow': '#eab308',
    'Red': '#ef4444',
    'Blue': '#3b82f6'
}

HAZARDOUS_TYPES = ['Yellow', 'Blue', 'Red']

MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


# ============================================
# DATA LOADING
# ============================================

_df = None
_general_waste_df = None


def load_data(filepath=None):
    """Load medical waste data from Excel file"""
    global _df
    
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), 'data', 'Medical_Waste_2022_2025_Updated.xlsx')
    
    if os.path.exists(filepath):
        _df = pd.read_excel(filepath)
        
        _df['Date'] = pd.to_datetime(_df['Date'])
        _df['Year'] = _df['Date'].dt.year
        _df['Month'] = _df['Date'].dt.month
        _df['Day'] = _df['Date'].dt.day
        
        _df['Total_Weight_kg'] = (
            _df['Shift A - Weight (kg)'].fillna(0) + 
            _df['Shift B - Weight (kg)'].fillna(0) + 
            _df['Shift C - Weight (kg)'].fillna(0)
        )
        
        _df['Total_Bags'] = (
            _df['Shift A - No.'].fillna(0) + 
            _df['Shift B - No.'].fillna(0) + 
            _df['Shift C - No.'].fillna(0)
        )
        
        _df['Department'] = _df['Department'].astype(str).str.strip()
        _df['Waste Bag'] = _df['Waste Bag'].astype(str).str.strip()
        
        print(f"Data loaded: {len(_df)} rows")
    else:
        print(f"Data file not found: {filepath}")
        _df = pd.DataFrame()
    
    return _df


def load_general_waste_data():
    """Load general waste data from Excel file"""
    global _general_waste_df
    
    if _general_waste_df is None:
        try:
            _general_waste_df = pd.read_excel('data/General Waste_Cost_Emissions_2024_2025.xlsx')
            
            month_map = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                'May': 5, 'June': 6, 'July': 7, 'August': 8,
                'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            if 'Month' in _general_waste_df.columns:
                _general_waste_df['Month_Num'] = _general_waste_df['Month'].map(month_map)
            
            if 'Year' in _general_waste_df.columns and 'Month_Num' in _general_waste_df.columns:
                _general_waste_df['Date'] = pd.to_datetime(
                    _general_waste_df['Year'].astype(str) + '-' + 
                    _general_waste_df['Month_Num'].astype(str) + '-01'
                )
            
            print(f"General waste data loaded: {len(_general_waste_df)} rows")
            print(f"General waste columns: {_general_waste_df.columns.tolist()}")
            print(f"Month_Num values: {_general_waste_df['Month_Num'].unique()}")
            
        except Exception as e:
            print(f"Error loading general waste data: {e}")
            _general_waste_df = pd.DataFrame()
    
    return _general_waste_df


def get_df():
    """Get medical waste dataframe"""
    global _df
    if _df is None:
        load_data()
    return _df


def get_general_waste_df():
    """Get general waste dataframe"""
    return load_general_waste_data().copy()


def get_waste_labels():
    return WASTE_LABELS


def get_waste_colors():
    return WASTE_COLORS


# ============================================
# CORE FILTERING UTILITIES
# ============================================

def get_filtered_df(period='monthly', start_date=None, end_date=None):
    """Filter medical waste dataframe by time period"""
    df = get_df()
    
    if df.empty:
        return df
    
    if period == 'custom' and start_date and end_date:
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)
        return df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
    
    if period == 'monthly':
        current_year = df['Year'].max()
        current_month = df[df['Year'] == current_year]['Month'].max()
        return df[(df['Year'] == current_year) & (df['Month'] == current_month)]
    
    elif period == 'yearly':
        current_year = df['Year'].max()
        return df[df['Year'] == current_year]
    
    elif period == 'daily':
        max_date = df['Date'].max()
        min_date = max_date - timedelta(days=30)
        return df[df['Date'] >= min_date]
    
    return df


def filter_general_waste(gen_df, period, start_date=None, end_date=None):
    """Filter general waste dataframe to match period"""
    full_df = get_df()
    
    if period == 'monthly':
        current_year = full_df['Year'].max()
        current_month = full_df[full_df['Year'] == current_year]['Month'].max()
        return gen_df[(gen_df['Year'] == current_year) & (gen_df['Month_Num'] == current_month)]
    
    elif period == 'yearly':
        current_year = full_df['Year'].max()
        return gen_df[gen_df['Year'] == current_year]
    
    elif period == 'custom' and start_date and end_date:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        return gen_df[(gen_df['Date'] >= start) & (gen_df['Date'] <= end)]
    
    else:
        current_year = full_df['Year'].max()
        return gen_df[gen_df['Year'] == current_year]


def get_total_weight_from_shifts(df):
    """Calculate total weight from shift columns"""
    shift_a_col = [c for c in df.columns if 'Shift A' in c and 'Weight' in c]
    shift_b_col = [c for c in df.columns if 'Shift B' in c and 'Weight' in c]
    shift_c_col = [c for c in df.columns if 'Shift C' in c and 'Weight' in c]
    
    weight = 0
    if shift_a_col:
        weight += float(df[shift_a_col[0]].sum())
    if shift_b_col:
        weight += float(df[shift_b_col[0]].sum())
    if shift_c_col:
        weight += float(df[shift_c_col[0]].sum())
    
    return weight


# ============================================
# PAGE 1: OVERVIEW
# ============================================

def calculate_overview_kpis(period='monthly', start_date=None, end_date=None):
    """KPIs for Overview page - combines hazardous + general waste"""
    df = get_filtered_df(period, start_date, end_date)
    full_df = get_df()
    general_df = get_general_waste_df()
    
    if df.empty:
        return {
            'total_waste': 0, 'total_bags': 0, 'waste_by_type': {},
            'total_cost': 0, 'monthly_cost': 0, 'prev_month_cost': 0,
            'yearly_waste': 0, 'monthly_waste': 0, 'total_emissions': 0,
            'avg_daily_waste': 0, 'month_change': 0, 'unique_days': 0
        }
    
    current_year = full_df['Year'].max()
    current_month = full_df[full_df['Year'] == current_year]['Month'].max()
    
    if current_month > 1:
        prev_month, prev_year = current_month - 1, current_year
    else:
        prev_month, prev_year = 12, current_year - 1
    
    # Hazardous data
    haz_total_waste = df['Total_Weight_kg'].sum()
    haz_total_cost = df['Total_Cost_USD'].sum()
    haz_total_emissions = df['Total_Emissions_kgCO2e'].sum()
    total_bags = df['Total_Bags'].sum()
    waste_by_type = df.groupby('Waste Bag')['Total_Weight_kg'].sum().to_dict()
    unique_days = df['Date'].nunique()
    
    haz_monthly_waste = full_df[(full_df['Year'] == current_year) & (full_df['Month'] == current_month)]['Total_Weight_kg'].sum()
    haz_monthly_cost = full_df[(full_df['Year'] == current_year) & (full_df['Month'] == current_month)]['Total_Cost_USD'].sum()
    haz_prev_month_cost = full_df[(full_df['Year'] == prev_year) & (full_df['Month'] == prev_month)]['Total_Cost_USD'].sum()
    haz_prev_month_waste = full_df[(full_df['Year'] == prev_year) & (full_df['Month'] == prev_month)]['Total_Weight_kg'].sum()
    haz_yearly_waste = full_df[full_df['Year'] == current_year]['Total_Weight_kg'].sum()
    
    # General waste data
    gen_monthly_waste = gen_monthly_cost = gen_prev_month_waste = gen_prev_month_cost = gen_yearly_waste = gen_filtered_emissions = 0
    
    if not general_df.empty and 'Month_Num' in general_df.columns:
        gen_current = general_df[(general_df['Year'] == current_year) & (general_df['Month_Num'] == current_month)]
        if not gen_current.empty:
            gen_monthly_waste = gen_current['Total Weight (kg)'].sum() if 'Total Weight (kg)' in gen_current.columns else 0
            gen_monthly_cost = gen_current['Total_Cost_Recycling_USD'].sum() if 'Total_Cost_Recycling_USD' in gen_current.columns else 0
        
        gen_prev = general_df[(general_df['Year'] == prev_year) & (general_df['Month_Num'] == prev_month)]
        if not gen_prev.empty:
            gen_prev_month_waste = gen_prev['Total Weight (kg)'].sum() if 'Total Weight (kg)' in gen_prev.columns else 0
            gen_prev_month_cost = gen_prev['Total_Cost_Recycling_USD'].sum() if 'Total_Cost_Recycling_USD' in gen_prev.columns else 0
        
        gen_year = general_df[general_df['Year'] == current_year]
        if not gen_year.empty:
            gen_yearly_waste = gen_year['Total Weight (kg)'].sum() if 'Total Weight (kg)' in gen_year.columns else 0
        
        if 'Date' in general_df.columns:
            min_date, max_date = df['Date'].min(), df['Date'].max()
            filtered_general = general_df[(general_df['Date'] >= min_date) & (general_df['Date'] <= max_date)]
            if not filtered_general.empty and 'Total_Emissions_Recycling_kgCO2e' in filtered_general.columns:
                gen_filtered_emissions = filtered_general['Total_Emissions_Recycling_kgCO2e'].sum()
    
    # Combined totals
    monthly_waste = haz_monthly_waste + gen_monthly_waste
    monthly_cost = haz_monthly_cost + gen_monthly_cost
    prev_month_cost = haz_prev_month_cost + gen_prev_month_cost
    prev_month_waste = haz_prev_month_waste + gen_prev_month_waste
    yearly_waste = haz_yearly_waste + gen_yearly_waste
    total_emissions = haz_total_emissions + gen_filtered_emissions
    avg_daily_waste = haz_total_waste / unique_days if unique_days > 0 else 0
    month_change = ((monthly_waste - prev_month_waste) / prev_month_waste * 100) if prev_month_waste > 0 else 0
    
    return {
        'total_waste': round(haz_total_waste, 1),
        'total_bags': int(total_bags),
        'waste_by_type': waste_by_type,
        'total_cost': round(haz_total_cost, 2),
        'monthly_cost': round(monthly_cost, 2),
        'prev_month_cost': round(prev_month_cost, 2),
        'yearly_waste': round(yearly_waste, 1),
        'monthly_waste': round(monthly_waste, 1),
        'total_emissions': round(total_emissions, 1),
        'avg_daily_waste': round(avg_daily_waste, 1),
        'month_change': round(month_change, 1),
        'unique_days': unique_days
    }


# ============================================
# PAGE 2: DEPARTMENTS
# ============================================

def get_department_mom_changes():
    """Get month-over-month change for each department"""
    full_df = get_df()
    
    if full_df.empty:
        return []
    
    current_year = full_df['Year'].max()
    current_month = full_df[full_df['Year'] == current_year]['Month'].max()
    
    if current_month > 1:
        prev_month, prev_year = current_month - 1, current_year
    else:
        prev_month, prev_year = 12, current_year - 1
    
    current_df = full_df[(full_df['Year'] == current_year) & (full_df['Month'] == current_month)]
    prev_df = full_df[(full_df['Year'] == prev_year) & (full_df['Month'] == prev_month)]
    
    current_by_dept = current_df.groupby('Department')['Total_Weight_kg'].sum()
    prev_by_dept = prev_df.groupby('Department')['Total_Weight_kg'].sum()
    
    # Combined total
    total_current = current_by_dept.sum()
    total_prev = prev_by_dept.sum()
    total_change = ((total_current - total_prev) / total_prev * 100) if total_prev > 0 else 0
    
    results = [{'department': 'All Departments', 'change': round(total_change, 1)}]
    
    # Individual departments (sorted by current waste, descending)
    for dept in current_by_dept.sort_values(ascending=False).index:
        curr = current_by_dept.get(dept, 0)
        prev = prev_by_dept.get(dept, 0)
        change = ((curr - prev) / prev * 100) if prev > 0 else (100 if curr > 0 else 0)
        results.append({'department': dept, 'change': round(change, 1)})
    
    return results

def calculate_department_kpis(period='monthly', start_date=None, end_date=None):
    """KPIs for Departments page"""
    df = get_filtered_df(period, start_date, end_date)
    full_df = get_df()
    
    if df.empty:
        return {
            'avg_daily_waste': 0, 'highest_cost_dept': 'N/A', 'highest_cost_amount': 0,
            'highest_dept': 'N/A', 'highest_dept_waste': 0, 'month_change': 0,
            'top_departments': {}, 'dept_count': 0
        }
    
    dept_waste = df.groupby('Department')['Total_Weight_kg'].sum().sort_values(ascending=False)
    top_departments = dept_waste.head(10).to_dict()
    dept_count = df['Department'].nunique()
    highest_dept = dept_waste.idxmax() if not dept_waste.empty else 'N/A'
    highest_dept_waste = dept_waste.max() if not dept_waste.empty else 0
    
    total_waste = df['Total_Weight_kg'].sum()
    unique_days = df['Date'].nunique()
    avg_daily_waste = total_waste / unique_days if unique_days > 0 else 0
    
    current_year = full_df['Year'].max()
    current_month = full_df[full_df['Year'] == current_year]['Month'].max()
    current_month_df = full_df[(full_df['Year'] == current_year) & (full_df['Month'] == current_month)]
    
    dept_cost = current_month_df.groupby('Department')['Total_Cost_USD'].sum().sort_values(ascending=False)
    highest_cost_dept = dept_cost.idxmax() if not dept_cost.empty else 'N/A'
    highest_cost_amount = dept_cost.max() if not dept_cost.empty else 0
    
    current_month_waste = current_month_df['Total_Weight_kg'].sum()
    prev_month, prev_year = (current_month - 1, current_year) if current_month > 1 else (12, current_year - 1)
    prev_month_waste = full_df[(full_df['Year'] == prev_year) & (full_df['Month'] == prev_month)]['Total_Weight_kg'].sum()
    month_change = ((current_month_waste - prev_month_waste) / prev_month_waste * 100) if prev_month_waste > 0 else 0
    
    return {
        'avg_daily_waste': round(avg_daily_waste, 1),
        'highest_cost_dept': highest_cost_dept,
        'highest_cost_amount': round(highest_cost_amount, 0),
        'highest_dept': highest_dept,
        'highest_dept_waste': round(highest_dept_waste, 1),
        'month_change': round(month_change, 1),
        'top_departments': top_departments,
        'dept_count': dept_count
    }


def calculate_shift_kpis(period='monthly', start_date=None, end_date=None):
    """KPIs for shift analysis (used in Departments page)"""
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return {}
    
    shift_a_weight = df['Shift A - Weight (kg)'].sum()
    shift_b_weight = df['Shift B - Weight (kg)'].sum()
    shift_c_weight = df['Shift C - Weight (kg)'].sum()
    shift_a_bags = df['Shift A - No.'].sum()
    shift_b_bags = df['Shift B - No.'].sum()
    shift_c_bags = df['Shift C - No.'].sum()
    total_weight = shift_a_weight + shift_b_weight + shift_c_weight
    
    return {
        'shift_a_weight': round(shift_a_weight, 1),
        'shift_b_weight': round(shift_b_weight, 1),
        'shift_c_weight': round(shift_c_weight, 1),
        'shift_a_bags': int(shift_a_bags),
        'shift_b_bags': int(shift_b_bags),
        'shift_c_bags': int(shift_c_bags),
        'shift_a_pct': round(shift_a_weight / total_weight * 100, 1) if total_weight > 0 else 0,
        'shift_b_pct': round(shift_b_weight / total_weight * 100, 1) if total_weight > 0 else 0,
        'shift_c_pct': round(shift_c_weight / total_weight * 100, 1) if total_weight > 0 else 0
    }


# ============================================
# PAGE 3: HAZARDOUS
# ============================================

def calculate_category_kpis(period='monthly', start_date=None, end_date=None):
    """KPIs for Hazardous waste page"""
    df = get_filtered_df(period, start_date, end_date)
    general_df = get_general_waste_df()
    
    if df.empty:
        return {
            'red_waste': 0, 'yellow_waste': 0, 'blue_waste': 0,
            'hazardous_pct': 0, 'total_hazardous': 0, 'general_waste': 0,
            'red_bags': 0, 'yellow_bags': 0, 'blue_bags': 0, 'total_bags': 0
        }
    
    waste_by_type = df.groupby('Waste Bag')['Total_Weight_kg'].sum()
    red_waste = waste_by_type.get('Red', 0)
    yellow_waste = waste_by_type.get('Yellow', 0)
    blue_waste = waste_by_type.get('Blue', 0)
    total_hazardous = red_waste + yellow_waste + blue_waste
    
    bags_by_type = df.groupby('Waste Bag')['Total_Bags'].sum()
    red_bags = int(bags_by_type.get('Red', 0))
    yellow_bags = int(bags_by_type.get('Yellow', 0))
    blue_bags = int(bags_by_type.get('Blue', 0))
    total_bags = red_bags + yellow_bags + blue_bags
    
    general_waste = 0
    if not general_df.empty:
        min_date, max_date = df['Date'].min(), df['Date'].max()
        if 'Date' in general_df.columns:
            filtered_general = general_df[(general_df['Date'] >= min_date) & (general_df['Date'] <= max_date)]
            if 'Total Weight (kg)' in filtered_general.columns:
                general_waste = filtered_general['Total Weight (kg)'].sum()
    
    total_all_waste = total_hazardous + general_waste
    hazardous_pct = (total_hazardous / total_all_waste * 100) if total_all_waste > 0 else 100
    
    return {
        'red_waste': round(red_waste, 1),
        'yellow_waste': round(yellow_waste, 1),
        'blue_waste': round(blue_waste, 1),
        'hazardous_pct': round(hazardous_pct, 1),
        'total_hazardous': round(total_hazardous, 1),
        'general_waste': round(general_waste, 1),
        'red_bags': red_bags,
        'yellow_bags': yellow_bags,
        'blue_bags': blue_bags,
        'total_bags': total_bags
    }


# ============================================
# PAGE 4: COSTS
# ============================================

def calculate_costs_kpis(period='yearly', start_date=None, end_date=None):
    """KPIs for Costs page"""
    df = get_filtered_df(period, start_date, end_date)
    gen_df = get_general_waste_df()
    gen_filtered = filter_general_waste(gen_df, period, start_date, end_date)
    
    # KPI 1: Total Cost (Medical + General)
    med_cost = float(df['Total_Cost_USD'].sum()) if 'Total_Cost_USD' in df.columns else 0
    gen_cost = float(gen_filtered['Total_Cost_Recycling_USD'].sum()) if len(gen_filtered) > 0 else 0
    total_cost = med_cost + gen_cost
    
    # KPI 2: Cost per kg
    med_weight = get_total_weight_from_shifts(df)
    gen_weight = float(gen_filtered['Total Weight (kg)'].sum()) if len(gen_filtered) > 0 and 'Total Weight (kg)' in gen_filtered.columns else 0
    total_weight = med_weight + gen_weight
    cost_per_kg = total_cost / total_weight if total_weight > 0 else 0
    
    # KPI 3: Transport Cost Share
    med_transport = float(df['Transport_Cost_USD'].sum()) if 'Transport_Cost_USD' in df.columns else 0
    gen_transport = float(gen_filtered['Transport_Cost_USD'].sum()) if len(gen_filtered) > 0 and 'Transport_Cost_USD' in gen_filtered.columns else 0
    total_transport = med_transport + gen_transport
    transport_share = (total_transport / total_cost * 100) if total_cost > 0 else 0
    
    # KPI 4: Net Recycling Savings (General only)
    if len(gen_filtered) > 0:
        landfill_cost = float(gen_filtered['Total_Cost_Landfill_USD'].sum())
        recycling_cost = float(gen_filtered['Total_Cost_Recycling_USD'].sum())
        recycling_savings = landfill_cost - recycling_cost
    else:
        recycling_savings = 0
    
    return {
        'total_cost': round(total_cost, 2),
        'cost_per_kg': round(cost_per_kg, 2),
        'transport_share': round(transport_share, 1),
        'recycling_savings': round(recycling_savings, 2)
    }


def get_cost_by_waste_type(period='yearly', start_date=None, end_date=None):
    """V1: Cost by Waste Stream (Donut) - Medical only"""
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return {'labels': [], 'values': [], 'colors': []}
    
    cost_by_type = df.groupby('Waste Bag')['Total_Cost_USD'].sum()
    
    labels, values, colors = [], [], []
    color_map = {'Yellow': '#eab308', 'Red': '#ef4444', 'Blue': '#3b82f6'}
    label_map = {
        'Yellow': 'Infectious & Anatomical (Yellow)',
        'Red': 'Highly Infectious (Red)',
        'Blue': 'Chemotherapy (Blue)'
    }
    
    for waste_type in ['Yellow', 'Red', 'Blue']:
        if waste_type in cost_by_type.index:
            labels.append(label_map[waste_type])
            values.append(round(float(cost_by_type[waste_type]), 2))
            colors.append(color_map[waste_type])
    
    return {'labels': labels, 'values': values, 'colors': colors}


def get_cost_trend():
    """V2: Cost Trend (Line) - Both files, 2024-2025 only"""
    full_df = get_df()
    gen_df = get_general_waste_df()
    med_df = full_df[full_df['Year'].isin([2024, 2025])].copy()
    
    if med_df.empty and gen_df.empty:
        return {'labels': [], 'transport': [], 'disposal': [], 'total': []}
    
    labels, transport_data, disposal_data, total_data = [], [], [], []
    
    for year in [2024, 2025]:
        for month in range(1, 13):
            med_month = med_df[(med_df['Year'] == year) & (med_df['Month'] == month)]
            med_transport = float(med_month['Transport_Cost_USD'].sum()) if not med_month.empty else 0
            med_disposal = float(med_month['Disposal_Cost_USD'].sum()) if not med_month.empty else 0
            
            gen_month = gen_df[(gen_df['Year'] == year) & (gen_df['Month_Num'] == month)]
            gen_transport = float(gen_month['Transport_Cost_USD'].sum()) if not gen_month.empty else 0
            gen_recycling = float(gen_month['Recycling_Cost_USD'].sum()) if not gen_month.empty else 0
            
            transport = med_transport + gen_transport
            disposal = med_disposal + gen_recycling
            total = transport + disposal
            
            if transport > 0 or disposal > 0:
                labels.append(f"{MONTH_NAMES[month-1]} {year}")
                transport_data.append(round(transport, 2))
                disposal_data.append(round(disposal, 2))
                total_data.append(round(total, 2))
    
    return {'labels': labels, 'transport': transport_data, 'disposal': disposal_data, 'total': total_data}


def get_cost_by_department(period='yearly', start_date=None, end_date=None):
    """V3: Cost by Department (Horizontal Bar) - Medical only, Top 10"""
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return {'labels': [], 'values': []}
    
    cost_by_dept = df.groupby('Department')['Total_Cost_USD'].sum().sort_values(ascending=False)
    top_10 = cost_by_dept.head(10)
    
    return {
        'labels': top_10.index.tolist(),
        'values': [round(float(v), 2) for v in top_10.values]
    }


def get_recycling_vs_landfill_cost():
    """V4: Recycling vs Landfill Cost (Clustered Bar) - General only"""
    gen_df = get_general_waste_df()
    
    if gen_df.empty:
        return {'labels': [], 'recycling': [], 'landfill': []}
    
    gen_df = gen_df.sort_values('Date')
    
    labels, recycling_data, landfill_data = [], [], []
    
    for _, row in gen_df.iterrows():
        year, month = int(row['Year']), int(row['Month_Num'])
        labels.append(f"{MONTH_NAMES[month-1]} {year}")
        recycling_data.append(round(float(row['Total_Cost_Recycling_USD']), 2))
        landfill_data.append(round(float(row['Total_Cost_Landfill_USD']), 2))
    
    return {'labels': labels, 'recycling': recycling_data, 'landfill': landfill_data}


# ============================================
# PAGE 5: EMISSIONS
# ============================================

def calculate_emissions_kpis(period='yearly', start_date=None, end_date=None):
    """KPIs for Emissions page"""
    df = get_filtered_df(period, start_date, end_date)
    full_df = get_df()
    gen_df = get_general_waste_df()
    gen_filtered = filter_general_waste(gen_df, period, start_date, end_date)
    
    # KPI 1: Total CO2e (Medical + General)
    med_emissions = float(df['Total_Emissions_kgCO2e'].sum()) if 'Total_Emissions_kgCO2e' in df.columns else 0
    gen_emissions = float(gen_filtered['Total_Emissions_Recycling_kgCO2e'].sum()) if len(gen_filtered) > 0 else 0
    total_emissions = med_emissions + gen_emissions
    
    # KPI 2: CO2e per kg
    med_weight = get_total_weight_from_shifts(df)
    gen_weight = float(gen_filtered['Total Weight (kg)'].sum()) if len(gen_filtered) > 0 and 'Total Weight (kg)' in gen_filtered.columns else 0
    total_weight = med_weight + gen_weight
    co2e_per_kg = total_emissions / total_weight if total_weight > 0 else 0
    
    # KPI 3: Emissions Avoided by Recycling (General only)
    if len(gen_filtered) > 0:
        landfill_emissions = float(gen_filtered['Total_Emissions_Landfill_kgCO2e'].sum())
        recycling_emissions = float(gen_filtered['Total_Emissions_Recycling_kgCO2e'].sum())
        emissions_avoided = landfill_emissions - recycling_emissions
    else:
        emissions_avoided = 0
    
    # KPI 4: Change vs 2022 Baseline (Medical only, 2022 monthly avg)
    total_2022_emissions = float(full_df[full_df['Year'] == 2022]['Total_Emissions_kgCO2e'].sum())
    baseline_2022_monthly_avg = total_2022_emissions / 12
    
    if period == 'monthly':
        current_emissions = float(df['Total_Emissions_kgCO2e'].sum())
        baseline_2022 = baseline_2022_monthly_avg
    elif period == 'yearly':
        current_emissions = float(df['Total_Emissions_kgCO2e'].sum())
        baseline_2022 = total_2022_emissions
    elif period == 'custom' and start_date and end_date:
        start, end = pd.to_datetime(start_date), pd.to_datetime(end_date)
        num_months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        current_emissions = float(df['Total_Emissions_kgCO2e'].sum())
        baseline_2022 = baseline_2022_monthly_avg * num_months
    else:
        current_emissions = float(df['Total_Emissions_kgCO2e'].sum())
        baseline_2022 = total_2022_emissions
    
    change_vs_2022 = ((current_emissions - baseline_2022) / baseline_2022 * 100) if baseline_2022 > 0 else 0
    
    return {
        'total_emissions': round(total_emissions, 1),
        'co2e_per_kg': round(co2e_per_kg, 3),
        'emissions_avoided': round(emissions_avoided, 1),
        'change_vs_2022': round(change_vs_2022, 1)
    }


def get_emissions_by_waste_type(period='yearly', start_date=None, end_date=None):
    """V1: CO₂e by Waste Type (Stacked Bar) - Medical only"""
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return {'labels': [], 'yellow': [], 'red': [], 'blue': []}
    
    if period == 'monthly':
        df['Date_Key'] = df['Date'].dt.strftime('%d %b')
        df['Sort_Key'] = df['Date'].dt.day
    else:
        df['Date_Key'] = df['Date'].dt.strftime('%b %Y')
        df['Sort_Key'] = df['Date'].dt.to_period('M').astype(str)
    
    dates_df = df.groupby(['Date_Key', 'Sort_Key']).size().reset_index(name='count')
    dates_df = dates_df.sort_values('Sort_Key')
    labels = dates_df['Date_Key'].tolist()
    
    yellow_data, red_data, blue_data = [], [], []
    
    for label in labels:
        date_df = df[df['Date_Key'] == label]
        yellow_data.append(round(float(date_df[date_df['Waste Bag'] == 'Yellow']['Total_Emissions_kgCO2e'].sum()), 1))
        red_data.append(round(float(date_df[date_df['Waste Bag'] == 'Red']['Total_Emissions_kgCO2e'].sum()), 1))
        blue_data.append(round(float(date_df[date_df['Waste Bag'] == 'Blue']['Total_Emissions_kgCO2e'].sum()), 1))
    
    return {'labels': labels, 'yellow': yellow_data, 'red': red_data, 'blue': blue_data}


def get_emissions_trend():
    """V2: Emissions Trend (Line) - Both files, 2024-2025"""
    full_df = get_df()
    gen_df = get_general_waste_df()
    med_df = full_df[full_df['Year'].isin([2024, 2025])].copy()
    
    if med_df.empty and gen_df.empty:
        return {'labels': [], 'transport': [], 'disposal': [], 'total': []}
    
    labels, transport_data, disposal_data, total_data = [], [], [], []
    
    for year in [2024, 2025]:
        for month in range(1, 13):
            med_month = med_df[(med_df['Year'] == year) & (med_df['Month'] == month)]
            med_transport = float(med_month['Transport_Emissions_kgCO2e'].sum()) if not med_month.empty else 0
            med_disposal = float(med_month['Disposal_Emissions_kgCO2e'].sum()) if not med_month.empty else 0
            
            gen_month = gen_df[(gen_df['Year'] == year) & (gen_df['Month_Num'] == month)]
            gen_transport = float(gen_month['Transport_Emissions_kgCO2e'].sum()) if not gen_month.empty else 0
            gen_recycling = float(gen_month['Recycling_Emissions_kgCO2e'].sum()) if not gen_month.empty else 0
            
            transport = med_transport + gen_transport
            disposal = med_disposal + gen_recycling
            total = transport + disposal
            
            if transport > 0 or disposal > 0:
                labels.append(f"{MONTH_NAMES[month-1]} {year}")
                transport_data.append(round(transport, 1))
                disposal_data.append(round(disposal, 1))
                total_data.append(round(total, 1))
    
    return {'labels': labels, 'transport': transport_data, 'disposal': disposal_data, 'total': total_data}


def get_recycling_vs_landfill():
    """V3: Recycling vs Landfill Emissions (Grouped Bar) - General only"""
    gen_df = get_general_waste_df()
    
    if gen_df.empty:
        return {'labels': [], 'recycling': [], 'landfill': []}
    
    gen_df = gen_df.sort_values('Date')
    
    labels, recycling_data, landfill_data = [], [], []
    
    for _, row in gen_df.iterrows():
        year, month = int(row['Year']), int(row['Month_Num'])
        labels.append(f"{MONTH_NAMES[month-1]} {year}")
        recycling_data.append(round(float(row['Total_Emissions_Recycling_kgCO2e']), 1))
        landfill_data.append(round(float(row['Total_Emissions_Landfill_kgCO2e']), 1))
    
    return {'labels': labels, 'recycling': recycling_data, 'landfill': landfill_data}


def get_emissions_by_source():
    """V4: Emissions by Source (Stacked Area) - Both files, 2024-2025"""
    full_df = get_df()
    gen_df = get_general_waste_df()
    med_df = full_df[full_df['Year'].isin([2024, 2025])].copy()
    
    if med_df.empty and gen_df.empty:
        return {'labels': [], 'transport': [], 'disposal': []}
    
    labels, transport_data, disposal_data = [], [], []
    
    for year in [2024, 2025]:
        for month in range(1, 13):
            med_month = med_df[(med_df['Year'] == year) & (med_df['Month'] == month)]
            med_transport = float(med_month['Transport_Emissions_kgCO2e'].sum()) if not med_month.empty else 0
            med_disposal = float(med_month['Disposal_Emissions_kgCO2e'].sum()) if not med_month.empty else 0
            
            gen_month = gen_df[(gen_df['Year'] == year) & (gen_df['Month_Num'] == month)]
            gen_transport = float(gen_month['Transport_Emissions_kgCO2e'].sum()) if not gen_month.empty else 0
            gen_recycling = float(gen_month['Recycling_Emissions_kgCO2e'].sum()) if not gen_month.empty else 0
            
            transport = med_transport + gen_transport
            disposal = med_disposal + gen_recycling
            
            if transport > 0 or disposal > 0:
                labels.append(f"{MONTH_NAMES[month-1]} {year}")
                transport_data.append(round(transport, 1))
                disposal_data.append(round(disposal, 1))
    
    return {'labels': labels, 'transport': transport_data, 'disposal': disposal_data}


# ============================================
# PAGE 6: TRENDS (Legacy fallback - real model in forecasting_service.py)
# ============================================

def calculate_forecast_kpis(period='monthly', start_date=None, end_date=None):
    """Legacy forecasting KPIs - simple linear regression fallback"""
    import numpy as np
    
    df = get_df()
    
    if df.empty:
        return {
            'forecasted_waste': 0, 'forecasted_emissions': 0, 'forecast_accuracy': 0,
            'last_month_actual': 0, 'last_month_predicted': 0, 'trend_direction': 'stable'
        }
    
    monthly = df.groupby(['Year', 'Month']).agg({
        'Total_Weight_kg': 'sum',
        'Total_Emissions_kgCO2e': 'sum'
    }).reset_index()
    monthly['month_num'] = range(len(monthly))
    
    if len(monthly) < 3:
        return {
            'forecasted_waste': 0, 'forecasted_emissions': 0, 'forecast_accuracy': 0,
            'last_month_actual': 0, 'last_month_predicted': 0, 'trend_direction': 'stable'
        }
    
    x = monthly['month_num'].values
    y_waste = monthly['Total_Weight_kg'].values
    y_emissions = monthly['Total_Emissions_kgCO2e'].values
    
    n = len(x)
    m_waste = (n * np.sum(x * y_waste) - np.sum(x) * np.sum(y_waste)) / (n * np.sum(x**2) - np.sum(x)**2)
    b_waste = (np.sum(y_waste) - m_waste * np.sum(x)) / n
    
    forecasted_waste = max(0, m_waste * n + b_waste)
    avg_emissions_per_kg = y_emissions.sum() / y_waste.sum() if y_waste.sum() > 0 else 0
    forecasted_emissions = forecasted_waste * avg_emissions_per_kg
    
    if len(monthly) >= 4:
        x_train, y_train = x[:-1], y_waste[:-1]
        n_train = len(x_train)
        m_t = (n_train * np.sum(x_train * y_train) - np.sum(x_train) * np.sum(y_train)) / (n_train * np.sum(x_train**2) - np.sum(x_train)**2)
        b_t = (np.sum(y_train) - m_t * np.sum(x_train)) / n_train
        
        last_month_predicted = m_t * x[-1] + b_t
        last_month_actual = y_waste[-1]
        
        if last_month_actual > 0:
            error_pct = abs(last_month_actual - last_month_predicted) / last_month_actual * 100
            forecast_accuracy = max(0, 100 - error_pct)
        else:
            forecast_accuracy = 0
    else:
        last_month_predicted = y_waste[-1]
        last_month_actual = y_waste[-1]
        forecast_accuracy = 85
    
    trend_direction = 'increasing' if m_waste > 50 else ('decreasing' if m_waste < -50 else 'stable')
    
    return {
        'forecasted_waste': round(forecasted_waste, 0),
        'forecasted_emissions': round(forecasted_emissions, 0),
        'forecast_accuracy': round(forecast_accuracy, 1),
        'last_month_actual': round(last_month_actual, 0),
        'last_month_predicted': round(last_month_predicted, 0),
        'trend_direction': trend_direction
    }


# ============================================
# LEGACY FUNCTIONS (kept for backward compatibility)
# ============================================

def calculate_cost_kpis(period='monthly', start_date=None, end_date=None):
    """Legacy cost KPIs - may be unused, kept for safety"""
    df = get_filtered_df(period, start_date, end_date)
    
    if df.empty:
        return {
            'total_cost': 0, 'transport_cost': 0, 'disposal_cost': 0,
            'cost_per_kg': 0, 'avg_daily_cost': 0, 'cost_by_type': {}, 'cost_by_dept': {}
        }
    
    total_cost = df['Total_Cost_USD'].sum()
    transport_cost = df['Transport_Cost_USD'].sum()
    disposal_cost = df['Disposal_Cost_USD'].sum()
    total_waste = df['Total_Weight_kg'].sum()
    cost_per_kg = total_cost / total_waste if total_waste > 0 else 0
    unique_days = df['Date'].nunique()
    avg_daily_cost = total_cost / unique_days if unique_days > 0 else 0
    cost_by_type = df.groupby('Waste Bag')['Total_Cost_USD'].sum().to_dict()
    cost_by_dept = df.groupby('Department')['Total_Cost_USD'].sum().sort_values(ascending=False).head(10).to_dict()
    
    return {
        'total_cost': round(total_cost, 2),
        'transport_cost': round(transport_cost, 2),
        'disposal_cost': round(disposal_cost, 2),
        'cost_per_kg': round(cost_per_kg, 2),
        'avg_daily_cost': round(avg_daily_cost, 2),
        'cost_by_type': {k: round(v, 2) for k, v in cost_by_type.items()},
        'cost_by_dept': {k: round(v, 2) for k, v in cost_by_dept.items()}
    }