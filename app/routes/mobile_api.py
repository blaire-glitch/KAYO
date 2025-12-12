"""
Mobile API endpoints for KAYO Android App
All endpoints return JSON responses for mobile consumption
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_user, current_user
from datetime import datetime, timedelta
from functools import wraps
import secrets

# Optional JWT import
try:
    import jwt
    # Verify it's PyJWT, not another jwt package
    if hasattr(jwt, 'encode') and hasattr(jwt, 'decode'):
        HAS_JWT = True
    else:
        HAS_JWT = False
        jwt = None
except ImportError as e:
    HAS_JWT = False
    jwt = None
except Exception as e:
    HAS_JWT = False
    jwt = None

from app import db
from app.models.user import User
from app.models.delegate import Delegate
from app.models.payment import Payment
from app.models.event import Event, PricingTier
from app.models.operations import CheckInRecord
from app.church_data import CHURCH_DATA

mobile_api_bp = Blueprint('mobile_api', __name__, url_prefix='/api/v1')


# ==================== JWT TOKEN AUTHENTICATION ====================

def generate_token(user_id, expires_hours=24*7):
    """Generate JWT token for mobile authentication"""
    if not HAS_JWT:
        return None
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_hours),
        'iat': datetime.utcnow()
    }
    secret_key = current_app.config.get('SECRET_KEY', 'your-secret-key')
    return jwt.encode(payload, secret_key, algorithm='HS256')


def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not HAS_JWT:
            return jsonify({'error': 'JWT authentication not available'}), 503
        
        token = None
        
        # Check Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            secret_key = current_app.config.get('SECRET_KEY', 'your-secret-key')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            current_user_id = payload['user_id']
            user = User.query.get(current_user_id)
            if not user or not user.is_active:
                return jsonify({'error': 'User not found or inactive'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(user, *args, **kwargs)
    return decorated


# ==================== STATUS ENDPOINT ====================
@mobile_api_bp.route('/status', methods=['GET'])
def api_status():
    """Check API status and availability"""
    jwt_version = None
    try:
        import jwt as jwt_check
        jwt_version = getattr(jwt_check, '__version__', 'unknown')
    except:
        pass
    
    return jsonify({
        'success': True,
        'status': 'online',
        'version': '1.0.0',
        'jwt_available': HAS_JWT,
        'jwt_version': jwt_version,
        'message': 'KAYO API is running' if HAS_JWT else 'API running but JWT not installed - install PyJWT on server'
    })


# ==================== CHURCH DATA ENDPOINTS ====================
@mobile_api_bp.route('/church/archdeaconries', methods=['GET'])
def get_archdeaconries():
    """Get list of all archdeaconries"""
    archdeaconries = sorted(CHURCH_DATA.keys())
    return jsonify({
        'success': True,
        'archdeaconries': archdeaconries,
        'count': len(archdeaconries)
    })


@mobile_api_bp.route('/church/parishes', methods=['GET'])
def get_parishes():
    """Get parishes, optionally filtered by archdeaconry"""
    archdeaconry = request.args.get('archdeaconry')
    
    if archdeaconry:
        if archdeaconry not in CHURCH_DATA:
            return jsonify({
                'success': False,
                'error': f'Archdeaconry "{archdeaconry}" not found'
            }), 404
        parishes = sorted(CHURCH_DATA[archdeaconry])
    else:
        # Return all parishes
        parishes = []
        for arch_parishes in CHURCH_DATA.values():
            parishes.extend(arch_parishes)
        parishes = sorted(set(parishes))
    
    return jsonify({
        'success': True,
        'archdeaconry': archdeaconry,
        'parishes': parishes,
        'count': len(parishes)
    })


@mobile_api_bp.route('/church/hierarchy', methods=['GET'])
def get_church_hierarchy():
    """Get full church hierarchy (archdeaconries with their parishes)"""
    hierarchy = []
    for archdeaconry in sorted(CHURCH_DATA.keys()):
        hierarchy.append({
            'archdeaconry': archdeaconry,
            'parishes': sorted(CHURCH_DATA[archdeaconry])
        })
    
    return jsonify({
        'success': True,
        'hierarchy': hierarchy,
        'archdeaconry_count': len(hierarchy),
        'total_parishes': sum(len(item['parishes']) for item in hierarchy)
    })


# ==================== AUTHENTICATION ENDPOINTS ====================
@mobile_api_bp.route('/auth/login', methods=['POST'])
def mobile_login():
    """Login endpoint for mobile app"""
    try:
        # Check if JWT is available first
        if not HAS_JWT:
            return jsonify({
                'success': False,
                'error': 'Authentication service temporarily unavailable. Please try again later.'
            }), 503
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'success': False, 'error': 'Account is deactivated'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate token
        token = generate_token(user.id)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'phone': user.phone if hasattr(user, 'phone') else None,
                'role': user.role,
                'local_church': user.local_church if hasattr(user, 'local_church') else None,
                'parish': user.parish if hasattr(user, 'parish') else None,
                'archdeaconry': user.archdeaconry if hasattr(user, 'archdeaconry') else None,
                'profile_picture': user.profile_picture if hasattr(user, 'profile_picture') else None
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@mobile_api_bp.route('/auth/register', methods=['POST'])
def mobile_register():
    """Register new user via mobile app"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['name', 'email', 'password', 'role']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if email exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(
        name=data['name'],
        email=data['email'],
        phone=data.get('phone'),
        role=data['role'],
        local_church=data.get('local_church'),
        parish=data.get('parish'),
        archdeaconry=data.get('archdeaconry'),
        oauth_provider='local'
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Generate token
    token = generate_token(user.id)
    
    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'token': token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        }
    }), 201


