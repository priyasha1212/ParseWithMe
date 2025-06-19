from flask import Flask, request, jsonify, render_template, session, send_file
from fpdf import FPDF
from reddit_scraper import fetch_reddit_posts
from googleapiclient.discovery import build
import webbrowser
from datetime import datetime
import random
import io
import requests
import json
import logging
from flask_cors import CORS

# Telegram API
from telethon import TelegramClient
import asyncio
import os

# Predefined credentials
DEFAULT_USERNAME = "user123"
DEFAULT_PASSWORD = "yash"   
YOUTUBE_API_KEY = 'AIzaSyBPr4RJFb6LIa5LlgpO1SFpoZ_DgZSTyMk'

# Telegram API credentials (replace with your actual credentials)
API_ID = '25817557'      # <-- Replace with your Telegram api_id (int)
API_HASH = '7d5b0d255fff646e6dea9e2008d1c1c3'  # <-- Replace with your Telegram api_hash (str)
TELEGRAM_SESSION = 'neurofeed_telegram'  # session file name

# Global variables
saved_data = {}
search_history = []

# Add global variables for shuffle history
shuffle_history = []
shuffle_index = -1

# Add a dictionary to store search results by timestamp for history navigation
search_results_by_time = {}

# Add this global variable at the top (after other globals)
current_username = DEFAULT_USERNAME

USER_DATA_DIR = 'user_data'
os.makedirs(USER_DATA_DIR, exist_ok=True)

def sanitize_text(text):
    return text.encode('latin-1', 'ignore').decode('latin-1')

def fetch_youtube_videos(keyword, max_results=5):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=keyword,
            part='snippet',
            type='video',
            maxResults=max_results
        )
        response = request.execute()
        return [{
            'title': item['snippet']['title'],
            'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            'channel': item['snippet']['channelTitle']
        } for item in response['items']]
    except Exception as e:
        logging.error(f"Failed to fetch YouTube videos: {e}")
        return []

# --- Telegram fetch: search public channels/groups only ---
def fetch_telegram_messages(keyword, limit=5):
    try:
        async def fetch():
            client = TelegramClient(TELEGRAM_SESSION, int(API_ID), API_HASH)
            await client.start()
            if not await client.is_user_authorized():
                logging.error("Telegram session is not authorized. Please log in interactively at least once using Telethon.")
                await client.disconnect()
                return []
            messages = []
            async for dialog in client.iter_dialogs():
                # Only consider public channels and supergroups
                if dialog.is_channel and (dialog.broadcast or dialog.megagroup):
                    async for message in client.iter_messages(dialog.id, search=keyword, limit=limit):
                        if message.message:
                            messages.append({
                                'chat': dialog.name,
                                'text': message.message,
                                'date': message.date.strftime("%Y-%m-%d %H:%M:%S")
                            })
            await client.disconnect()
            return messages[:limit]
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(fetch())
        loop.close()
        if not messages:
            logging.info(f"No Telegram public channel/group messages found for keyword: {keyword}")
        return messages
    except Exception as e:
        logging.error(f"Failed to fetch Telegram messages: {e}")
        return []

