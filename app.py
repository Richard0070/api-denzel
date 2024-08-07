from flask import Flask, request, send_file, jsonify, render_template_string
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import os
import io
from gemini import Gemini

app = Flask(__name__)

@app.route("/")
def start():
    return "Denzel™ is Running"

@app.route('/translate', methods=['GET'])
def get_translation():
    text = request.args.get('text')
    key1 = request.args.get('key1')
    
    if not text:
        return jsonify({"error": "Text to be translated is missing."}), 400
    if not key1:
        return jsonify({"error": "Cookie value is missing."}), 400
    
    query = f"what's the translation for \"{text}\"? just send the translated text in english. do not add anything else. if it's a slur, just say \"Slur Detected\"."
    cookies = {"__Secure-1PSID": key1}
    
    try:
        client = Gemini(cookies=cookies)
        translation = client.generate_content(query)
        translation_text = translation.payload.get('candidates', [{}])[0].get('text', '')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"translation": translation_text.strip()})

@app.route('/welcome')
def generate_welcome_image():
    username = request.args.get('username')
    displayname = request.args.get('displayname')
    base_image = Image.open("wlcm.png")

    avatar = request.args.get('avatar')
    avatar_image = Image.open(requests.get(avatar, stream=True).raw).convert("RGBA").resize((160, 160))
     
    mask = Image.new("L", avatar_image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar_image.size[0], avatar_image.size[1]), fill=255)
    avatar_image = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
    avatar_image.putalpha(mask)

    font1 = ImageFont.truetype("fonts/ggfont.woff", 50)
    font2 = ImageFont.truetype("fonts/ggfont.woff", 30)

    draw = ImageDraw.Draw(base_image)

    base_image.paste(avatar_image, (100, 95), avatar_image)

    if len(displayname) > 13:
        displayname = f'{displayname[:10]}...'

    if len(username) > 20:
        username = f'{username[:17]}...'

    draw.text((320, 120), displayname, fill=(255, 255, 255), font=font1)
    draw.text((320, 180), username, fill="#dddddd", font=font2)
    
    img_byte_array = io.BytesIO()
    base_image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)

    return send_file(img_byte_array, mimetype='image/png')


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

if __name__ == "__main__":
    app.run(debug=True)