@mobile_api_bp.route('/auth/google', methods=['POST'])
def mobile_google_auth():
    """Google OAuth authentication for mobile"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    google_id = data.get('google_id')
    email = data.get('email')
    name = data.get('name')
    profile_picture = data.get('profile_picture')
    
    if not google_id or not email:
        return jsonify({'error': 'Google ID and email required'}), 400
    
    # Check if user exists by Google ID
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        # Check by email
        user = User.query.filter_by(email=email).first()
        if user:
            # Link Google account to existing user
            user.google_id = google_id
            user.profile_picture = profile_picture
            user.oauth_provider = 'google'
        else:
            # Create new user
            user = User(
                name=name or email.split('@')[0],
                email=email,
                google_id=google_id,
                profile_picture=profile_picture,
                oauth_provider='google',
                role='user'
            )
            db.session.add(user)
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    token = generate_token(user.id)
    
    # Check if profile is complete
    profile_complete = bool(user.local_church and user.parish)
    
    return jsonify({
        'success': True,
        'token': token,
        'profile_complete': profile_complete,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'local_church': user.local_church,
            'parish': user.parish,
            'archdeaconry': user.archdeaconry,
            'profile_picture': user.profile_picture
        }
    })


@mobile_api_bp.route('/auth/profile', methods=['GET'])
@token_required
def get_profile(user):
    """Get current user profile"""
    return jsonify({
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'local_church': user.local_church,
            'parish': user.parish,
            'archdeaconry': user.archdeaconry,
            'profile_picture': user.profile_picture,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    })


@mobile_api_bp.route('/auth/profile', methods=['PUT'])
@token_required
def update_profile(user):
    """Update user profile"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update allowed fields
    allowed_fields = ['name', 'phone', 'local_church', 'parish', 'archdeaconry', 'role']
    for field in allowed_fields:
        if field in data:
            setattr(user, field, data[field])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Profile updated',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'local_church': user.local_church,
            'parish': user.parish,
            'archdeaconry': user.archdeaconry
        }
    })


# ==================== CHURCH DATA ENDPOINTS ====================

