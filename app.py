from flask import Flask, request, send_file, jsonify, render_template_string
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import os
import io
from bardapi import BardCookies
from playwright.async_api import async_playwright

app = Flask(__name__)

@app.route("/")
def start():
    return "API Denzel is Running"

@app.route('/screenshot', methods=['GET'])
async def screenshot():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    async with async_playwright() as p:
        
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        screenshot = await page.screenshot(path=screenshot_path)
        await browser.close()
        
        img_byte_array = io.BytesIO(screenshot)
        img_byte_array.seek(0)

        return send_file(img_byte_array, mimetype='image/png')

@app.route('/bard', methods=['GET'])
def get_answer():
    question = request.args.get('question')
    key1 = request.args.get('key1')
    key2 = request.args.get('key2')
    
    if not question:
        return jsonify({"error": "Question parameter is missing."}), 400
    
    cookie_dict = {
        "__Secure-1PSID": key1,
        "__Secure-1PSIDCC": key2,
    }
    
    bard = BardCookies(cookie_dict=cookie_dict)
    answer = bard.get_answer(question)['content']
   
    return jsonify({"answer": answer})

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
