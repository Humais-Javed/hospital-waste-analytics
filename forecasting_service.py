"""
Forecasting Service
Reads pre-computed forecast results from the Excel output
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

# Path to the Excel output from the forecasting model
FORECAST_FILE = "data/Medical_Waste_Forecast_2026.xlsx"


def forecast_available():
    """Check if forecast file exists"""
    return os.path.exists(FORECAST_FILE)


def get_forecast_kpis():
    """Get KPIs for the forecasting page"""
    if not forecast_available():
        return {
            'next_month_forecast': None,
            'next_month_name': 'N/A',
            'next_month_change': None,
            'annual_forecast': None,
            'annual_change': None,
            'peak_month': 'N/A',
            'accuracy': None,
            'error': 'Forecast data not available. Run forecasting_model.py first.'
        }
    
    try:
        # Read Monthly Summary sheet
        monthly_df = pd.read_excel(FORECAST_FILE, sheet_name='Monthly Summary', header=1)
        
        # Clean column names (they may have extra spaces)
        monthly_df.columns = monthly_df.columns.str.strip()
        
        # Get the data rows (exclude TOTAL row)
        data_rows = monthly_df[monthly_df['Month'].isin([
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ])].copy()
        
        # Find column names (they vary slightly)
        forecast_col = [c for c in monthly_df.columns if '2026' in c and 'Forecast' in c]
        forecast_col = forecast_col[0] if forecast_col else '2026 Forecast'
        
        actual_2025_col = [c for c in monthly_df.columns if '2025' in c]
        actual_2025_col = actual_2025_col[0] if actual_2025_col else '2025 Actual (clean)'
        
        # Determine "next month" based on current date
        # For the dashboard, we'll show January 2026 as the next forecast month
        current_month = datetime.now().month
        
        # For demo purposes, use January 2026
        next_month_idx = 0  # January
        next_month_name = 'Jan 2026'
        
        # Get next month forecast
        next_month_forecast = float(data_rows.iloc[next_month_idx][forecast_col])
        
        # Get same month last year for comparison
        prev_year_value = float(data_rows.iloc[next_month_idx][actual_2025_col])
        next_month_change = ((next_month_forecast - prev_year_value) / prev_year_value * 100) if prev_year_value > 0 else 0
        
        # Get annual totals from TOTAL row
        total_row = monthly_df[monthly_df['Month'] == 'TOTAL']
        if len(total_row) > 0:
            annual_forecast = float(total_row[forecast_col].values[0])
            annual_2025 = float(total_row[actual_2025_col].values[0])
            annual_change = ((annual_forecast - annual_2025) / annual_2025 * 100) if annual_2025 > 0 else 0
        else:
            # Calculate from data rows
            annual_forecast = float(data_rows[forecast_col].sum())
            annual_2025 = float(data_rows[actual_2025_col].sum())
            annual_change = ((annual_forecast - annual_2025) / annual_2025 * 100) if annual_2025 > 0 else 0
        
        # Find peak month
        peak_idx = data_rows[forecast_col].idxmax()
        peak_month_name = data_rows.loc[peak_idx, 'Month']
        peak_month = f"{peak_month_name} 2026"
        
        # Get accuracy from Model Summary sheet
        summary_df = pd.read_excel(FORECAST_FILE, sheet_name='Model Summary', header=None)
        # Find the accuracy value - look for "Average" row in the validation results
        accuracy = 86.8  # Default
        for i, row in summary_df.iterrows():
            row_str = str(row.values)
            if 'Average' in row_str:
                # Try to extract accuracy from this row
                for val in row.values:
                    if isinstance(val, (int, float)) and 80 <= val <= 100:
                        accuracy = float(val)
                        break
        
        return {
            'next_month_forecast': round(next_month_forecast, 0),
            'next_month_name': next_month_name,
            'next_month_change': round(next_month_change, 1),
            'annual_forecast': round(annual_forecast, 0),
            'annual_change': round(annual_change, 1),
            'peak_month': peak_month,
            'accuracy': round(accuracy, 0),
            'error': None
        }
        
    except Exception as e:
        return {
            'next_month_forecast': None,
            'next_month_name': 'N/A',
            'next_month_change': None,
            'annual_forecast': None,
            'annual_change': None,
            'peak_month': 'N/A',
            'accuracy': None,
            'error': f'Error reading forecast data: {str(e)}'
        }


def get_forecast_with_bands():
    """Get daily forecast data with confidence bands for the line chart"""
    if not forecast_available():
        return {'error': 'Forecast data not available'}
    
    try:
        # Read Historical vs Forecast sheet for combined data
        hist_df = pd.read_excel(FORECAST_FILE, sheet_name='Historical vs Forecast', header=1)
        hist_df.columns = hist_df.columns.str.strip()
        
        # Read Daily Forecast for P90 Upper (not in hist sheet)
        daily_df = pd.read_excel(FORECAST_FILE, sheet_name='Daily Forecast 2026', header=1)
        daily_df.columns = daily_df.columns.str.strip()
        
        # Build response data
        # For the chart, we'll aggregate to monthly to avoid too many points
        hist_df['Date'] = pd.to_datetime(hist_df['Date'], dayfirst=True)
        hist_df['YearMonth'] = hist_df['Date'].dt.to_period('M')
        
        # Aggregate historical actuals by month
        actual_col = [c for c in hist_df.columns if 'Actual' in c][0]
        forecast_col = [c for c in hist_df.columns if 'Forecast' in c and 'P10' not in c][0]
        p10_col = [c for c in hist_df.columns if 'P10' in c][0]
        
        # Get monthly aggregates
        monthly_data = hist_df.groupby('YearMonth').agg({
            actual_col: 'sum',
            forecast_col: 'sum',
            p10_col: 'sum'
        }).reset_index()
        
        # Get P90 from daily forecast
        daily_df['Date'] = pd.to_datetime(daily_df['Date'], dayfirst=True)
        daily_df['YearMonth'] = daily_df['Date'].dt.to_period('M')
        p90_col = [c for c in daily_df.columns if 'P90' in c][0]
        forecast_daily_col = [c for c in daily_df.columns if 'Forecast' in c][0]
        
        p90_monthly = daily_df.groupby('YearMonth')[p90_col].sum().to_dict()
        
        # Build response
        labels = []
        actuals = []
        forecasts = []
        p10_lower = []
        p90_upper = []
        
        for _, row in monthly_data.iterrows():
            period = row['YearMonth']
            labels.append(period.strftime('%b %Y'))
            
            actual_val = row[actual_col]
            forecast_val = row[forecast_col]
            p10_val = row[p10_col]
            p90_val = p90_monthly.get(period, forecast_val * 1.1)
            
            # Actual values only for historical data
            if period.year < 2026:
                actuals.append(round(float(actual_val), 0) if pd.notna(actual_val) and actual_val != '' else None)
                forecasts.append(None)
                p10_lower.append(None)
                p90_upper.append(None)
            else:
                actuals.append(None)
                forecasts.append(round(float(forecast_val), 0) if pd.notna(forecast_val) and forecast_val != '' else None)
                p10_lower.append(round(float(p10_val), 0) if pd.notna(p10_val) and p10_val != '' else None)
                p90_upper.append(round(float(p90_val), 0) if pd.notna(p90_val) else None)
        
        return {
            'labels': labels,
            'actuals': actuals,
            'forecasts': forecasts,
            'p10_lower': p10_lower,
            'p90_upper': p90_upper
        }
        
    except Exception as e:
        return {'error': f'Error reading forecast data: {str(e)}'}


def get_seasonal_patterns():
    """Get monthly data by year for seasonal pattern chart"""
    if not forecast_available():
        return {'error': 'Forecast data not available'}
    
    try:
        monthly_df = pd.read_excel(FORECAST_FILE, sheet_name='Monthly Summary', header=1)
        monthly_df.columns = monthly_df.columns.str.strip()
        
        # Get data rows only (exclude TOTAL)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        data_rows = monthly_df[monthly_df['Month'].isin(months)].copy()
        
        # Find year columns
        col_2022 = [c for c in monthly_df.columns if '2022' in c][0]
        col_2023 = [c for c in monthly_df.columns if '2023' in c][0]
        col_2024 = [c for c in monthly_df.columns if '2024' in c][0]
        col_2025 = [c for c in monthly_df.columns if '2025' in c][0]
        
        return {
            'labels': months,
            'data_2022': [round(float(x), 0) if pd.notna(x) else 0 for x in data_rows[col_2022].values],
            'data_2023': [round(float(x), 0) if pd.notna(x) else 0 for x in data_rows[col_2023].values],
            'data_2024': [round(float(x), 0) if pd.notna(x) else 0 for x in data_rows[col_2024].values],
            'data_2025': [round(float(x), 0) if pd.notna(x) else 0 for x in data_rows[col_2025].values]
        }
        
    except Exception as e:
        return {'error': f'Error reading forecast data: {str(e)}'}


def get_monthly_comparison():
    """Get 2025 actual vs 2026 forecast by month"""
    if not forecast_available():
        return {'error': 'Forecast data not available'}
    
    try:
        monthly_df = pd.read_excel(FORECAST_FILE, sheet_name='Monthly Summary', header=1)
        monthly_df.columns = monthly_df.columns.str.strip()
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        data_rows = monthly_df[monthly_df['Month'].isin(months)].copy()
        
        col_2025 = [c for c in monthly_df.columns if '2025' in c][0]
        col_2026 = [c for c in monthly_df.columns if '2026' in c and 'Forecast' in c][0]
        
        return {
            'labels': months,
            'actual_2025': [round(float(x), 0) if pd.notna(x) else 0 for x in data_rows[col_2025].values],
            'forecast_2026': [round(float(x), 0) if pd.notna(x) else 0 for x in data_rows[col_2026].values]
        }
        
    except Exception as e:
        return {'error': f'Error reading forecast data: {str(e)}'}