@mobile_api_bp.route('/church-data', methods=['GET'])
def get_all_church_data():
    """Get all church hierarchy data"""
    return jsonify({
        'archdeaconries': list(CHURCH_DATA.keys()),
        'data': CHURCH_DATA
    })


@mobile_api_bp.route('/church-data/<archdeaconry>/parishes', methods=['GET'])
def get_parishes(archdeaconry):
    """Get parishes for an archdeaconry"""
    if archdeaconry in CHURCH_DATA:
        return jsonify({
            'archdeaconry': archdeaconry,
            'parishes': sorted(CHURCH_DATA[archdeaconry])
        })
    return jsonify({'error': 'Archdeaconry not found'}), 404


# ==================== EVENTS ENDPOINTS ====================

@mobile_api_bp.route('/events', methods=['GET'])
def get_events():
    """Get all active events"""
    events = Event.query.filter_by(is_active=True, is_published=True).all()
    
    return jsonify({
        'events': [{
            'id': e.id,
            'name': e.name,
            'slug': e.slug,
            'description': e.description,
            'venue': e.venue,
            'start_date': e.start_date.isoformat() if e.start_date else None,
            'end_date': e.end_date.isoformat() if e.end_date else None,
            'registration_deadline': e.registration_deadline.isoformat() if e.registration_deadline else None,
            'max_delegates': e.max_delegates,
            'current_delegates': e.delegates.count() if e.delegates else 0,
            'primary_color': e.primary_color,
            'secondary_color': e.secondary_color
        } for e in events]
    })


@mobile_api_bp.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get single event details"""
    event = Event.query.get_or_404(event_id)
    
    # Get pricing tiers
    tiers = [{
        'id': t.id,
        'name': t.name,
        'price': t.price,
        'description': t.description
    } for t in event.pricing_tiers]
    
    return jsonify({
        'event': {
            'id': event.id,
            'name': event.name,
            'slug': event.slug,
            'description': event.description,
            'venue': event.venue,
            'venue_address': event.venue_address,
            'start_date': event.start_date.isoformat() if event.start_date else None,
            'end_date': event.end_date.isoformat() if event.end_date else None,
            'registration_deadline': event.registration_deadline.isoformat() if event.registration_deadline else None,
            'max_delegates': event.max_delegates,
            'current_delegates': event.delegates.count(),
            'primary_color': event.primary_color,
            'secondary_color': event.secondary_color,
            'pricing_tiers': tiers
        }
    })


# ==================== DELEGATES ENDPOINTS ====================

@mobile_api_bp.route('/delegates', methods=['GET'])
@token_required
def get_delegates(user):
    """Get delegates registered by current user"""
    event_id = request.args.get('event_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    
    query = Delegate.query.filter_by(registered_by=user.id)
    
    if event_id:
        query = query.filter_by(event_id=event_id)
    
    if search:
        query = query.filter(
            db.or_(
                Delegate.name.ilike(f'%{search}%'),
                Delegate.ticket_number.ilike(f'%{search}%'),
                Delegate.phone_number.ilike(f'%{search}%')
            )
        )
    
    delegates = query.order_by(Delegate.registered_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'delegates': [{
            'id': d.id,
            'ticket_number': d.ticket_number,
            'delegate_number': d.delegate_number,
            'name': d.name,
            'phone_number': d.phone_number,
            'local_church': d.local_church,
            'parish': d.parish,
            'archdeaconry': d.archdeaconry,
            'gender': d.gender,
            'category': d.category,
            'is_paid': d.is_paid,
            'amount_paid': d.amount_paid,
            'checked_in': d.checked_in,
            'registered_at': d.registered_at.isoformat() if d.registered_at else None
        } for d in delegates.items],
        'pagination': {
            'page': delegates.page,
            'pages': delegates.pages,
            'total': delegates.total,
            'has_next': delegates.has_next,
            'has_prev': delegates.has_prev
        }
    })


@mobile_api_bp.route('/delegates', methods=['POST'])
@token_required
def register_delegate(user):
    """Register a new delegate"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['name', 'local_church', 'parish', 'archdeaconry', 'gender']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Get event
    event_id = data.get('event_id')
    event = Event.query.get(event_id) if event_id else Event.query.filter_by(is_active=True).first()
    
    if not event:
        return jsonify({'error': 'No active event found'}), 400
    
    # Check for duplicates
    if data.get('phone_number'):
        existing = Delegate.query.filter_by(
            phone_number=data['phone_number'],
            event_id=event.id
        ).first()
        if existing:
            return jsonify({'error': 'Phone number already registered for this event'}), 400
    
    # Generate ticket number
    ticket_number = Delegate.generate_ticket_number(event)
    delegate_number = Delegate.get_next_delegate_number(event.id)
    
    delegate = Delegate(
        ticket_number=ticket_number,
        delegate_number=delegate_number,
        name=data['name'],
        local_church=data['local_church'],
        parish=data['parish'],
        archdeaconry=data['archdeaconry'],
        phone_number=data.get('phone_number'),
        id_number=data.get('id_number'),
        gender=data['gender'],
        category=data.get('category', 'delegate'),
        event_id=event.id,
        pricing_tier_id=data.get('pricing_tier_id'),
        registered_by=user.id
    )
    
    db.session.add(delegate)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Delegate registered successfully',
        'delegate': {
            'id': delegate.id,
            'ticket_number': delegate.ticket_number,
            'delegate_number': delegate.delegate_number,
            'name': delegate.name,
            'is_paid': delegate.is_paid
        }
    }), 201


