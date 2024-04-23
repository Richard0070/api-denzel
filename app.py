from flask import Flask, request, send_file, render_template_string, jsonify
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import os
import io
import random 
import string

app = Flask(__name__)

BASE_URL = 'https://api-denzel.vercel.app/'
links_storage = {}

@app.route("/")
def start():
    return "API Denzel is Running"
    
@app.route("/check")
def mbsa():
    return render_template('index.html')

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/generate_link', methods=['GET'])
def generate_link():
    link = request.args.get('link')
    if not link:
        return jsonify({'error': 'Missing link parameter'})

    random_string = generate_random_string()
    new_link = BASE_URL + random_string
    links_storage[random_string] = link  # Store the link in the dictionary
    
    return jsonify({'new_link': new_link})

@app.route('/<random_string>', methods=['GET'])
def embed_image(random_string):
    link = links_storage.get(random_string)
    if not link:
        return jsonify({'error': 'Link not found'})

    return render_template('embed.html', image_url=link)

@app.route('/card')
def generate_rank_card():
    name = request.args.get('name')
    level = int(request.args.get('level', 0))
    avatarurl = request.args.get('avatarurl')
    xp = int(request.args.get('xp', 0))
    totalxp = int(request.args.get('totalxp', 0))
    rank = int(request.args.get('rank', 0))

    base_image = Image.open('card.jpg')
    draw = ImageDraw.Draw(base_image)
    username_font_size = 30
    info_font_size = 25
    username_font = ImageFont.truetype("fonts/mont_bold.ttf", username_font_size)
    info_font = ImageFont.truetype("fonts/mont.ttf", info_font_size)

    username = name
    if len(username) > 12:
        username = f'{username[:12]}...'

    avatar_image = Image.open(requests.get(avatarurl, stream=True).raw).convert("RGBA").resize((110, 110))
    mask = Image.new('L', avatar_image.size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, *avatar_image.size), fill=255)
    circular_avatar = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
    circular_avatar.putalpha(mask)
    coordinate = (base_image.height - circular_avatar.height) // 2
    base_image.paste(circular_avatar, (30, coordinate), circular_avatar)

    draw.text((185, 43), f'{username}', font=username_font, fill=(255, 255, 255))
    draw.text((185, 83), f'Level {level} | XP: {xp} / {totalxp}', font=info_font, fill=(255, 255, 255))
    draw.text((185, 115), f'Rank: {rank}', font=info_font, fill=(255, 255, 255))

    progress_percent = (xp / totalxp) * 100
    progress_length = int(base_image.width * (progress_percent / 100))

    draw.rectangle([(0, base_image.height - 5),
                    (progress_length, base_image.height)],
                   fill=(255, 255, 255))

    img_byte_array = io.BytesIO()
    base_image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)

    return send_file(img_byte_array, mimetype='image/png')

@app.route("/card2")
def generate_card():
    username = request.args.get('username')
    balance = int(request.args.get('balance'))
    vip = request.args.get('vip', '').lower() == 'true'

    base_image = Image.open('card_base.png')

    if len(username) > 12:
        username = f'{username[:12]}...'

    if balance > 1000:
        balance = f'{balance / 1000:.1f}k'

    avatarurl = request.args.get('avatarurl')
    avatar_image = Image.open(requests.get(avatarurl, stream=True).raw).convert("RGBA").resize((380, 380))
    mask = Image.new('L', (380, 380), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, 380, 380), fill=255)
    circular_avatar = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
    circular_avatar.putalpha(mask)
    base_image.paste(circular_avatar, (180, 130), circular_avatar)

    draw = ImageDraw.Draw(base_image)
    font = ImageFont.truetype("fonts/book.ttf", 100)
    draw.text((700, 160), f"Username: {username}", fill="white", font=font)
    draw.text((700, 330), f"Laddoos: {balance}", fill="white", font=font)

    if vip:
        vip_path = "vip.png"
        vip_image = Image.open(vip_path).resize((300, 200))
        base_image.paste(vip_image, (1900, 180))

    img_byte_array = io.BytesIO()
    base_image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)

    return send_file(img_byte_array, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)
    
