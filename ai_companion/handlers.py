import logging
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from .prompts import (
    PromptManager,
    ServicePrompt,
    get_user_system_prompt,
    get_user_ai_mode,
    set_user_ai_mode,
    get_user_prompt,
    set_user_prompt,
    prompt_loader,
    get_prompt_with_history,
)
from .prompts import user_ai_modes, user_prompts
from .ai import generic_chat, download_and_encode_image
from .utils import extract_dan, print_usage, remove_offtopic, generate_link_preview, find_url, remove_links, extract_first_url, is_youtube_url, get_video_info_api, get_highest_rated_comments, extract_video_id
from .db import DBsqlite
from .config import DB_FILENAME, DEFAULT_AI_MODE

logger = logging.getLogger(__name__)

# Initialize database with schema if needed
import os
import sqlite3

def init_database():
    """Initialize database with schema if tables don't exist."""
    # Check if database exists and has tables
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        tables_exist = cursor.fetchone() is not None
        conn.close()

        if not tables_exist:
            # Database is empty, load schema
            schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.schema')
            with open(schema_path, 'r') as f:
                schema = f.read()
            return DBsqlite(DB_FILENAME, schema)
        else:
            # Database exists, just connect
            return DBsqlite(DB_FILENAME)
    except Exception as e:
        # If anything goes wrong, try to initialize with schema
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.schema')
        with open(schema_path, 'r') as f:
            schema = f.read()
        return DBsqlite(DB_FILENAME, schema)

db = init_database()
try:
    from .prompts import set_db_instance
    set_db_instance(db)
except Exception:
    logger.debug("Could not attach DB instance to prompts")

dan_prompt = [{"role": "system", "content": prompt_loader.get_prompt('dan') or 'You are a friendly assistant'}]

global_prompt = PromptManager(dan_prompt, 10)
service_prompt = ServicePrompt(dan_prompt, 1)