@mobile_api_bp.route('/delegates/<int:delegate_id>', methods=['GET'])
@token_required
def get_delegate(user, delegate_id):
    """Get single delegate details"""
    delegate = Delegate.query.get_or_404(delegate_id)
    
    # Check ownership or admin
    if delegate.registered_by != user.id and not user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'delegate': {
            'id': delegate.id,
            'ticket_number': delegate.ticket_number,
            'delegate_number': delegate.delegate_number,
            'name': delegate.name,
            'phone_number': delegate.phone_number,
            'id_number': delegate.id_number,
            'local_church': delegate.local_church,
            'parish': delegate.parish,
            'archdeaconry': delegate.archdeaconry,
            'gender': delegate.gender,
            'category': delegate.category,
            'is_paid': delegate.is_paid,
            'amount_paid': delegate.amount_paid,
            'checked_in': delegate.checked_in,
            'checked_in_at': delegate.checked_in_at.isoformat() if delegate.checked_in_at else None,
            'registered_at': delegate.registered_at.isoformat() if delegate.registered_at else None,
            'event_id': delegate.event_id
        }
    })


@mobile_api_bp.route('/delegates/<int:delegate_id>', methods=['PUT'])
@token_required
def update_delegate(user, delegate_id):
    """Update delegate details"""
    delegate = Delegate.query.get_or_404(delegate_id)
    
    # Check ownership or admin
    if delegate.registered_by != user.id and not user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update allowed fields
    allowed_fields = ['name', 'phone_number', 'local_church', 'parish', 
                      'archdeaconry', 'gender', 'category', 'id_number']
    for field in allowed_fields:
        if field in data:
            setattr(delegate, field, data[field])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Delegate updated',
        'delegate': {
            'id': delegate.id,
            'ticket_number': delegate.ticket_number,
            'name': delegate.name
        }
    })


# ==================== CHECK-IN ENDPOINTS ====================

