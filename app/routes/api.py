from flask import Blueprint, jsonify
from app.church_data import CHURCH_DATA, get_parishes

api_bp = Blueprint('api', __name__, url_prefix='/api')


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
