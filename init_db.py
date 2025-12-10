"""
Script to initialize the database and create an admin user.
Run this after setting up your environment:
    python init_db.py
"""

from app import create_app, db
from app.models import User

app = create_app()


def init_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created successfully!")
        
        # Check if admin exists
        admin = User.query.filter_by(email='admin@kayo.org').first()
        
        if not admin:
            # Create default admin user
            admin = User(
                name='Admin',
                email='admin@kayo.org',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin user created!")
            print("  Email: admin@kayo.org")
            print("  Password: admin123")
            print("  ⚠️  Please change this password immediately!")
        else:
            print("ℹ Admin user already exists.")
        
        print("\n✓ Database initialization complete!")


if __name__ == '__main__':
    init_database()
