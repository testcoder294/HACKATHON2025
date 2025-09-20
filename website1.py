from datetime import date
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
from flask import Flask, render_template, url_for, abort

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, redirect, flash, session
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))
# To initialize the database, run this once in Python shell:
# >>> from website1 import db
# >>> db.create_all()

# User registration
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

# User login
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
	return render_template('login.html')

# User logout
@app.route('/logout')
@login_required
def logout():
	logout_user()
	flash('Logged out successfully!')
	return redirect('/')

# User model
class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True, nullable=False)
	email = db.Column(db.String(120), unique=True, nullable=False)
	password_hash = db.Column(db.String(128), nullable=False)
	logs = db.relationship('FoodLog', backref='user', lazy=True)

# Food item model
class FoodItem(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(100), nullable=False)
	image = db.Column(db.String(100), nullable=False)
	nutrition = db.Column(db.Text, nullable=False)  # Store as JSON string
	price = db.Column(db.Float, nullable=False)
	is_healthy = db.Column(db.Boolean, default=True)
	logs = db.relationship('FoodLog', backref='food', lazy=True)

# Food log model
class FoodLog(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	food_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
	date = db.Column(db.Date, nullable=False)
	is_healthy = db.Column(db.Boolean, nullable=False)

# To initialize the database, run this once in Python shell:
# >>> from website1 import db
# >>> db.create_all()

@app.route('/')
def index():
	food_items = FoodItem.query.all()
	return render_template('index.html', food_items=food_items)

@app.route('/food/<int:food_id>')
def food_detail(food_id):
	item = FoodItem.query.get_or_404(food_id)
	return render_template('food_detail.html', item=item)


if __name__ == '__main__':
	app.run(debug=True)