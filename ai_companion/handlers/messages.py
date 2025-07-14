import logging
from telegram import Update, helpers
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from ..prompts import (
    PromptManager,
    ServicePrompt,
    get_user_ai_mode,
    get_prompt_with_history,
)
from ..ai import generic_chat, download_and_encode_image
from ..utils import (
    extract_dan,
    print_usage,
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

NEGATIVE_REACTIONS = {"😡", "👎", "🤬", "🤮"}
WEIRD_REACTIONS = {"🤯", "🥴", "🤪", "😳"}

# provided by __init__.py
global_prompt: PromptManager | None = None
service_prompt: ServicePrompt | None = None
DB: DBsqlite | None = None

async def channel_message_handler(update: Update, context: CallbackContext) -> None:
    """Handle messages posted by channels in linked chats."""
    message = update.message
    if not message or not message.sender_chat:
        return
    channel_id = message.sender_chat.id
    try:
        global_prompt.reset()
        history_prompt = await get_prompt_with_history(channel_id, DB)
        global_prompt.initial_prompt = history_prompt
        global_prompt._prompt = history_prompt.copy()

        text = message.text or message.caption or ""
        response = extract_dan(
            generic_chat(global_prompt, text, channel_id, ai_mode=get_user_ai_mode(channel_id))
        )
        reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
        global_prompt.conversation.add_message(reply)
    except Exception as e:
        logger.error(f"Error handling channel message: {e}")

async def forward_message_handler(update: Update, context: CallbackContext) -> None:
    """Handle forwarded messages from other chats or channels."""
    message = update.message
    fo = getattr(message, "forward_origin", None)
    if not message or fo is None:
        return
    user_id = message.from_user.id if message.from_user else message.chat_id
    origin = "a chat"
    try:
        if fo.type == "chat":
            origin = fo.sender_chat.title or fo.sender_chat.username or origin
        elif fo.type == "channel":
            origin = fo.chat.title or fo.chat.username or origin
        elif fo.type in {"user", "hidden_user"}:
            if getattr(fo, "sender_user", None):
                origin = fo.sender_user.full_name
            elif getattr(fo, "sender_user_name", None):
                origin = fo.sender_user_name
    except Exception:
        pass

    text = message.text or message.caption or ""
    prompt = f"A message was forwarded from {origin}: {text}"
    try:
        global_prompt.reset()
        history_prompt = await get_prompt_with_history(user_id, DB)
        global_prompt.initial_prompt = history_prompt
        global_prompt._prompt = history_prompt.copy()
        response = extract_dan(generic_chat(global_prompt, prompt, user_id, ai_mode=get_user_ai_mode(user_id)))
        reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
        global_prompt.conversation.add_message(reply)
    except Exception as e:
        logger.error(f"Error handling forwarded message: {e}")

async def joined(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        if member.username == context.bot.username:
            usage = f"<span class=\"tg-spoiler\">{print_usage()}</span>"
            await context.bot.send_message(update.message.chat_id,
                                           f"Hey, your chat just have been updated with an awesome AI companion!\n{usage}",
                                           parse_mode=ParseMode.HTML)
            await DB.register_chat(update.message)

async def ignore_private(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id > 0:
        await update.message.reply_text('I only respond in group chats!')

async def mention_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    user_id = message.from_user.id
    bot_username = context.bot.username
    if f"@{bot_username}" in message.text or message.text.startswith(f"@{bot_username}"):
        text = message.text.replace(f"@{bot_username}", "").strip() or "Hello!"
        if message.reply_to_message:
            original = message.reply_to_message.text or message.reply_to_message.caption or ""
            if original:
                text = f"In reply to: \"{original}\"\n{text}"
        try:
            global_prompt.reset()
            history_prompt = await get_prompt_with_history(user_id, DB)
            global_prompt.initial_prompt = history_prompt
            global_prompt._prompt = history_prompt.copy()

            await DB.register_user(message.from_user)
            await DB.add_history(user_id, "user", message.text)
            response = extract_dan(generic_chat(global_prompt, text, user_id, ai_mode=get_user_ai_mode(user_id)))
            await DB.add_history(user_id, "assistant", response)
            await DB.register_message(message, message)
            reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
            global_prompt.conversation.add_message(reply)
        except Exception as e:
            logger.error(f"Error in mention handler: {e}")
            await message.reply_text("Sorry, I'm experiencing technical difficulties. Please try again later.")

async def bot_reply_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    user_id = message.from_user.id
    if not (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    ):
        return
    is_new_user = not await DB.check_user(message)
    if is_new_user:
        await DB.register_user(message.from_user)
        if message.reply_to_message and message.reply_to_message.text:
            await DB.add_history(user_id, "assistant", message.reply_to_message.text, important=True)
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
        await DB.add_history(user_id, "system", user_summary, important=True)
        new_user_prompt = (
            "You're in Telegram chat, where a user has interacted with you for the first time, write a greeting message to him."
        )
        if message.from_user.first_name:
            new_user_prompt += f" First name: {message.from_user.first_name}."
        new_user_greeting = extract_dan(
            generic_chat(service_prompt, new_user_prompt, user_id, ai_mode=get_user_ai_mode(user_id))
        )
        usage = f"<span class=\"tg-spoiler\">{print_usage()}</span>"
        await DB.add_history(user_id, "assistant", new_user_greeting)
        await message.reply_text(f"{new_user_greeting}\n\n{usage}", parse_mode=ParseMode.HTML)

    try:
        global_prompt.reset()
        history_prompt = await get_prompt_with_history(user_id, DB)
        global_prompt.initial_prompt = history_prompt
        global_prompt._prompt = history_prompt.copy()

        await DB.register_user(message.from_user)
        await DB.add_history(user_id, "user", message.text)
        response = extract_dan(
            generic_chat(global_prompt, message.text, user_id, ai_mode=get_user_ai_mode(user_id))
        )
        await DB.add_history(user_id, "assistant", response)
        await DB.register_message(message, message)
        reply = await message.reply_text(response, parse_mode=ParseMode.HTML)
        global_prompt.conversation.add_message(reply)
    except Exception as e:
        logger.error(f"Error in bot reply: {e}")
        await message.reply_text(
            "Sorry, I'm experiencing technical difficulties. Please try again later."
        )

async def reaction_handler(update: Update, context: CallbackContext) -> None:
    """Respond to negative or weird reactions to bot messages."""
    r = update.message_reaction
    if not r or not r.new_reaction:
        return
    try:
        if not await DB.is_bot_message(r.message_id):
            return
    except Exception as e:
        logger.error(f"Error checking message for reaction: {e}")
        return
    emoji = None
    for react in r.new_reaction:
        if getattr(react, "emoji", None) in NEGATIVE_REACTIONS | WEIRD_REACTIONS:
            emoji = react.emoji
            break
    if not emoji:
        return
    user = r.user or r.actor_chat
    user_id = user.id if user else r.chat.id
    prompt = f"A user reacted with {emoji} to my previous message. Reply briefly."
    try:
        global_prompt.reset()
        history_prompt = await get_prompt_with_history(user_id, DB)
        global_prompt.initial_prompt = history_prompt
        global_prompt._prompt = history_prompt.copy()
        response = extract_dan(generic_chat(global_prompt, prompt, user_id, ai_mode=get_user_ai_mode(user_id)))
        await context.bot.send_message(r.chat.id, response, reply_to_message_id=r.message_id, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error handling reaction: {e}")

