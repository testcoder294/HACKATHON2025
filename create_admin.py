from website1 import app, db, User
from werkzeug.security import generate_password_hash

# Change these values as needed
admin_username = 'admin'
admin_email = 'admin@example.com'
admin_password = 'admin123'

with app.app_context():
    existing = User.query.filter_by(username=admin_username).first()
    if existing:
        existing.is_admin = True
        existing.email = admin_email
        existing.password_hash = generate_password_hash(admin_password)
        print('Updated existing user to admin.')
    else:
        admin = User(
            username=admin_username,
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            is_admin=True
        )
        db.session.add(admin)
        print('Created new admin user.')
    db.session.commit()
    print('Done.')
