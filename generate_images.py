from PIL import Image, ImageDraw, ImageFont
import os

# Food items and filenames
food_images = [
    ('veg_sandwich.jpg', 'Veg Sandwich'),
    ('paneer_roll.jpg', 'Paneer Roll'),
]

os.makedirs('static/images', exist_ok=True)

for filename, label in food_images:
    img = Image.new('RGB', (300, 200), color=(255, 165, 0))  # Orange background
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', 28)
    except:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), label, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((300-w)/2, (200-h)/2), label, fill=(255,255,255), font=font)
    img.save(f'static/images/{filename}')
print('Placeholder images created.')
