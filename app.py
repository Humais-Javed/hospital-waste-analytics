"""
Medical Waste Monitoring Dashboard
Main application entry point
"""

from flask import Flask
from config import Config
from extensions import db, login_manager


def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Import models (required for db.create_all)
    from models.user import User
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Load data on startup
    from data_service import load_data
    with app.app_context():
        db.create_all()  # Create database tables
        load_data()      # Load waste data
        
        # Create default admin user if none exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created")
    
    return app


# Create the app instance
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=5001)
