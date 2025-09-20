import os
import json
from flask import Flask, render_template, url_for, abort, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
from datetime import date
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure current_user is available in all templates
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
	nutrition = db.Column(db.Text, nullable=False)  # Store as JSON string
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

@app.route('/logout')
@login_required
def logout():
	logout_user()
	flash('Logged out successfully!')
	return redirect('/')


@app.route('/')
def index():
	food_items = FoodItem.query.all()
	return render_template('index.html', food_items=food_items)

@app.route('/food/<int:food_id>')
def food_detail(food_id):
	item = FoodItem.query.get_or_404(food_id)
	return render_template('food_detail.html', item=item)



# To initialize the database, run this once in Python shell:
# >>> from website1 import db
# >>> db.create_all()





# User dashboard
@app.route('/dashboard')
@login_required
def dashboard():
	logs = FoodLog.query.filter_by(user_id=current_user.id).order_by(FoodLog.date.desc()).all()
	total_calories = 0
	healthy_count = 0
	junk_count = 0
	for log in logs:
		food = FoodItem.query.get(log.food_id)
		# Assume nutrition is stored as JSON string
		import json
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
	return render_template('dashboard.html', logs=logs, total_calories=total_calories, healthy_count=healthy_count, junk_count=junk_count)

# Log food consumption
@app.route('/log_food/<int:food_id>', methods=['POST'])
@login_required
def log_food(food_id):
	food = FoodItem.query.get_or_404(food_id)
	log = FoodLog(user_id=current_user.id, food_id=food.id, date=date.today(), is_healthy=food.is_healthy)
	db.session.add(log)
	db.session.commit()
	flash(f'Logged {food.name} as consumed!')
	return redirect('/dashboard')

# === Auth routes ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!')
            return redirect('/')
        else:
            flash('Invalid username or password!')
            return redirect('/login')
    return render_template('login.html')

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

# Add food item (admin only)
@app.route('/add_food', methods=['GET', 'POST'])
@login_required
def add_food():
    if not current_user.is_admin:
        return 'Forbidden: Admins only', 403
    if request.method == 'POST':
        name = request.form['name']
        image = request.form['image']
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
            image=image,
            nutrition=json.dumps(nutrition),
            price=price,
            is_healthy=is_healthy
        )
        db.session.add(food)
        db.session.commit()
        flash('Food item added!')
        return redirect('/')
    return render_template('add_food.html')

if __name__ == '__main__':
	app.run(debug=True)