"""
Admin Analytics Routes
Phase 3 - Business Intelligence and Reporting

Provides comprehensive analytics and reporting capabilities
for restaurant operations including peak hours, best sellers,
customer feedback, and cash reconciliation.
"""

from flask import render_template, jsonify, request
from flask_login import current_user
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta, date
from models import (
    db, Order, Menu, Ingredient, Feedback, DailyReport, 
    HourlyStats, MenuPopularity, OrderItem, User,
    get_thai_now, update_daily_report, update_hourly_stats, 
    update_menu_popularity
)
from .auth import admin_required
from . import admin_bp


@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Main analytics dashboard"""
    return render_template('admin/analytics.html')


@admin_bp.route('/analytics/peak-hours')
@admin_required
def peak_hours():
    """Peak hours analysis page"""
    return render_template('admin/analytics/peak_hours.html')


@admin_bp.route('/analytics/best-sellers')
@admin_required
def best_sellers():
    """Best selling items analysis page"""
    return render_template('admin/analytics/best_sellers.html')


@admin_bp.route('/analytics/feedback')
@admin_required
def feedback_analysis():
    """Customer feedback analysis page"""
    return render_template('admin/analytics/feedback.html')


@admin_bp.route('/reports/cash-reconciliation')
@admin_required
def cash_reconciliation():
    """Daily cash reconciliation report"""
    return render_template('admin/reports/cash_reconciliation.html')


# =============================================================================
# API ENDPOINTS FOR ANALYTICS DATA
# =============================================================================

@admin_bp.route('/api/analytics/peak-hours')
@admin_required
def api_peak_hours():
    """API: Get peak hours data"""
    try:
        # Get date range from query params
        days = request.args.get('days', 7, type=int)
        end_date = get_thai_now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Query hourly statistics
        hourly_data = {}
        for hour in range(24):
            hourly_data[hour] = {
                'hour': f"{hour:02d}:00",
                'total_orders': 0,
                'total_revenue': 0,
                'avg_orders': 0,
                'avg_revenue': 0
            }
        
        # Get hourly stats from database
        stats = HourlyStats.query.filter(
            HourlyStats.date >= start_date,
            HourlyStats.date <= end_date
        ).all()
        
        # Aggregate data by hour
        for stat in stats:
            hour_data = hourly_data[stat.hour]
            hour_data['total_orders'] += stat.order_count
            hour_data['total_revenue'] += float(stat.revenue)
        
        # Calculate averages
        for hour_data in hourly_data.values():
            hour_data['avg_orders'] = hour_data['total_orders'] / days
            hour_data['avg_revenue'] = hour_data['total_revenue'] / days
        
        # Convert to list and sort by hour
        result = list(hourly_data.values())
        
        # Find peak hour
        peak_hour = max(result, key=lambda x: x['avg_orders'])
        
        return jsonify({
            'success': True,
            'data': result,
            'peak_hour': peak_hour,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/analytics/top-selling')
@admin_required
def api_top_selling():
    """API: Get top selling items"""
    try:
        # Get parameters
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        end_date = get_thai_now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Query menu popularity
        top_items = db.session.query(
            Menu.name,
            Menu.price,
            func.sum(MenuPopularity.order_count).label('total_orders'),
            func.sum(MenuPopularity.revenue).label('total_revenue'),
            func.avg(MenuPopularity.average_rating).label('avg_rating')
        ).join(MenuPopularity).filter(
            MenuPopularity.date >= start_date,
            MenuPopularity.date <= end_date
        ).group_by(Menu.id, Menu.name, Menu.price)\
         .order_by(desc('total_orders'))\
         .limit(limit).all()
        
        # Format results
        result = []
        for item in top_items:
            result.append({
                'name': item.name,
                'base_price': float(item.price),
                'total_orders': item.total_orders or 0,
                'total_revenue': float(item.total_revenue or 0),
                'avg_rating': float(item.avg_rating or 0),
                'avg_order_value': float(item.total_revenue or 0) / max(item.total_orders or 1, 1)
            })
        
        # Get worst performing items
        worst_items = db.session.query(
            Menu.name,
            Menu.price,
            func.sum(MenuPopularity.order_count).label('total_orders'),
            func.sum(MenuPopularity.revenue).label('total_revenue')
        ).join(MenuPopularity).filter(
            MenuPopularity.date >= start_date,
            MenuPopularity.date <= end_date
        ).group_by(Menu.id, Menu.name, Menu.price)\
         .order_by('total_orders')\
         .limit(5).all()
        
        worst_result = []
        for item in worst_items:
            worst_result.append({
                'name': item.name,
                'base_price': float(item.price),
                'total_orders': item.total_orders or 0,
                'total_revenue': float(item.total_revenue or 0)
            })
        
        return jsonify({
            'success': True,
            'top_sellers': result,
            'worst_performers': worst_result,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/analytics/feedback')
@admin_required
def api_feedback():
    """API: Get customer feedback analysis"""
    try:
        # Get parameters
        days = request.args.get('days', 30, type=int)
        
        end_date = get_thai_now().date()
        start_date = end_date - timedelta(days=days-1)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        
        # Get feedback data
        feedbacks = Feedback.query.join(Order).filter(
            Order.created_at >= start_datetime,
            Order.created_at < end_datetime
        ).all()
        
        if not feedbacks:
            return jsonify({
                'success': True,
                'summary': {
                    'total_feedback': 0,
                    'average_rating': 0,
                    'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                },
                'recent_feedback': [],
                'feedback_trend': []
            })
        
        # Calculate summary statistics
        total_feedback = len(feedbacks)
        average_rating = sum(f.rating for f in feedbacks) / total_feedback
        
        # Rating distribution
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for feedback in feedbacks:
            rating_dist[feedback.rating] += 1
        
        # Recent feedback (last 10)
        recent_feedbacks = sorted(feedbacks, key=lambda x: x.created_at, reverse=True)[:10]
        recent_data = []
        for feedback in recent_feedbacks:
            recent_data.append({
                'order_number': feedback.order.order_number,
                'customer_name': feedback.order.customer_name,
                'rating': feedback.rating,
                'comment': feedback.comment,
                'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        # Daily feedback trend
        daily_trend = {}
        for feedback in feedbacks:
            day = feedback.created_at.date()
            if day not in daily_trend:
                daily_trend[day] = {'count': 0, 'total_rating': 0}
            daily_trend[day]['count'] += 1
            daily_trend[day]['total_rating'] += feedback.rating
        
        trend_data = []
        for day, data in sorted(daily_trend.items()):
            trend_data.append({
                'date': day.isoformat(),
                'feedback_count': data['count'],
                'average_rating': data['total_rating'] / data['count']
            })
        
        return jsonify({
            'success': True,
            'summary': {
                'total_feedback': total_feedback,
                'average_rating': round(average_rating, 2),
                'rating_distribution': rating_dist
            },
            'recent_feedback': recent_data,
            'feedback_trend': trend_data,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/reports/cash-reconciliation')
@admin_required
def api_cash_reconciliation():
    """API: Get daily cash reconciliation report"""
    try:
        # Get target date
        date_str = request.args.get('date')
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = get_thai_now().date()
        
        # Calculate date range
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        
        # Get all orders for the day
        daily_orders = Order.query.filter(
            Order.created_at >= day_start,
            Order.created_at < day_end
        ).order_by(Order.created_at).all()
        
        # Categorize orders
        completed_orders = [o for o in daily_orders if o.status in ['delivered', 'completed']]
        pending_orders = [o for o in daily_orders if o.status == 'pending']
        cancelled_orders = [o for o in daily_orders if o.status == 'cancelled']
        
        # Calculate totals
        total_cash_expected = sum(float(o.total_price) for o in completed_orders)
        total_orders = len(daily_orders)
        completed_count = len(completed_orders)
        
        # Payment method breakdown (assuming all cash for now)
        payment_breakdown = {
            'cash': total_cash_expected,
            'card': 0,
            'online': 0
        }
        
        # Order details
        order_details = []
        for order in completed_orders:
            order_details.append({
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'total_price': float(order.total_price),
                'status': order.status,
                'created_at': order.created_at.strftime('%H:%M'),
                'completed_at': order.completed_at.strftime('%H:%M') if order.completed_at else None
            })
        
        return jsonify({
            'success': True,
            'date': target_date.isoformat(),
            'summary': {
                'total_orders': total_orders,
                'completed_orders': completed_count,
                'pending_orders': len(pending_orders),
                'cancelled_orders': len(cancelled_orders),
                'total_cash_expected': total_cash_expected,
                'completion_rate': (completed_count / total_orders * 100) if total_orders > 0 else 0
            },
            'payment_breakdown': payment_breakdown,
            'order_details': order_details
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/analytics/update-reports')
@admin_required
def api_update_reports():
    """API: Manually trigger report updates"""
    try:
        target_date = get_thai_now().date()
        
        # Update all reports
        update_daily_report(target_date)
        update_hourly_stats(target_date)
        update_menu_popularity(target_date)
        
        return jsonify({
            'success': True,
            'message': f'Reports updated for {target_date}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
