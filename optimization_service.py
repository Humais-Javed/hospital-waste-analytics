"""
Optimization Service
Reads pre-computed optimization results from MedWaste_Ultra_v4.xlsx
"""

import pandas as pd
import os

EXCEL_PATH = "data/MedWaste_Ultra_v4.xlsx"

_cache = {}


def _load_sheet(sheet_name):
    """Load and cache a sheet from the Excel file"""
    if sheet_name not in _cache:
        if os.path.exists(EXCEL_PATH):
            try:
                _cache[sheet_name] = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=None)
            except Exception as e:
                print(f"Error loading sheet {sheet_name}: {e}")
                _cache[sheet_name] = None
        else:
            print(f"Warning: {EXCEL_PATH} not found")
            _cache[sheet_name] = None
    return _cache[sheet_name]


def get_optimization_kpis(strategy='recommended'):
    """Get KPIs for a given strategy from Optimisation Results sheet"""
    df = _load_sheet('Optimisation Results')
    
    if df is None:
        return {
            'optimized_cost': 0, 'baseline_cost': 0, 'cost_saving': 0, 'cost_reduction_pct': 0,
            'optimized_emissions': 0, 'baseline_emissions': 0, 'emissions_saving': 0, 
            'emissions_reduction_pct': 0, 'strategy': strategy
        }
    
    row_map = {'baseline': 3, 'min_cost': 4, 'min_emissions': 5, 'recommended': 6}
    
    baseline_row = df.iloc[3]
    baseline_cost = float(baseline_row[12])
    baseline_emissions = float(baseline_row[13])
    
    strategy_row = df.iloc[row_map.get(strategy, 6)]
    optimized_cost = float(strategy_row[12])
    optimized_emissions = float(strategy_row[13])
    
    cost_saving = baseline_cost - optimized_cost
    emissions_saving = baseline_emissions - optimized_emissions
    cost_reduction_pct = (cost_saving / baseline_cost * 100) if baseline_cost > 0 else 0
    emissions_reduction_pct = (emissions_saving / baseline_emissions * 100) if baseline_emissions > 0 else 0
    
    return {
        'optimized_cost': round(optimized_cost, 2),
        'baseline_cost': round(baseline_cost, 2),
        'cost_saving': round(cost_saving, 2),
        'cost_reduction_pct': round(cost_reduction_pct, 1),
        'optimized_emissions': round(optimized_emissions, 2),
        'baseline_emissions': round(baseline_emissions, 2),
        'emissions_saving': round(emissions_saving, 2),
        'emissions_reduction_pct': round(emissions_reduction_pct, 1),
        'strategy': strategy
    }


def _get_routing_config(strategy):
    """Get sheet name and data start row for each strategy"""
    config = {
        'recommended': ('Recommended Routing', 2),
        'min_cost': ('Min Cost Routing', 3),
        'min_emissions': ('Min Emissions Routing', 3)
    }
    return config.get(strategy, config['recommended'])


def get_routing_table(strategy='recommended'):
    """Get routing table data for display - combines split treatments into single rows"""
    sheet_name, data_start_row = _get_routing_config(strategy)
    df = _load_sheet(sheet_name)
    
    if df is None:
        return []
    
    # Group by waste stream and combine treatments
    stream_data = {}
    
    for i in range(data_start_row, len(df)):
        row = df.iloc[i]
        stream = str(row[0]).strip() if pd.notna(row[0]) else ''
        treatment = str(row[1]).strip() if pd.notna(row[1]) else ''
        flexibility = str(row[2]).strip() if pd.notna(row[2]) else ''
        volume = float(row[3]) if pd.notna(row[3]) else 0
        cost = float(row[5]) if pd.notna(row[5]) else 0
        emissions = float(row[6]) if pd.notna(row[6]) else 0
        
        # Skip empty, aggregate, transport, and bag handling rows
        if stream in ['', 'ALL', 'Medical'] or 'Transport' in treatment or 'Handling' in treatment:
            continue
        
        if stream not in stream_data:
            stream_data[stream] = {
                'stream': stream,
                'treatments': [],
                'total_volume': 0,
                'total_cost': 0,
                'total_emissions': 0,
                'flexibility': flexibility
            }
        
        stream_data[stream]['treatments'].append({'method': treatment, 'volume': volume})
        stream_data[stream]['total_volume'] += volume
        stream_data[stream]['total_cost'] += cost
        stream_data[stream]['total_emissions'] += emissions
        if flexibility == 'Variable':
            stream_data[stream]['flexibility'] = 'Variable'
    
    # Build final rows with combined treatment strings
    rows = []
    for stream, data in stream_data.items():
        if len(data['treatments']) == 1:
            treatment_str = f"100% {data['treatments'][0]['method']}"
        else:
            total_vol = data['total_volume']
            parts = []
            for t in sorted(data['treatments'], key=lambda x: x['volume'], reverse=True):
                pct = (t['volume'] / total_vol * 100) if total_vol > 0 else 0
                parts.append(f"{pct:.0f}% {t['method']}")
            treatment_str = ' + '.join(parts)
        
        rows.append({
            'stream': data['stream'],
            'volume': round(data['total_volume']),
            'treatment': treatment_str,
            'cost': round(data['total_cost'], 2),
            'emissions': round(data['total_emissions'], 2),
            'flexibility': data['flexibility'],
            'compliance': True
        })
    
    return rows