async def joined(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        if member.username == context.bot.username:
            usage = f"<span class=\"tg-spoiler\">{print_usage()}</span>"
            await context.bot.send_message(update.message.chat_id, f"Hey, your chat just have been updated with an awesome AI companion!\n{usage}", parse_mode=ParseMode.HTML)
            db.register_chat(update.message)

async def offtopic_command_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = message.from_user.id if message.from_user else None
    global_prompt.reset()
    if user_id:
        history_prompt = get_prompt_with_history(user_id, db)
        global_prompt.initial_prompt = history_prompt
        global_prompt._prompt = history_prompt.copy()
    base = remove_offtopic(message.text)
    offtopic_prompt = f"Let's change the topic.\n{base}"
    if user_id:
        db.register_user(message.from_user)
        db.add_history(user_id, "user", message.text)
    response = extract_dan(generic_chat(global_prompt, offtopic_prompt, user_id, ai_mode=get_user_ai_mode(user_id)))
    if user_id:
        db.add_history(user_id, "assistant", response)
    await message.reply_text(response, parse_mode=ParseMode.HTML)

async def mode_command_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    user_id = message.from_user.id
    args = context.args
    if not args:
        from .ai import openai_client
        current_mode = get_user_ai_mode(user_id)
        available_modes = "grok" + (", gpt" if openai_client else "")
        await message.reply_text(
            f"🤖 <b>Current AI Mode:</b> {current_mode.upper()}\n"
            f"📋 <b>Available modes:</b> {available_modes}",
            parse_mode=ParseMode.HTML
        )
        return
    new_mode = args[0].lower()
    if set_user_ai_mode(user_id, new_mode):
        await message.reply_text(f"✅ AI mode switched to <b>{new_mode}</b>!", parse_mode=ParseMode.HTML)
    else:
        await message.reply_text(f"❌ Invalid mode.", parse_mode=ParseMode.HTML)

async def prompt_command_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    user_id = message.from_user.id
    args = context.args
    if not args:
        current_prompt = get_user_prompt(user_id)
        available_prompts = ", ".join(prompt_loader.list_prompts())
        await message.reply_text(
            f"📝 <b>Current Prompt:</b> {current_prompt}\n"
            f"📋 <b>Available prompts:</b> {available_prompts}",
            parse_mode=ParseMode.HTML
        )
        return
    prompt_name = args[0].lower()
    if prompt_name == "reload":
        prompt_loader.reload_prompts()
        await message.reply_text("🔄 Prompts reloaded!", parse_mode=ParseMode.HTML)
        return
    if set_user_prompt(user_id, prompt_name):
        await message.reply_text(f"✅ System prompt switched to <b>{prompt_name}</b>!", parse_mode=ParseMode.HTML)
    else:
        await message.reply_text("❌ Invalid prompt name", parse_mode=ParseMode.HTML)

async def ignore_private(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id > 0:
        await update.message.reply_text('I only respond in group chats!')

async def mention_handler(update: Update, context: CallbackContext) -> None:
    """Handle messages that mention the bot."""
    message = update.message
    if not message.from_user:
        return

    user_id = message.from_user.id

    # Check if the bot is mentioned in the message
    bot_username = context.bot.username
    if f"@{bot_username}" in message.text or message.text.startswith(f"@{bot_username}"):
        # Remove the mention from the text
        text = message.text.replace(f"@{bot_username}", "").strip()
        if not text:
            text = "Hello!"

        try:
            global_prompt.reset()
            history_prompt = get_prompt_with_history(user_id, db)
            global_prompt.initial_prompt = history_prompt
            global_prompt._prompt = history_prompt.copy()

            db.register_user(message.from_user)
            db.add_history(user_id, "user", message.text)
            response = extract_dan(generic_chat(global_prompt, text, user_id, ai_mode=get_user_ai_mode(user_id)))
            db.add_history(user_id, "assistant", response)
            db.register_message(message, message)
            reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
            global_prompt.conversation.add_message(reply)
        except Exception as e:
            logger.error(f"Error in mention handler: {e}")
            await message.reply_text("Sorry, I'm experiencing technical difficulties. Please try again later.")

async def bot_reply_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return  # Skip if no user information

    user_id = message.from_user.id

    # If the reply is not directed at the bot, simply respond without greeting
    if not (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    ):
        try:
            global_prompt.reset()
            history_prompt = get_prompt_with_history(user_id, db)
            global_prompt.initial_prompt = history_prompt
            global_prompt._prompt = history_prompt.copy()
            db.register_user(message.from_user)
            db.add_history(user_id, "user", message.text)
            response = extract_dan(
                generic_chat(global_prompt, message.text, user_id, ai_mode=get_user_ai_mode(user_id))
            )
            db.add_history(user_id, "assistant", response)
            db.register_message(message, message)
            reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
            global_prompt.conversation.add_message(reply)
        except Exception as e:
            logger.error(f"Error in bot reply: {e}")
            await message.reply_text(
                "Sorry, I'm experiencing technical difficulties. Please try again later."
            )
        return

    # Determine if this user interacted before in this chat
    is_new_user = not db.check_user(message)

    if is_new_user:
        db.register_user(message.from_user)
        photo_data = None
        try:
            photos = await context.bot.get_user_profile_photos(user_id, limit=1)
            if photos.total_count:
                file = await context.bot.getFile(photos.photos[0][-1].file_id)
                photo_url = file.file_path
                if not photo_url.startswith("http"):
                    bot_token = context.bot.token
                    photo_url = f"https://api.telegram.org/file/bot{bot_token}/{file.file_path}"
                photo_data = download_and_encode_image(photo_url)
        except Exception:
            pass

        analysis_prompt = "Describe this user for future reference."
        if message.from_user.full_name:
            analysis_prompt += f" Name: {message.from_user.full_name}."
        user_summary = extract_dan(
            generic_chat(service_prompt, analysis_prompt, user_id, image_data=photo_data, ai_mode=get_user_ai_mode(user_id))
        )
        db.add_history(user_id, "system", user_summary, important=True)

        new_user_prompt = (
            "You're in Telegram chat, where a user has interacted with you for the first time, write a greeting message to him."
        )
        if message.from_user.first_name:
            new_user_prompt += f" First name: {message.from_user.first_name}."
        new_user_greeting = extract_dan(
            generic_chat(service_prompt, new_user_prompt, user_id, ai_mode=get_user_ai_mode(user_id))
        )
        usage = f"<span class=\"tg-spoiler\">{print_usage()}</span>"
        db.add_history(user_id, "assistant", new_user_greeting)
        await message.reply_text(f"{new_user_greeting}\n\n{usage}", parse_mode=ParseMode.HTML)

    # Respond to the actual message content
    try:
        global_prompt.reset()
        history_prompt = get_prompt_with_history(user_id, db)
        global_prompt.initial_prompt = history_prompt
        global_prompt._prompt = history_prompt.copy()

        db.register_user(message.from_user)
        db.add_history(user_id, "user", message.text)
        response = extract_dan(
            generic_chat(global_prompt, message.text, user_id, ai_mode=get_user_ai_mode(user_id))
        )

        db.add_history(user_id, "assistant", response)

        db.register_message(message, message)
        reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
        global_prompt.conversation.add_message(reply)
    except Exception as e:
        logger.error(f"Error in bot reply: {e}")
        await message.reply_text(
            "Sorry, I'm experiencing technical difficulties. Please try again later."
        )

async def photo_msg_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    user_id = message.from_user.id
    photo = await context.bot.getFile(message.photo[-1].file_id)
    photo_url = photo.file_path
    if not photo_url.startswith('http'):
        bot_token = context.bot.token
        photo_url = f"https://api.telegram.org/file/bot{bot_token}/{photo.file_path}"
    image_data = download_and_encode_image(photo_url)
    msg_caption = message.caption or ""
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
    history_prompt = get_prompt_with_history(user_id, db)
    global_prompt.initial_prompt = history_prompt
    global_prompt._prompt = history_prompt.copy()
    photo_prompt = "You're in a Telegram chat where a user sent you a photo."
    if msg_caption:
        photo_prompt += f" They included this caption: \"{msg_caption}\""
    if caption_urls:
        photo_prompt += f" They also shared these links: {caption_urls}"
    photo_prompt += " Please look at the image and respond with your thoughts about it."
    try:
        db.register_user(message.from_user)
        db.add_history(user_id, "user", message.caption or "<photo>")
        response = extract_dan(generic_chat(global_prompt, photo_prompt, user_id, image_data=image_data, ai_mode=get_user_ai_mode(user_id)))

        db.add_history(user_id, "assistant", response)
        db.register_message(message, message)

        reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
        global_prompt.conversation.add_message(reply)
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.reply_text("Sorry, I couldn't process your image right now. Please try again later.")

async def url_msg_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    text = message.text
    url = extract_first_url(text)
    body = text.replace(url, '')
    user_id = message.from_user.id
    global_prompt.reset()
    history_prompt = get_prompt_with_history(user_id, db)
    global_prompt.initial_prompt = history_prompt
    global_prompt._prompt = history_prompt.copy()
    if is_youtube_url(url):
        video_id = extract_video_id(url)
        yt_info = get_video_info_api(video_id)
        yt_prompt = (f"You're in Telegram chat where one user sent you a YouTube video titled: '{yt_info['title']}',"
                     f" Description: {yt_info['description']}, From channel: {yt_info['channelname']}."
                     f" User's note: {body} What do you think about it?")
        thumbnail_url = yt_info.get('thumbnail')
        db.register_user(message.from_user)
        db.add_history(user_id, "user", text)
        response = extract_dan(generic_chat(global_prompt, yt_prompt, user_id, image_url=thumbnail_url, ai_mode=get_user_ai_mode(user_id)))

        db.add_history(user_id, "assistant", response)
        db.register_message(message, message)

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
        db.register_user(message.from_user)
        db.add_history(user_id, "user", text)
        response = extract_dan(generic_chat(global_prompt, url_prompt, user_id, image_url=thumbnail_url, ai_mode=get_user_ai_mode(user_id)))

        db.add_history(user_id, "assistant", response)
        db.register_message(message, message)

        await message.reply_text(response, parse_mode=ParseMode.HTML)
