from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.church_data import CHURCH_DATA, get_parishes

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/search')
@login_required
def global_search():
    """Global search API - searches delegates, users, payments, events"""
    from app.models.delegate import Delegate
    from app.models.user import User
    from app.models.payment import Payment
    from app.models.event import Event
    
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'results': []})
    
    results = []
    search_term = f'%{query}%'
    
    # Search Delegates
    delegates = Delegate.query.filter(
        (Delegate.full_name.ilike(search_term)) |
        (Delegate.phone.ilike(search_term)) |
        (Delegate.email.ilike(search_term)) |
        (Delegate.parish.ilike(search_term))
    ).limit(5).all()
    
    for d in delegates:
        results.append({
            'type': 'delegate',
            'icon': 'bi-person',
            'title': d.full_name,
            'subtitle': f'{d.parish} • {d.phone or "No phone"}',
            'url': f'/delegates/{d.id}',
            'badge': d.registration_status
        })
    
    # Search Users (admin only)
    if current_user.role in ['admin', 'super_admin']:
        users = User.query.filter(
            (User.name.ilike(search_term)) |
            (User.email.ilike(search_term)) |
            (User.phone.ilike(search_term))
        ).limit(5).all()
        
        for u in users:
            results.append({
                'type': 'user',
                'icon': 'bi-person-badge',
                'title': u.name,
                'subtitle': f'{u.role.title()} • {u.email}',
                'url': f'/admin/users/{u.id}',
                'badge': u.role
            })
    
    # Search Payments
    if current_user.role in ['admin', 'super_admin', 'finance', 'treasurer']:
        payments = Payment.query.filter(
            (Payment.transaction_code.ilike(search_term)) |
            (Payment.phone_number.ilike(search_term))
        ).limit(5).all()
        
        for p in payments:
            payer = p.delegate.full_name if p.delegate else (p.user.name if p.user else 'Unknown')
            results.append({
                'type': 'payment',
                'icon': 'bi-cash-coin',
                'title': f'KES {p.amount:,.0f} - {p.transaction_code or "No code"}',
                'subtitle': f'{payer} • {p.payment_date.strftime("%d %b %Y")}',
                'url': '/finance/dashboard',
                'badge': p.status
            })
    
    # Search Events
    events = Event.query.filter(
        (Event.name.ilike(search_term)) |
        (Event.venue.ilike(search_term))
    ).limit(3).all()
    
    for e in events:
        results.append({
            'type': 'event',
            'icon': 'bi-calendar-event',
            'title': e.name,
            'subtitle': f'{e.venue} • {e.start_date.strftime("%d %b %Y")}',
            'url': f'/events/{e.id}',
            'badge': 'Active' if e.is_active else 'Inactive'
        })
    
    return jsonify({'results': results, 'query': query})


@api_bp.route('/activity-feed')
@login_required
def activity_feed():
    """Get recent activity feed - registrations, payments, check-ins"""
    from app.models.delegate import Delegate
    from app.models.payment import Payment
    from app.models.user import User
    from app.models.event import CheckInRecord
    from datetime import datetime, timedelta
    
    activities = []
    
    # Get recent delegates (last 7 days)
    recent_delegates = Delegate.query.filter(
        Delegate.created_at >= datetime.utcnow() - timedelta(days=7)
    ).order_by(Delegate.created_at.desc()).limit(10).all()
    
    for d in recent_delegates:
        activities.append({
            'type': 'registration',
            'icon': 'bi-person-plus-fill',
            'color': 'success',
            'title': f'{d.full_name} registered',
            'subtitle': f'{d.parish} • {d.archdeaconry}',
            'time': d.created_at.isoformat(),
            'time_ago': time_ago(d.created_at),
            'url': f'/delegates/{d.id}'
        })
    
    # Get recent payments (last 7 days)
    if current_user.role in ['admin', 'super_admin', 'finance', 'treasurer']:
        recent_payments = Payment.query.filter(
            Payment.payment_date >= datetime.utcnow() - timedelta(days=7),
            Payment.status == 'completed'
        ).order_by(Payment.payment_date.desc()).limit(10).all()
        
        for p in recent_payments:
            payer = p.delegate.full_name if p.delegate else (p.user.name if p.user else 'Unknown')
            activities.append({
                'type': 'payment',
                'icon': 'bi-cash-coin',
                'color': 'primary',
                'title': f'KES {p.amount:,.0f} received',
                'subtitle': f'From {payer} • {p.transaction_code or "Manual"}',
                'time': p.payment_date.isoformat(),
                'time_ago': time_ago(p.payment_date),
                'url': '/finance/dashboard'
            })
    
    # Get recent check-ins (last 7 days)
    try:
        recent_checkins = CheckInRecord.query.filter(
            CheckInRecord.checked_in_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(CheckInRecord.checked_in_at.desc()).limit(10).all()
        
        for c in recent_checkins:
            activities.append({
                'type': 'checkin',
                'icon': 'bi-check-circle-fill',
                'color': 'info',
                'title': f'{c.delegate.full_name if c.delegate else "Unknown"} checked in',
                'subtitle': f'At {c.event.name if c.event else "Event"}',
                'time': c.checked_in_at.isoformat(),
                'time_ago': time_ago(c.checked_in_at),
                'url': '/checkin/dashboard'
            })
    except:
        pass  # CheckInRecord might not exist
    
    # Get recent user approvals (admin only)
    if current_user.role in ['admin', 'super_admin']:
        recent_users = User.query.filter(
            User.created_at >= datetime.utcnow() - timedelta(days=7),
            User.is_approved == True
        ).order_by(User.created_at.desc()).limit(5).all()
        
        for u in recent_users:
            activities.append({
                'type': 'user',
                'icon': 'bi-person-check-fill',
                'color': 'warning',
                'title': f'{u.name} joined',
                'subtitle': f'{u.role.title()} • {u.parish or "No parish"}',
                'time': u.created_at.isoformat(),
                'time_ago': time_ago(u.created_at),
                'url': f'/admin/users/{u.id}'
            })
    
    # Sort all activities by time (most recent first)
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return jsonify({
        'activities': activities[:20],  # Return top 20 activities
        'count': len(activities)
    })


def time_ago(dt):
    """Convert datetime to human-readable time ago string"""
    from datetime import datetime
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f'{mins}m ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours}h ago'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days}d ago'
    else:
        return dt.strftime('%d %b')


@api_bp.route('/parishes/<archdeaconry>')
def get_parishes_for_archdeaconry(archdeaconry):
    """API endpoint to get parishes for a specific archdeaconry"""
    if archdeaconry in CHURCH_DATA:
        parishes = sorted(CHURCH_DATA[archdeaconry])
        return jsonify({'parishes': parishes})
    return jsonify({'parishes': [], 'error': 'Archdeaconry not found'}), 404


@api_bp.route('/church-data')
def get_church_data():
    """API endpoint to get all church data"""
    return jsonify(CHURCH_DATA)
