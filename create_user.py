"""
Script to create initial admin user
Run: python create_user.py
"""

from app import app
from extensions import db
from models.user import User


def create_admin():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if admin already exists
        existing = User.query.filter_by(username='admin').first()
        if existing:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")


if __name__ == '__main__':
    create_admin()
