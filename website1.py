# website1.py
import os
import json
from datetime import date
from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin, LoginManager, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# === App Setup ===
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# === Context processor ===
@app.context_processor
def inject_user():
    return dict(current_user=current_user)


# === Models ===
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    logs = db.relationship('FoodLog', backref='user', lazy=True)


class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    nutrition = db.Column(db.Text, nullable=False)  # JSON string
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)  # NEW FIELD
    is_healthy = db.Column(db.Boolean, default=True)
    logs = db.relationship('FoodLog', backref='food', lazy=True)


class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_healthy = db.Column(db.Boolean, nullable=False)


# === User loader ===
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# === Routes ===

@app.route('/')
def index():
    # Return list of dicts with decoded nutrition to avoid template .get errors
    items = FoodItem.query.all()
    prepared = []
    for it in items:
        try:
            nutrition = json.loads(it.nutrition)
        except Exception:
            nutrition = {}
        prepared.append({
            "id": it.id,
            "name": it.name,
            "image": it.image,
            "price": it.price,
            "description": it.description,
            "is_healthy": it.is_healthy,
            "nutrition": nutrition
        })
    return render_template('index.html', food_items=prepared)


@app.route('/food/<int:food_id>')
def food_detail(food_id):
    item = FoodItem.query.get_or_404(food_id)
    nutrition = {}
    try:
        nutrition = json.loads(item.nutrition)
    except Exception:
        nutrition = {}
    return render_template('food_detail.html', item=item, nutrition=nutrition)


@app.route('/dashboard')
@login_required
def dashboard():
    logs = FoodLog.query.filter_by(user_id=current_user.id).order_by(FoodLog.date.desc()).all()
    total_calories = 0
    healthy_count = 0
    junk_count = 0
    total_spent = 0.0
    for log in logs:
        food = FoodItem.query.get(log.food_id)
        try:
            nutrition = json.loads(food.nutrition)
            cal = nutrition.get('Calories', '0').split()[0]
            total_calories += int(cal)
        except Exception:
            pass
        if food:
            total_spent += float(food.price or 0)
        if log.is_healthy:
            healthy_count += 1
        else:
            junk_count += 1
    return render_template(
        'dashboard.html',
        logs=logs,
        total_calories=total_calories,
        healthy_count=healthy_count,
        junk_count=junk_count,
        total_spent=total_spent
    )


@app.route('/log_food/<int:food_id>', methods=['POST'])
@login_required
def log_food(food_id):
    food = FoodItem.query.get_or_404(food_id)
    log = FoodLog(user_id=current_user.id, food_id=food.id, date=date.today(), is_healthy=food.is_healthy)
    db.session.add(log)
    db.session.commit()
    flash(f'Logged {food.name} as consumed!', 'success')
    return redirect('/dashboard')


@app.route('/add_food', methods=['GET', 'POST'])
@login_required
def add_food():
    if not current_user.is_admin:
        return 'Forbidden: Admins only', 403

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        # Image handling
        file = request.files.get('image')
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_path = f'uploads/{filename}'
        else:
            # allow manual filename but always prefix uploads/
            manual = request.form.get('image', '').strip()
            image_path = f'uploads/{manual}' if manual else ''

        nutrition = {
            'Calories': request.form.get('calories', '').strip(),
            'Protein': request.form.get('protein', '').strip(),
            'Fat': request.form.get('fat', '').strip(),
            'Carbs': request.form.get('carbs', '').strip()
        }
        try:
            price = float(request.form.get('price', 0))
        except ValueError:
            price = 0.0
        is_healthy = request.form.get('is_healthy') == 'on'

        food = FoodItem(
            name=name,
            image=image_path,
            nutrition=json.dumps(nutrition),
            price=price,
            description=description,
            is_healthy=is_healthy
        )
        db.session.add(food)
        db.session.commit()
        flash('Food item added!', 'success')
        return redirect('/')

    return render_template('add_food.html')


@app.route('/edit_food/<int:food_id>', methods=['GET', 'POST'])
@login_required
def edit_food(food_id):
    if not current_user.is_admin:
        return 'Forbidden: Admins only', 403

    item = FoodItem.query.get_or_404(food_id)

    if request.method == 'POST':
        item.name = request.form.get('name', item.name).strip()
        try:
            item.price = float(request.form.get('price', item.price))
        except ValueError:
            pass
        item.description = request.form.get('description', item.description)
        item.is_healthy = 'is_healthy' in request.form

        # Nutrition: accept JSON string from form; ensure it's stored as string
        posted_nut = request.form.get('nutrition', None)
        if posted_nut is not None:
            # If admin entered JSON text, try to validate
            try:
                parsed = json.loads(posted_nut)
                item.nutrition = json.dumps(parsed)
            except Exception:
                # if invalid JSON, keep as raw string (not ideal) — but prefer validated
                item.nutrition = posted_nut

        # Image upload
        image_file = request.files.get('image_file')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            item.image = f'uploads/{filename}'
        else:
            manual = request.form.get('image', '').strip()
            if manual:
                item.image = f'uploads/{manual}'

        db.session.commit()
        flash('Food item updated!', 'success')
        return redirect(url_for('food_detail', food_id=item.id))

    # prepare nutrition text for textarea (stringified JSON for editing)
    try:
        nutrition_text = json.dumps(json.loads(item.nutrition), indent=2)
    except Exception:
        nutrition_text = item.nutrition
    return render_template('edit_food.html', item=item, nutrition_text=nutrition_text)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect('/')
        else:
            flash('Invalid username or password!', 'error')
            return redirect('/login')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists!', 'error')
            return redirect('/register')
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect('/login')
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
