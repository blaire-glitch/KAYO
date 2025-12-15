#!/usr/bin/env python
"""Script to create all database tables"""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

# Import ALL models explicitly
from app.models.user import User
from app.models.delegate import Delegate
from app.models.event import Event, PricingTier, CustomField
from app.models.payment import Payment
from app.models.audit import AuditLog, Role
from app.models.permission_request import PermissionRequest
from app.models.fund_management import Pledge, PledgePayment, ScheduledPayment, Installment, FundTransfer
from app.models.operations import CheckInSession, CheckIn, Announcement

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("All tables created successfully")
    
    # Verify pledges table exists
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables in database: {tables}")
    
    if 'pledges' in tables:
        print("SUCCESS: pledges table exists")
    else:
        print("WARNING: pledges table was NOT created")
