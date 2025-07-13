import logging
from telegram import Update, helpers
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from ..prompts import (
    PromptManager,
    get_user_ai_mode,
    get_prompt_with_history,
)
from ..ai import generic_chat, download_and_encode_image
from ..utils import (
    extract_dan,
    find_url,
    remove_links,
    generate_link_preview,
    extract_first_url,
    is_youtube_url,
    get_video_info_api,
    get_highest_rated_comments,
    extract_video_id,
)
from ..db import DBsqlite

logger = logging.getLogger(__name__)

# provided by __init__.py
global_prompt: PromptManager | None = None
DB: DBsqlite | None = None

async def photo_msg_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    bot_username = context.bot.username
    if not (
        (message.caption and f"@{bot_username}" in message.caption)
        or (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == context.bot.id
        )
    ):
        return
    user_id = message.from_user.id
    photo = await context.bot.getFile(message.photo[-1].file_id)
    photo_url = photo.file_path
    if not photo_url.startswith('http'):
        bot_token = context.bot.token
        photo_url = f"https://api.telegram.org/file/bot{bot_token}/{photo.file_path}"
    image_data = download_and_encode_image(photo_url)
    msg_caption = message.caption or ""
    if f"@{bot_username}" in msg_caption:
        msg_caption = msg_caption.replace(f"@{bot_username}", "").strip()
    caption_urls = ''
    if msg_caption:
        caption_url_list = find_url(msg_caption)
        if caption_url_list:
            msg_caption = remove_links(msg_caption)
            for url in caption_url_list:
                try:
                    info = generate_link_preview(url)
                    caption_urls += f" Link: \"{info['title']}\" - {info['description']}"
                except Exception:
                    pass
    global_prompt.reset()
    history_prompt = await get_prompt_with_history(user_id, DB)
    global_prompt.initial_prompt = history_prompt
    global_prompt._prompt = history_prompt.copy()
    photo_prompt = "You're in a Telegram chat where a user sent you a photo."
    if msg_caption:
        photo_prompt += f" They included this caption: \"{msg_caption}\""
    if caption_urls:
        photo_prompt += f" They also shared these links: {caption_urls}"
    photo_prompt += " Please look at the image and respond with your thoughts about it."
    try:
        await DB.register_user(message.from_user)
        await DB.add_history(user_id, "user", message.caption or "<photo>")
        response = extract_dan(generic_chat(global_prompt, photo_prompt, user_id, image_data=image_data, ai_mode=get_user_ai_mode(user_id)))
        await DB.add_history(user_id, "assistant", response)
        await DB.register_message(message, message)
        reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
        global_prompt.conversation.add_message(reply)
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.reply_text("Sorry, I couldn't process your image right now. Please try again later.")

async def url_msg_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    bot_username = context.bot.username
    if not (
        f"@{bot_username}" in message.text
        or (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == context.bot.id
        )
    ):
        return
    text = message.text
    if f"@{bot_username}" in text:
        text = text.replace(f"@{bot_username}", "").strip()
    url = extract_first_url(text)
    body = text.replace(url, '')
    user_id = message.from_user.id
    global_prompt.reset()
    history_prompt = await get_prompt_with_history(user_id, DB)
    global_prompt.initial_prompt = history_prompt
    global_prompt._prompt = history_prompt.copy()
    if is_youtube_url(url):
        video_id = extract_video_id(url)
        yt_info = get_video_info_api(video_id)
        yt_prompt = (f"You're in Telegram chat where one user sent you a YouTube video titled: '{yt_info['title']}',"
                     f" Description: {yt_info['description']}, From channel: {yt_info['channelname']}."
                     f" User's note: {body} What do you think about it?")
        thumbnail_url = yt_info.get('thumbnail')
        await DB.register_user(message.from_user)
        await DB.add_history(user_id, "user", text)
        response = extract_dan(generic_chat(global_prompt, yt_prompt, user_id, image_url=thumbnail_url, ai_mode=get_user_ai_mode(user_id)))
        await DB.add_history(user_id, "assistant", response)
        await DB.register_message(message, message)
        await message.reply_text(response, parse_mode=ParseMode.HTML)
        comments_list = get_highest_rated_comments(video_id)
        comments = "\n".join([f"{i+1}: \"{c}\"" for i, c in enumerate(comments_list)])
        escaped = helpers.escape_markdown(comments)
        await message.reply_text(escaped)
    else:
        info = generate_link_preview(url)
        url_prompt = (f"You're in Telegram chat where one user shared a website titled: '{info['title']}',"
                      f" Description: {info['description']}. User's note: {body} What do you think about it?")
        thumbnail_url = info.get('thumbnail')
        await DB.register_user(message.from_user)
        await DB.add_history(user_id, "user", text)
        response = extract_dan(generic_chat(global_prompt, url_prompt, user_id, image_url=thumbnail_url, ai_mode=get_user_ai_mode(user_id)))
        await DB.add_history(user_id, "assistant", response)
        await DB.register_message(message, message)
        await message.reply_text(response, parse_mode=ParseMode.HTML)

