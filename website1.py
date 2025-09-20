from flask import Flask, render_template, url_for, abort
app = Flask(__name__)

# Example food items data
food_items = [
	{
		'id': 1,
		'name': 'Veg Sandwich',
		'image': 'veg_sandwich.jpg',
		'nutrition': {
			'Calories': '250 kcal',
			'Protein': '8g',
			'Fat': '6g',
			'Carbs': '40g'
		}
	},
	{
		'id': 2,
		'name': 'Paneer Roll',
		'image': 'paneer_roll.jpg',
		'nutrition': {
			'Calories': '320 kcal',
			'Protein': '12g',
			'Fat': '10g',
			'Carbs': '45g'
		}
	},
	# Add more items as needed
]

@app.route('/')
def index():
	return render_template('index.html', food_items=food_items)

@app.route('/food/<int:food_id>')
def food_detail(food_id):
	item = next((f for f in food_items if f['id'] == food_id), None)
	if not item:
		abort(404)
	return render_template('food_detail.html', item=item)


if __name__ == '__main__':
	app.run(debug=True)