from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import requests
from flask import Flask, send_file, request, render_template, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/welcome')
def generate_welcome_image():
    username = request.args.get('username')
    displayname = request.args.get('displayname')
    avatar = request.args.get('avatar')
    avatar_image = Image.open(requests.get(avatar, stream=True).raw).convert("RGBA").resize((160, 160))

    base_image = Image.open("assets/cards/welcome_card_base.png")
    font1 = ImageFont.truetype("assets/fonts/ggfont.woff", 50)
    font2 = ImageFont.truetype("assets/fonts/ggfont.woff", 30)

    # cut the avatar in circle & paste it on the welcome card
    mask = Image.new("L", avatar_image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar_image.size[0], avatar_image.size[1]), fill=255)
    avatar_image = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
    avatar_image.putalpha(mask)
    draw = ImageDraw.Draw(base_image)
    base_image.paste(avatar_image, (100, 95), avatar_image)

    if len(displayname) > 13:
        displayname = f'{displayname[:10]}...'
    if len(username) > 20:
        username = f'{username[:17]}...'

    # paste the username & display name on the welcome card
    draw.text((320, 120), displayname, fill=(255, 255, 255), font=font1)
    draw.text((320, 180), username, fill="#dddddd", font=font2)
    
    img_byte_array = BytesIO()
    base_image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)

    return send_file(img_byte_array, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)
