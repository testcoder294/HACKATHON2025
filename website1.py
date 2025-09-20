from werkzeug.utils import secure_filename
import os
import json
from flask import Flask, render_template, url_for, abort, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

# === App setup ===
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Image upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Make current_user available in templates
@app.context_processor
def inject_user():
    return dict(current_user=current_user)


# === Models ===
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    logs = db.relationship('FoodLog', backref='user', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)


class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    nutrition = db.Column(db.Text, nullable=False)  # Store JSON string
    price = db.Column(db.Float, nullable=False)
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
    food_items = FoodItem.query.all()
    # Decode nutrition for each food item
    food_with_nutrition = []
    for item in food_items:
        try:
            nutrition = json.loads(item.nutrition)
        except:
            nutrition = {}
        food_with_nutrition.append({
            'id': item.id,
            'name': item.name,
            'image': item.image,
            'price': item.price,
            'is_healthy': item.is_healthy,
            'nutrition': nutrition
        })
    return render_template('index.html', food_items=food_with_nutrition)



@app.route('/food/<int:food_id>')
def food_detail(food_id):
    item = FoodItem.query.get_or_404(food_id)
    nutrition = {}
    try:
        nutrition = json.loads(item.nutrition)
    except:
        pass
    return render_template('food_detail.html', item=item, nutrition=nutrition)


@app.route('/dashboard')
@login_required
def dashboard():
    logs = FoodLog.query.filter_by(user_id=current_user.id).order_by(FoodLog.date.desc()).all()
    total_calories = 0
    healthy_count = 0
    junk_count = 0
    for log in logs:
        food = FoodItem.query.get(log.food_id)
        nutrition = json.loads(food.nutrition)
        cal = nutrition.get('Calories', '0').split()[0]
        try:
            total_calories += int(cal)
        except:
            pass
        if log.is_healthy:
            healthy_count += 1
        else:
            junk_count += 1
    return render_template('dashboard.html',
                           logs=logs,
                           total_calories=total_calories,
                           healthy_count=healthy_count,
                           junk_count=junk_count)


@app.route('/log_food/<int:food_id>', methods=['POST'])
@login_required
def log_food(food_id):
    food = FoodItem.query.get_or_404(food_id)
    log = FoodLog(user_id=current_user.id,
                  food_id=food.id,
                  date=date.today(),
                  is_healthy=food.is_healthy)
    db.session.add(log)
    db.session.commit()
    flash(f'Logged {food.name} as consumed!')
    return redirect('/dashboard')


# === Auth Routes ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect('/')
        else:
            flash('Invalid username or password!', 'error')
            return redirect('/login')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists!')
            return redirect('/register')
        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect('/login')
    return render_template('register.html')


# === Admin: Add Food ===
@app.route('/add_food', methods=['GET', 'POST'])
@login_required
def add_food():
    if not current_user.is_admin:
        return 'Forbidden: Admins only', 403

    if request.method == 'POST':
        name = request.form['name']

        # Handle uploaded image
        file = request.files['image']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_path = f'uploads/{filename}'
        else:
            image_path = ''

        nutrition = {
            'Calories': request.form.get('calories', ''),
            'Protein': request.form.get('protein', ''),
            'Fat': request.form.get('fat', ''),
            'Carbs': request.form.get('carbs', '')
        }
        price = float(request.form['price'])
        is_healthy = request.form.get('is_healthy') == 'on'

        food = FoodItem(
            name=name,
            image=image_path,
            nutrition=json.dumps(nutrition),
            price=price,
            is_healthy=is_healthy
        )
        db.session.add(food)
        db.session.commit()
        flash('Food item added!')
        return redirect('/')
    return render_template('add_food.html')


# === Admin: Edit Food ===
@app.route('/edit_food/<int:food_id>', methods=['GET', 'POST'])
@login_required
def edit_food(food_id):
    if not current_user.is_admin:
        return 'Forbidden: Admins only', 403

    item = FoodItem.query.get_or_404(food_id)

    if request.method == 'POST':
        item.name = request.form['name']

        # Handle image upload
        image = request.form.get('image', '')
        image_file = request.files.get('image_file')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            image = f'uploads/{filename}'
        item.image = image

        # Price
        item.price = float(request.form['price'])

        # Nutrition (store as JSON string always)
        try:
            nutrition_dict = json.loads(request.form['nutrition'])
            item.nutrition = json.dumps(nutrition_dict)
        except:
            item.nutrition = request.form['nutrition']

        # Healthy toggle
        item.is_healthy = 'is_healthy' in request.form

        db.session.commit()
        flash('Food item updated!', 'success')
        return redirect(url_for('food_detail', food_id=item.id))

    return render_template('edit_food.html', item=item)


if __name__ == '__main__':
    app.run(debug=True)