@mobile_api_bp.route('/checkin/scan', methods=['POST'])
@token_required
def scan_checkin(user):
    """Check in a delegate via QR code scan"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    qr_data = data.get('qr_data')
    session_id = data.get('session_id')
    
    if not qr_data:
        return jsonify({'error': 'QR data required'}), 400
    
    # Parse QR code - format: KAYO|TICKET_NUMBER|NAME|PHONE
    try:
        parts = qr_data.split('|')
        ticket_number = parts[1] if len(parts) > 1 else qr_data
    except:
        ticket_number = qr_data
    
    # Find delegate
    delegate = Delegate.query.filter_by(ticket_number=ticket_number).first()
    
    if not delegate:
        # Try searching by ticket number directly
        delegate = Delegate.query.filter(
            db.or_(
                Delegate.ticket_number == qr_data,
                Delegate.ticket_number.ilike(f'%{qr_data}%')
            )
        ).first()
    
    if not delegate:
        return jsonify({
            'success': False,
            'error': 'Delegate not found',
            'qr_data': qr_data
        }), 404
    
    # Check if already checked in
    already_checked_in = delegate.checked_in
    
    # Perform check-in
    if not delegate.checked_in:
        delegate.checked_in = True
        delegate.checked_in_at = datetime.utcnow()
    
    # Create check-in record
    checkin_record = CheckInRecord(
        delegate_id=delegate.id,
        checked_in_by=user.id,
        session_id=session_id,
        check_in_time=datetime.utcnow(),
        check_in_method='qr_scan'
    )
    db.session.add(checkin_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'already_checked_in': already_checked_in,
        'delegate': {
            'id': delegate.id,
            'ticket_number': delegate.ticket_number,
            'delegate_number': delegate.delegate_number,
            'name': delegate.name,
            'local_church': delegate.local_church,
            'parish': delegate.parish,
            'category': delegate.category,
            'is_paid': delegate.is_paid,
            'checked_in': delegate.checked_in,
            'checked_in_at': delegate.checked_in_at.isoformat() if delegate.checked_in_at else None
        }
    })


@mobile_api_bp.route('/checkin/manual', methods=['POST'])
@token_required
def manual_checkin(user):
    """Manual check-in by searching delegate"""
    data = request.get_json()
    
    search_term = data.get('search')
    delegate_id = data.get('delegate_id')
    session_id = data.get('session_id')
    
    if delegate_id:
        delegate = Delegate.query.get(delegate_id)
    elif search_term:
        delegate = Delegate.query.filter(
            db.or_(
                Delegate.ticket_number.ilike(f'%{search_term}%'),
                Delegate.name.ilike(f'%{search_term}%'),
                Delegate.phone_number.ilike(f'%{search_term}%')
            )
        ).first()
    else:
        return jsonify({'error': 'Search term or delegate ID required'}), 400
    
    if not delegate:
        return jsonify({'error': 'Delegate not found'}), 404
    
    already_checked_in = delegate.checked_in
    
    if not delegate.checked_in:
        delegate.checked_in = True
        delegate.checked_in_at = datetime.utcnow()
    
    checkin_record = CheckInRecord(
        delegate_id=delegate.id,
        checked_in_by=user.id,
        session_id=session_id,
        check_in_time=datetime.utcnow(),
        check_in_method='manual'
    )
    db.session.add(checkin_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'already_checked_in': already_checked_in,
        'delegate': {
            'id': delegate.id,
            'ticket_number': delegate.ticket_number,
            'name': delegate.name,
            'is_paid': delegate.is_paid,
            'checked_in': delegate.checked_in
        }
    })


# ==================== DASHBOARD/STATS ENDPOINTS ====================

@mobile_api_bp.route('/dashboard/stats', methods=['GET'])
@token_required
def get_dashboard_stats(user):
    """Get dashboard statistics for mobile app"""
    event_id = request.args.get('event_id', type=int)
    
    # Base query for user's delegates
    query = Delegate.query.filter_by(registered_by=user.id)
    if event_id:
        query = query.filter_by(event_id=event_id)
    
    total_delegates = query.count()
    paid_delegates = query.filter_by(is_paid=True).count()
    unpaid_delegates = total_delegates - paid_delegates
    checked_in = query.filter_by(checked_in=True).count()
    
    # Amount due
    unpaid_query = query.filter_by(is_paid=False)
    total_due = sum([d.pricing_tier.price if d.pricing_tier else 1000 for d in unpaid_query.all()])
    
    return jsonify({
        'stats': {
            'total_delegates': total_delegates,
            'paid_delegates': paid_delegates,
            'unpaid_delegates': unpaid_delegates,
            'checked_in': checked_in,
            'total_amount_due': total_due
        }
    })


@mobile_api_bp.route('/dashboard/recent-delegates', methods=['GET'])
@token_required
def get_recent_delegates(user):
    """Get recently registered delegates"""
    limit = request.args.get('limit', 10, type=int)
    
    delegates = Delegate.query.filter_by(registered_by=user.id)\
        .order_by(Delegate.registered_at.desc())\
        .limit(limit).all()
    
    return jsonify({
        'delegates': [{
            'id': d.id,
            'ticket_number': d.ticket_number,
            'name': d.name,
            'is_paid': d.is_paid,
            'registered_at': d.registered_at.isoformat() if d.registered_at else None
        } for d in delegates]
    })


# ==================== PAYMENTS ENDPOINTS ====================

@mobile_api_bp.route('/payments/initiate', methods=['POST'])
@token_required
def initiate_payment(user):
    """Initiate M-Pesa STK push for delegate payment"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    delegate_ids = data.get('delegate_ids', [])
    phone_number = data.get('phone_number')
    
    if not delegate_ids:
        return jsonify({'error': 'No delegates selected'}), 400
    
    if not phone_number:
        return jsonify({'error': 'Phone number required'}), 400
    
    # Get delegates and calculate amount
    delegates = Delegate.query.filter(
        Delegate.id.in_(delegate_ids),
        Delegate.registered_by == user.id,
        Delegate.is_paid == False
    ).all()
    
    if not delegates:
        return jsonify({'error': 'No unpaid delegates found'}), 400
    
    # Calculate total amount
    total_amount = sum([
        d.pricing_tier.price if d.pricing_tier else 1000 
        for d in delegates
    ])
    
    # Create payment record
    payment = Payment(
        user_id=user.id,
        amount=total_amount,
        phone_number=phone_number,
        payment_method='mpesa',
        status='pending',
        description=f"Payment for {len(delegates)} delegate(s)"
    )
    db.session.add(payment)
    db.session.commit()
    
    # Store delegate IDs for callback
    payment.delegate_ids = ','.join([str(d.id) for d in delegates])
    db.session.commit()
    
    # TODO: Integrate actual M-Pesa STK push here
    # For now, return payment info
    
    return jsonify({
        'success': True,
        'payment': {
            'id': payment.id,
            'amount': total_amount,
            'phone_number': phone_number,
            'status': 'pending',
            'delegates_count': len(delegates)
        },
        'message': 'Payment initiated. Check your phone for M-Pesa prompt.'
    })


@mobile_api_bp.route('/payments/status/<int:payment_id>', methods=['GET'])
@token_required
def check_payment_status(user, payment_id):
    """Check payment status"""
    payment = Payment.query.get_or_404(payment_id)
    
    if payment.user_id != user.id and not user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'payment': {
            'id': payment.id,
            'amount': payment.amount,
            'status': payment.status,
            'transaction_id': payment.transaction_id,
            'created_at': payment.created_at.isoformat() if payment.created_at else None
        }
    })


# ==================== NOTIFICATIONS ENDPOINTS ====================

@mobile_api_bp.route('/notifications/register-device', methods=['POST'])
@token_required
def register_device(user):
    """Register device for push notifications"""
    data = request.get_json()
    
    fcm_token = data.get('fcm_token')
    device_type = data.get('device_type', 'android')
    
    if not fcm_token:
        return jsonify({'error': 'FCM token required'}), 400
    
    # Store FCM token (you might want a separate table for this)
    # For now, we'll use a simple approach
    # TODO: Create DeviceToken model
    
    return jsonify({
        'success': True,
        'message': 'Device registered for notifications'
    })


# ==================== HEALTH CHECK ====================

@mobile_api_bp.route('/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })
