from website1 import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create all tables
    db.create_all()

    # Check if an admin already exists
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin123"),  # default password
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Database initialized and default admin created (username=admin, password=admin123)")
    else:
        print("✅ Database already initialized, admin exists")