def get_treatment_allocation(strategy='recommended'):
    """Get treatment allocation data for stacked bar chart - all waste streams"""
    sheet_name, data_start_row = _get_routing_config(strategy)
    df = _load_sheet(sheet_name)
    
    if df is None:
        return {'streams': [], 'incineration': [], 'recycling': [], 'autoclave': [], 'landfill': []}
    
    # Collect unique streams and their treatment volumes
    streams_order = []
    stream_treatments = {}
    
    for i in range(data_start_row, len(df)):
        row = df.iloc[i]
        stream = str(row[0]).strip() if pd.notna(row[0]) else ''
        treatment = str(row[1]).strip() if pd.notna(row[1]) else ''
        volume = float(row[3]) if pd.notna(row[3]) else 0
        
        if stream in ['', 'ALL', 'Medical'] or 'Transport' in treatment or 'Handling' in treatment:
            continue
        
        if stream not in stream_treatments:
            streams_order.append(stream)
            stream_treatments[stream] = {'Incineration': 0, 'Recycling': 0, 'Autoclave': 0, 'Landfill': 0}
        
        if 'Incineration' in treatment:
            stream_treatments[stream]['Incineration'] += volume
        elif 'Autoclave' in treatment:
            stream_treatments[stream]['Autoclave'] += volume
        elif 'Recycling' in treatment:
            stream_treatments[stream]['Recycling'] += volume
        elif 'Landfill' in treatment:
            stream_treatments[stream]['Landfill'] += volume
    
    return {
        'streams': streams_order,
        'incineration': [round(stream_treatments[s]['Incineration']) for s in streams_order],
        'recycling': [round(stream_treatments[s]['Recycling']) for s in streams_order],
        'autoclave': [round(stream_treatments[s]['Autoclave']) for s in streams_order],
        'landfill': [round(stream_treatments[s]['Landfill']) for s in streams_order]
    }


def get_pareto_frontier(strategy='recommended'):
    """Get main point + alternative points based on strategy"""
    df = _load_sheet('Pareto Frontier')
    
    if df is None:
        return {'main_point': None, 'alternatives': []}
    
    # Row ranges for each strategy (0-indexed)
    # Excel row 4 = index 3, etc.
    strategy_config = {
        'recommended': {
            'main_row': 3,      # Excel row 4 (★ Recommended)
            'alt_start': 4,     # Excel row 5
            'alt_end': 108,     # Excel row 109
            'label': 'Recommended',
            'color': '#10b981',
            'marker': 'star'
        },
        'min_emissions': {
            'main_row': 109,    # Excel row 110 (▼ Min Emissions)
            'alt_start': 110,   # Excel row 111
            'alt_end': 303,     # Excel row 304
            'label': 'Min Emissions',
            'color': '#3b82f6',
            'marker': 'triangle'
        },
        'min_cost': {
            'main_row': 304,    # Excel row 305 (◆ Min Cost)
            'alt_start': None,  # No alternatives
            'alt_end': None,
            'label': 'Min Cost',
            'color': '#f59e0b',
            'marker': 'diamond'
        }
    }
    
    config = strategy_config.get(strategy, strategy_config['recommended'])
    
    # Get main point
    main_row = df.iloc[config['main_row']]
    try:
        main_cost = float(main_row[2])
        main_emissions = float(main_row[3])
    except (ValueError, TypeError):
        return {'main_point': None, 'alternatives': []}
    
    main_point = {
        'label': config['label'],
        'cost': round(main_cost, 2),
        'emissions': round(main_emissions, 2),
        'color': config['color'],
        'marker': config['marker']
    }
    
    # Get alternatives (if any)
    alternatives = []
    if config['alt_start'] is not None and config['alt_end'] is not None:
        for i in range(config['alt_start'], config['alt_end'] + 1):
            if i >= len(df):
                break
            row = df.iloc[i]
            if not pd.notna(row[2]) or not pd.notna(row[3]):
                continue
            try:
                cost = float(row[2])
                emissions = float(row[3])
                alternatives.append({'cost': round(cost, 2), 'emissions': round(emissions, 2)})
            except (ValueError, TypeError):
                continue
    
    # Sort alternatives by cost for smooth curve
    alternatives.sort(key=lambda p: p['cost'])
    
    return {'main_point': main_point, 'alternatives': alternatives}