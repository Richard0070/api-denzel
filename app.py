from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import requests
from flask import Flask, send_file, request, render_template, jsonify, redirect, make_response
import os
import json
import secrets 
import time

app = Flask(__name__)
app.secret_key = os.getenv('COOKIE_SECRET')

@app.route("/")
def index():
    return render_template('index.html')

# Load environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI')

# In-memory store for Discord tokens
store = {}

@app.route('/linked-role')
def linked_role():
    state = secrets.token_urlsafe(16)
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&state={state}"
        f"&scope=role_connections.write identify"
        f"&prompt=consent"
    )

    resp = make_response(redirect(url))
    resp.set_cookie('clientState', state, max_age=300, secure=True, httponly=True)
    return resp

@app.route('/discord-oauth-callback')
def discord_oauth_callback():
    code = request.args.get('code')
    discord_state = request.args.get('state')
    client_state = request.cookies.get('clientState')

    if client_state != discord_state:
        return 'State verification failed.', 403

    tokens = get_oauth_tokens(code)

    me_data = get_user_data(tokens['access_token'])
    user_id = me_data['user']['id']

    store_discord_tokens(user_id, {
        'access_token': tokens['access_token'],
        'refresh_token': tokens['refresh_token'],
        'expires_in': tokens['expires_in']
    })
    update_metadata(user_id)
    return render_template('index.html')

def get_oauth_tokens(code):
    url = 'https://discord.com/api/v10/oauth2/token'
    body = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
    }
    response = requests.post(url, data=body)
    response.raise_for_status() 
    return response.json()

def get_user_data(access_token):
    url = 'https://discord.com/api/v10/oauth2/@me'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def store_discord_tokens(user_id, tokens):
    store[f'discord-{user_id}'] = tokens

def get_discord_tokens(user_id):
    return store.get(f'discord-{user_id}')
    
def get_access_token(user_id, tokens):
    if tokens['expires_in'] < time.time():
        url = 'https://discord.com/api/v10/oauth2/token'
        body = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': tokens['refresh_token'],
        }
        response = requests.post(url, data=body)
        response.raise_for_status()
        new_tokens = response.json()
        new_tokens['expires_in'] = time.time() + new_tokens['expires_in']
        store_discord_tokens(user_id, new_tokens)
        return new_tokens['access_token']
    return tokens['access_token']
    
def update_metadata(user_id):
    tokens = get_discord_tokens(user_id)
    if not tokens:
        return

    metadata = {
        'is_heisenberg': 1,      
        'is_sexy': 1,            
        'is_troller': 1,    
        'is_bjp': 1
    }

    push_metadata(user_id, tokens, metadata)

def push_metadata(user_id, tokens, metadata):
    url = f"https://discord.com/api/v10/users/@me/applications/{DISCORD_CLIENT_ID}/role-connection"
    access_token = get_access_token(user_id, tokens)
    
    body = {
        'platform_name': 'Melody Realm',
        'metadata': metadata,
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    response = requests.put(url, headers=headers, json=body)
    response.raise_for_status()
    
@app.route('/welcome')
def generate_welcome_image():
    username = request.args.get('username')
    displayname = request.args.get('displayname')
    avatar = request.args.get('avatar')

    if not all([username, displayname, avatar]):
        return 'Missing user information.', 400

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
