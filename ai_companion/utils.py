import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from linkpreview import Link, LinkPreview, LinkGrabber
from telegram.constants import ParseMode
from telegram import helpers

from .ai import download_and_encode_image, generic_chat
from .prompts import get_user_system_prompt, PromptManager, ServicePrompt, prompt_loader
from .config import YT_API_KEY, DEFAULT_AI_MODE

logger = logging.getLogger(__name__)

def extract_dan(string):
    dan_index = string.find("DAN:")
    return string[dan_index + len("DAN:"):] if dan_index != -1 else string

def extract_video_id(url):
    import urllib.parse as urlparse
    url_data = urlparse.urlparse(url)
    if url_data.netloc == "youtu.be":
        return url_data.path[1:]
    if url_data.netloc in ("www.youtube.com", "youtube.com"):
        if url_data.path == "/watch":
            query = urlparse.parse_qs(url_data.query)
            return query["v"][0]
        if url_data.path[:7] == "/embed/":
            return url_data.path.split("/")[2]
        if url_data.path[:3] == "/v/":
            return url_data.path.split("/")[2]
    return None

def remove_links(text):
    url_pattern = re.compile(r'http[s]?://\S+')
    return re.sub(url_pattern, '', text)

def find_url(text):
    url_pattern = re.compile(r'http[s]?://\S+')
    return re.findall(url_pattern, text)

def generate_link_preview(url):
    grabber = LinkGrabber(initial_timeout=20, maxsize=2048576, receive_timeout=10, chunk_size=1024)
    content, url = grabber.get_content(url)
    preview = LinkPreview(Link(url, content), parser="lxml")
    return {'title': preview.title, 'description': preview.description, 'thumbnail': preview.absolute_image}

def get_user_pp(context, user_id):
    return context.bot.get_user_profile_photos(user_id)

def print_usage():
    return ("<u>Usage</u>\n"
            "<i>The bot responds to links, replies and photos\n"
            "<u>with special handling of YouTube links</u> and default for other types of links.\n"
            "/offtopic\n/offtopic your_message lets the bot know that you want to discuss a different topic.\n"
            "/mode - switch between AI providers (Grok/GPT)\n"
            "/prompt - switch between system prompts (dan, friendly, professional, creative, sarcastic, concise)\n"
            "Just reply to any of the bot's messages to get an AI answer</i>")

def remove_offtopic(s):
    s = re.sub(r'/offtopic@\S+ ', '', s)
    s = re.sub(r'/offtopic ', '', s)
    return s

def extract_first_url(text):
    url_regex = r'http[s]?://\S+'
    m = re.search(url_regex, text)
    return m.group() if m else None

def is_youtube_url(url):
    return re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})', url) is not None

def get_video_info_api(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YT_API_KEY}&part=snippet"
    json_url = requests.get(url)
    data = json.loads(json_url.text)
    if data.get('items'):
        snippet = data['items'][0]['snippet']
        return {
            'title': snippet['title'],
            'description': remove_links(snippet.get('description','')),
            'thumbnail': snippet['thumbnails']['standard']['url'],
            'channelname': snippet['channelTitle']
        }
    return {}

def get_highest_rated_comments(video_id):
    url = f"https://www.googleapis.com/youtube/v3/commentThreads?key={YT_API_KEY}&textFormat=plainText&part=snippet&videoId={video_id}&order=relevance&maxResults=3"
    json_url = requests.get(url)
    data = json.loads(json_url.text)
    return [item['snippet']['topLevelComment']['snippet']['textOriginal'] for item in data.get('items', [])]
