"""
Dashboard Routes - All dashboard page routes
Organized by page number
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from data_service import (
    calculate_overview_kpis,
    calculate_department_kpis,
    calculate_category_kpis,
    calculate_costs_kpis,
    calculate_emissions_kpis,
    calculate_shift_kpis
)
from optimization_service import get_optimization_kpis
from forecasting_service import get_forecast_kpis

dashboard_bp = Blueprint('dashboard', __name__)


# ============================================
# UTILITIES
# ============================================

def get_filter_params():
    """Extract filter parameters from request"""
    period = request.args.get('period', 'yearly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    return period, start_date, end_date


def make_context(active_page, kpis, period=None, start_date=None, end_date=None):
    """Build common template context"""
    return {
        'kpis': kpis,
        'active_page': active_page,
        'period': period,
        'start_date': start_date,
        'end_date': end_date
    }


# ============================================
# PAGE 1: OVERVIEW
# ============================================

@dashboard_bp.route('/')
@login_required
def overview():
    """Main dashboard overview"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_overview_kpis(period, start_date, end_date)
    return render_template('overview.html', **make_context('overview', kpis, period, start_date, end_date))


# ============================================
# PAGE 2: DEPARTMENTS
# ============================================

@dashboard_bp.route('/departments')
@login_required
def departments():
    """Department analysis"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_department_kpis(period, start_date, end_date)
    kpis.update(calculate_overview_kpis(period, start_date, end_date))
    return render_template('departments.html', **make_context('departments', kpis, period, start_date, end_date))


# ============================================
# PAGE 3: HAZARDOUS
# ============================================

@dashboard_bp.route('/hazardous')
@login_required
def hazardous():
    """Hazardous waste tracking"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_category_kpis(period, start_date, end_date)
    kpis.update(calculate_overview_kpis(period, start_date, end_date))
    return render_template('hazardous.html', **make_context('hazardous', kpis, period, start_date, end_date))


# ============================================
# PAGE 4: COSTS
# ============================================

@dashboard_bp.route('/costs')
@login_required
def costs():
    """Cost tracking"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_costs_kpis(period, start_date, end_date)
    return render_template('costs.html', **make_context('costs', kpis, period, start_date, end_date))


# ============================================
# PAGE 5: EMISSIONS
# ============================================

@dashboard_bp.route('/emissions')
@login_required
def emissions():
    """Emissions tracking"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_emissions_kpis(period, start_date, end_date)
    return render_template('emissions.html', **make_context('emissions', kpis, period, start_date, end_date))


# ============================================
# PAGE 6: TRENDS & FORECASTING (Admin Only)
# ============================================

@dashboard_bp.route('/trends')
@login_required
def trends():
    """Trends and forecasting (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.overview'))
    
    kpis = get_forecast_kpis()
    return render_template('trends.html', kpis=kpis, active_page='trends')


# ============================================
# PAGE 7: OPTIMIZATION (Admin Only)
# ============================================

@dashboard_bp.route('/optimization')
@login_required
def optimization():
    """Optimization recommendations (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.overview'))
    
    strategy = request.args.get('strategy', 'recommended')
    kpis = get_optimization_kpis(strategy)
    return render_template('optimization.html', kpis=kpis, strategy=strategy, active_page='optimization')


# ============================================
# LEGACY ROUTES (kept for backward compatibility)
# ============================================

@dashboard_bp.route('/shifts')
@login_required
def shifts():
    """Shift analysis (legacy - may be unused)"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_shift_kpis(period, start_date, end_date)
    return render_template('shifts.html', **make_context('shifts', kpis, period, start_date, end_date))


@dashboard_bp.route('/compliance')
@login_required
def compliance():
    """Compliance tracking (legacy - may be unused)"""
    period, start_date, end_date = get_filter_params()
    kpis = calculate_overview_kpis(period, start_date, end_date)
    return render_template('compliance.html', **make_context('compliance', kpis, period, start_date, end_date))