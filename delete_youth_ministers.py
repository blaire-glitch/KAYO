"""Script to delete all users with youth_minister role from the database."""
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    youth_ministers = User.query.filter_by(role='youth_minister').all()
    print(f'Found {len(youth_ministers)} youth minister users:')
    for ym in youth_ministers:
        print(f'  - ID: {ym.id}, Name: {ym.name}, Email: {ym.email}')
    
    if youth_ministers:
        for ym in youth_ministers:
            db.session.delete(ym)
        db.session.commit()
        print(f'\nDeleted {len(youth_ministers)} youth minister users.')
    else:
        print('\nNo youth minister users to delete.')
