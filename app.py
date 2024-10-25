from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import requests
from flask import Flask, send_file, request, render_template, jsonify, redirect, make_response
import os
from urllib.parse import urlencode

app = Flask(__name__)

store = {}

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

@app.route("/")
def index():
    return render_template('index.html') 
    
@app.route('/linked-role')
def linked_role():
    state = os.urandom(16).hex()
    url = (
        "https://discord.com/api/oauth2/authorize?"
        + urlencode({
            "client_id": DISCORD_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "identify role_connections.write",
            "state": state,
        })
    )
    
    resp = make_response(redirect(url))
    resp.set_cookie('clientState', state, max_age=300)
    return resp

@app.route('/discord-oauth-callback')
def discord_oauth_callback():
    try:
        code = request.args.get('code')
        discord_state = request.args.get('state')
        client_state = request.cookies.get('clientState')

        if client_state != discord_state:
            return 'State verification failed.', 403

        tokens = get_oauth_tokens(code)
        user_data = get_user_data(tokens)
        user_id = user_data['id']

        store[user_id] = {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "expires_at": tokens['expires_at'],
        }

        update_metadata(user_id)

        return 'Woohoo! Welcome to the club, pal :D'
    except Exception as e:
        return f'An error occurred. {e}', 500

@app.route('/update-metadata', methods=['POST'])
def update_metadata_route():
    user_id = request.json.get('user_id')
    try:
        update_metadata(user_id)
        return '', 204
    except Exception as e:
        return 'An error occurred.', 500

def update_metadata(user_id):
    tokens = store.get(user_id)
    if not tokens:
        raise Exception("User not found.")

    metadata = {
        "cookieseaten": 1483,
        "allergictonuts": 0,
        "firstcookiebaked": "2003-12-20",
    }

    push_metadata(user_id, tokens, metadata)

def get_oauth_tokens(code):
    token_url = "https://discord.com/api/v10/oauth2/token"
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify role_connections.write"
    }
    response = requests.post(token_url, data=data)
    if response.ok:
        return response.json()    
    raise Exception(f"Failed to get OAuth tokens. {response.status_code} - {response.text} | {code} | {data}")

def get_user_data(tokens):
    user_url = "https://discord.com/api/v10/users/@me"
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}"
    }
    response = requests.get(user_url, headers=headers)
    if response.ok:
        return response.json()
    raise Exception("Failed to fetch user data.")

def push_metadata(user_id, tokens, metadata):
    url = f"https://discord.com/api/v10/users/@me/applications/{os.getenv('DISCORD_APPLICATION_ID')}/role-connection"
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json",
    }
    response = requests.put(url, headers=headers, json={"metadata": metadata})
    if not response.ok:
        raise Exception("Failed to push metadata.")

@app.route('/welcome')
def generate_welcome_image():
    username = request.args.get('username')
    displayname = request.args.get('displayname')
    avatar = request.args.get('avatar')
    avatar_image = Image.open(requests.get(avatar, stream=True).raw).convert("RGBA").resize((160, 160))

    base_image = Image.open("assets/cards/welcome_card_base.png")
    font1 = ImageFont.truetype("assets/fonts/ggfont.woff", 50)
    font2 = ImageFont.truetype("assets/fonts/ggfont.woff", 30)

    # Cut the avatar in a circle & paste it on the welcome card
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

    # Paste the username & display name on the welcome card
    draw.text((320, 120), displayname, fill=(255, 255, 255), font=font1)
    draw.text((320, 180), username, fill="#dddddd", font=font2)

    img_byte_array = BytesIO()
    base_image.save(img_byte_array, format='PNG')
    img_byte_array.seek(0)

    return send_file(img_byte_array, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)