def fetch_instagram_posts(keyword, max_results=5):
    try:
        with open('instagram_posts.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        key = None
        for k in data:
            if k.lower() in keyword.lower():
                key = k
                break
        if not key:
            return []
        posts = data[key]
        results = []
        for post in posts[:max_results]:
            # Only keep username, url, and channel/page url if available
            results.append({
                'url': post['url'],
                'owner_username': post['username'],
                'channel_url': post.get('channel_url', ''),
            })
        return results
    except Exception as e:
        logging.error(f"Failed to fetch Instagram posts: {e}")
        return []

def fetch_facebook_posts(keyword, max_results=5):
    try:
        with open('facebook_posts.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        key = None
        # Try exact match, then with _facebook, then with space+facebook
        for k in data:
            if k.lower() == keyword.lower():
                key = k
                break
        if not key:
            for k in data:
                if k.lower() == f"{keyword.lower()}_facebook":
                    key = k
                    break
        if not key:
            for k in data:
                if k.lower() == f"{keyword.lower()} facebook":
                    key = k
                    break
        # Also try if keyword is contained in the key (for partial matches)
        if not key:
            for k in data:
                if keyword.lower() in k.lower():
                    key = k
                    break
        if not key:
            return []
        posts = data[key]
        results = []
        for post in posts[:max_results]:
            # Only keep username, url, and channel/page url if available
            results.append({
                'url': post['url'],
                'username': post['username'],
                'page_url': post.get('page_url', ''),
            })
        return results
    except Exception as e:
        logging.error(f"Failed to fetch Facebook posts: {e}")
        return []

def start_scraping(keyword, num_results):
    global saved_data, shuffle_history, shuffle_index, search_results_by_time, current_username
    # Always save the username with the search history
    username = current_username
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    search_history.append(f"{keyword} — {timestamp} — {username}")

    reddit_posts = fetch_reddit_posts(keyword)
    telegram_messages = fetch_telegram_messages(keyword, limit=num_results)
    youtube_videos = fetch_youtube_videos(keyword, max_results=num_results)
    instagram_posts = fetch_instagram_posts(keyword, max_results=num_results)
    facebook_videos = fetch_facebook_posts(keyword, max_results=num_results)

    reddit_posts = reddit_posts[:num_results]

    if not reddit_posts and not youtube_videos and not telegram_messages and not instagram_posts and not facebook_videos:
        return {"message": "No results found. Try searching for 'pahalgamattack' or 'planecrash'."}

    saved_data = {
        'reddit_posts': reddit_posts,
        'telegram_messages': telegram_messages,
        'youtube_videos': youtube_videos,
        'instagram_posts': instagram_posts,
        'facebook_videos': facebook_videos
    }

    # Save the results and shuffle history in the history dictionary
    search_results_by_time[timestamp] = {
        'keyword': keyword,
        'username': username,
        'reddit_posts': reddit_posts.copy(),
        'telegram_messages': telegram_messages.copy(),
        'youtube_videos': youtube_videos.copy(),
        'instagram_posts': instagram_posts.copy(),
        'facebook_videos': facebook_videos.copy(),
        'shuffle_history': [
            {
                'reddit_posts': reddit_posts.copy(),
                'telegram_messages': telegram_messages.copy(),
                'youtube_videos': youtube_videos.copy(),
                'instagram_posts': instagram_posts.copy(),
                'facebook_videos': facebook_videos.copy()
            }
        ],
        'shuffle_index': 0
    }

    # Reset shuffle history and add the initial result set
    shuffle_history = [{
        'reddit_posts': reddit_posts.copy(),
        'telegram_messages': telegram_messages.copy(),
        'youtube_videos': youtube_videos.copy(),
        'instagram_posts': instagram_posts.copy(),
        'facebook_videos': facebook_videos.copy()
    }]
    shuffle_index = 0

    # Return the results as JSON
    return {
        'reddit_posts': reddit_posts,
        'telegram_messages': telegram_messages,
        'youtube_videos': youtube_videos,
        'instagram_posts': instagram_posts,
        'facebook_videos': facebook_videos
    }


def shuffle_results():
    global shuffle_history, shuffle_index, search_results_by_time
    if not shuffle_history:
        return
    # Shuffle within each section, keep headings/order fixed
    current = shuffle_history[shuffle_index]
    new_results = {
        'reddit_posts': current['reddit_posts'].copy(),
        'telegram_messages': current['telegram_messages'].copy(),
        'youtube_videos': current['youtube_videos'].copy(),
        'instagram_posts': current['instagram_posts'].copy(),
        'facebook_videos': current['facebook_videos'].copy()
    }
    random.shuffle(new_results['reddit_posts'])
    random.shuffle(new_results['telegram_messages'])
    random.shuffle(new_results['youtube_videos'])
    random.shuffle(new_results['instagram_posts'])
    random.shuffle(new_results['facebook_videos'])
    shuffle_history = shuffle_history[:shuffle_index+1]  # Discard any 'forward' history
    shuffle_history.append(new_results)
    shuffle_index += 1
    # Also update the current search_results_by_time entry if it matches the current keyword/timestamp
    if search_history:
        last_history = search_history[-1]
        if '—' in last_history:
            _, last_timestamp = last_history.split('—', 1)
            last_timestamp = last_timestamp.strip()
            if last_timestamp in search_results_by_time:
                search_results_by_time[last_timestamp]['shuffle_history'] = shuffle_history.copy()
                search_results_by_time[last_timestamp]['shuffle_index'] = shuffle_index


def go_back():
    global shuffle_index
    if shuffle_index > 0:
        shuffle_index -= 1


def go_forward():
    global shuffle_index
    if shuffle_index < len(shuffle_history) - 1:
        shuffle_index += 1


def save_report():
    if not saved_data:
        logging.warning("No data to save.")
        return

    reddit_posts = saved_data.get('reddit_posts', [])
    telegram_messages = saved_data.get('telegram_messages', [])
    youtube_videos = saved_data.get('youtube_videos', [])
    instagram_posts = saved_data.get('instagram_posts', [])
    facebook_videos = saved_data.get('facebook_videos', [])

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=16, style='B')
        pdf.cell(200, 10, sanitize_text(f"PARSEwithME Report - 'report'"), ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", size=12)

        if reddit_posts:
            pdf.set_font("Arial", size=14, style='B')
            pdf.cell(200, 10, "Reddit Posts:", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            for post in reddit_posts:
                pdf.multi_cell(0, 10, f"Title: {sanitize_text(post['title'])}")
                pdf.multi_cell(0, 10, f"URL: {sanitize_text(post['url'])}")
                pdf.ln(3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

        if telegram_messages:
            pdf.set_font("Arial", size=14, style='B')
            pdf.cell(200, 10, "Telegram Messages:", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            for msg in telegram_messages:
                pdf.multi_cell(0, 10, f"Chat: {sanitize_text(msg['chat'])}")
                pdf.multi_cell(0, 10, f"Message: {sanitize_text(msg['text'])}")
                pdf.multi_cell(0, 10, f"Date: {sanitize_text(msg['date'])}")
                pdf.ln(3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

        if youtube_videos:
            pdf.set_font("Arial", size=14, style='B')
            pdf.cell(200, 10, "YouTube Videos:", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            for video in youtube_videos:
                pdf.multi_cell(0, 10, f"Title: {sanitize_text(video['title'])}")
                pdf.multi_cell(0, 10, f"Channel: {sanitize_text(video['channel'])}")
                pdf.multi_cell(0, 10, f"URL: {sanitize_text(video['url'])}")
                pdf.ln(3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

        if instagram_posts:
            pdf.set_font("Arial", size=14, style='B')
            pdf.cell(200, 10, "Instagram Posts:", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            for post in instagram_posts:
                pdf.multi_cell(0, 10, f"Username: @{sanitize_text(post['owner_username'])}")
                pdf.multi_cell(0, 10, f"Post URL: {sanitize_text(post['url'])}")
                if post.get('channel_url'):
                    pdf.multi_cell(0, 10, f"Channel URL: {sanitize_text(post['channel_url'])}")
                pdf.ln(3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

        if facebook_videos:
            pdf.set_font("Arial", size=14, style='B')
            pdf.cell(200, 10, "Facebook Videos:", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            for video in facebook_videos:
                pdf.multi_cell(0, 10, f"Username: {video['username']}")
                pdf.multi_cell(0, 10, f"Post URL: {video['url']}")
                if video.get('page_url'):
                    pdf.multi_cell(0, 10, f"Page URL: {video['page_url']}")
                pdf.ln(3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

        filename = f"parsewithme_report_report.pdf"
        pdf.output(filename)
        logging.info(f"Report saved as {filename}")
    except Exception as e:
        logging.error(f"Failed to save report: {e}")

# --- Flask API for frontend integration ---
app = Flask(__name__, template_folder="templates")
app.secret_key = 'parsewithme_secret_key'  # For session management
CORS(app)

# In-memory user store (for demo)
users = {DEFAULT_USERNAME: DEFAULT_PASSWORD}

def get_user_history_path(username):
    return os.path.join(USER_DATA_DIR, f"{username}_history.json")

def load_user_history(username):
    path = get_user_history_path(username)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_user_history(username, history):
    path = get_user_history_path(username)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(history, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json()
    keyword = data.get('keyword', '')
    num_results = int(data.get('num_results', 5))
    # Use the scraping logic (no GUI)
    reddit_posts = fetch_reddit_posts(keyword)
    telegram_messages = fetch_telegram_messages(keyword, limit=num_results)
    youtube_videos = fetch_youtube_videos(keyword, max_results=num_results)
    instagram_posts = fetch_instagram_posts(keyword, max_results=num_results)
    facebook_videos = fetch_facebook_posts(keyword, max_results=num_results)
    logging.info(f"Telegram results for '{keyword}': {telegram_messages}")
    return jsonify({
        'reddit_posts': reddit_posts[:num_results],
        'telegram_messages': telegram_messages,
        'youtube_videos': youtube_videos,
        'instagram_posts': instagram_posts,
        'facebook_videos': facebook_videos
    })

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if username in users and users[username] == password:
        session['username'] = username
        return jsonify({'success': True, 'username': username})
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    if username in users:
        return jsonify({'success': False, 'error': 'User exists'}), 409
    users[username] = password
    return jsonify({'success': True, 'username': username})

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'success': True})

@app.route('/history', methods=['GET'])
def get_history():
    username = session.get('username', DEFAULT_USERNAME)
    return jsonify({'history': load_user_history(username)})

@app.route('/history', methods=['POST'])
def add_history():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json()
    keyword = data.get('keyword')
    timestamp = data.get('timestamp')
    username = session['username']
    entry = f"{keyword} — {timestamp} — {username}"
    history = load_user_history(username)
    history.append(entry)
    save_user_history(username, history)
    return jsonify({'success': True})

@app.route('/history/clear', methods=['POST'])
def clear_history():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    username = session['username']
    save_user_history(username, [])
    return jsonify({'success': True})

@app.route('/save', methods=['POST'])
def save_pad():
    data = request.get_json()
    username = session.get('username', DEFAULT_USERNAME)
    pad = data.get('pad')
    if not pad:
        return jsonify({'success': False, 'error': 'No pad data'}), 400
    if 'pads' not in saved_data:
        saved_data['pads'] = {}
    if username not in saved_data['pads']:
        saved_data['pads'][username] = []
    saved_data['pads'][username].append(pad)
    return jsonify({'success': True})

@app.route('/pads', methods=['GET'])
def get_pads():
    username = session.get('username', DEFAULT_USERNAME)
    pads = saved_data.get('pads', {}).get(username, [])
    return jsonify({'pads': pads})

@app.route('/reset_password', methods=['POST'])
def reset_password():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json()
    password = data.get('password')
    if not password:
        return jsonify({'success': False, 'error': 'Missing password'}), 400
    users[session['username']] = password
    return jsonify({'success': True})

@app.route('/report', methods=['POST'])
def report():
    # Accept results from frontend and generate PDF from them
    from fpdf import FPDF
    import tempfile
    data = request.get_json()
    # Expecting keys: reddit_posts, telegram_messages, youtube_videos, instagram_posts, facebook_videos
    reddit_posts = data.get('reddit_posts', [])
    telegram_messages = data.get('telegram_messages', [])
    youtube_videos = data.get('youtube_videos', [])
    instagram_posts = data.get('instagram_posts', [])
    facebook_videos = data.get('facebook_videos', [])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16, style='B')
    pdf.cell(200, 10, "PARSEwithME Report", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)

    if reddit_posts:
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(200, 10, "Reddit Posts:", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        for post in reddit_posts:
            pdf.multi_cell(0, 10, f"Title: {sanitize_text(post.get('title',''))}")
            pdf.multi_cell(0, 10, f"URL: {sanitize_text(post.get('url',''))}")
            pdf.ln(3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

    if telegram_messages:
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(200, 10, "Telegram Messages:", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        for msg in telegram_messages:
            pdf.multi_cell(0, 10, f"Chat: {sanitize_text(msg.get('chat',''))}")
            pdf.multi_cell(0, 10, f"Message: {sanitize_text(msg.get('text',''))}")
            pdf.multi_cell(0, 10, f"Date: {sanitize_text(msg.get('date',''))}")
            pdf.ln(3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

    if youtube_videos:
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(200, 10, "YouTube Videos:", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        for video in youtube_videos:
            pdf.multi_cell(0, 10, f"Title: {sanitize_text(video.get('title',''))}")
            pdf.multi_cell(0, 10, f"Channel: {sanitize_text(video.get('channel',''))}")
            pdf.multi_cell(0, 10, f"URL: {sanitize_text(video.get('url',''))}")
            pdf.ln(3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

    if instagram_posts:
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(200, 10, "Instagram Posts:", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        for post in instagram_posts:
            pdf.multi_cell(0, 10, f"Username: @{sanitize_text(post.get('owner_username',''))}")
            pdf.multi_cell(0, 10, f"Post URL: {sanitize_text(post.get('url',''))}")
            if post.get('channel_url'):
                pdf.multi_cell(0, 10, f"Channel URL: {sanitize_text(post.get('channel_url',''))}")
            pdf.ln(3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

    if facebook_videos:
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(200, 10, "Facebook Videos:", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        for video in facebook_videos:
            pdf.multi_cell(0, 10, f"Username: {sanitize_text(video.get('username',''))}")
            pdf.multi_cell(0, 10, f"Post URL: {sanitize_text(video.get('url',''))}")
            if video.get('page_url'):
                pdf.multi_cell(0, 10, f"Page URL: {sanitize_text(video.get('page_url',''))}")
            pdf.ln(3)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf.output(tmp.name)
    tmp.close()
    return send_file(tmp.name, as_attachment=True, download_name='parsewithme_report.pdf', mimetype='application/pdf')

# Store PDFs per user (demo: just list generated reports)
@app.route('/pdfs', methods=['GET'])
def list_pdfs():
    # For demo, just return a static list
    return jsonify({'pdfs': ['parsewithme_report.pdf']})

@app.route('/pdfs/<filename>', methods=['GET'])
def get_pdf(filename):
    # For demo, always return the last generated report
    import os
    path = os.path.join(os.getcwd(), filename)
    if not os.path.exists(path):
        return '', 404
    return send_file(path, as_attachment=True)

@app.route('/pdfs/delete', methods=['POST'])
def delete_pdfs():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401
    data = request.get_json()
    files = data.get('files', [])
    username = session['username']
    deleted = []
    for fname in files:
        # Only allow deleting from user_data dir for this user
        user_pdf_path = os.path.join(USER_DATA_DIR, fname)
        if os.path.exists(user_pdf_path):
            try:
                os.remove(user_pdf_path)
                deleted.append(fname)
            except Exception as e:
                continue
    # Optionally update user's PDF list if you keep one
    return jsonify({'success': True, 'deleted': deleted})

if __name__ == '__main__':
    import threading
    import webbrowser
    def open_browser():
        webbrowser.open('http://localhost:5000')
    threading.Timer(1.0, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
