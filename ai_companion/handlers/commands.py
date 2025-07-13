import logging
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from ..prompts import (
    get_user_ai_mode,
    get_user_prompt,
    prompt_loader,
    PromptManager,
    ServicePrompt,
    get_prompt_with_history,
    set_user_ai_mode,
    set_user_prompt,
)
from ..ai import generic_chat
from ..utils import extract_dan, print_usage, remove_offtopic
from ..db import DBsqlite

logger = logging.getLogger(__name__)

# global instances will be provided by __init__.py
global_prompt: PromptManager | None = None
service_prompt: ServicePrompt | None = None
DB: DBsqlite | None = None

async def offtopic_command_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    user_id = message.from_user.id if message.from_user else None
    global_prompt.reset()
    if user_id:
        history_prompt = await get_prompt_with_history(user_id, DB)
        global_prompt.initial_prompt = history_prompt
        global_prompt._prompt = history_prompt.copy()
    base = remove_offtopic(message.text)
    offtopic_prompt = f"Let's change the topic.\n{base}"
    if user_id:
        await DB.register_user(message.from_user)
        await DB.add_history(user_id, "user", message.text)
    response = extract_dan(generic_chat(global_prompt, offtopic_prompt, user_id, ai_mode=get_user_ai_mode(user_id)))
    if user_id:
        await DB.add_history(user_id, "assistant", response)
    await message.reply_text(response, parse_mode=ParseMode.HTML)

async def mode_command_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    user_id = message.from_user.id
    args = context.args
    if not args:
        from ..ai import openai_client
        current_mode = get_user_ai_mode(user_id)
        available_modes = "grok" + (", gpt" if openai_client else "")
        await message.reply_text(
            f"🤖 <b>Current AI Mode:</b> {current_mode.upper()}\n"
            f"📋 <b>Available modes:</b> {available_modes}",
            parse_mode=ParseMode.HTML
        )
        return
    new_mode = args[0].lower()
    if await set_user_ai_mode(user_id, new_mode):
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
    if await set_user_prompt(user_id, prompt_name):
        await message.reply_text(f"✅ System prompt switched to <b>{prompt_name}</b>!", parse_mode=ParseMode.HTML)
    else:
        await message.reply_text("❌ Invalid prompt name", parse_mode=ParseMode.HTML)

async def clear_history_command_handler(update: Update, context: CallbackContext) -> None:
    message = update.message
    if not message.from_user:
        return
    user_id = message.from_user.id
    await DB.clear_history(user_id)
    await message.reply_text("🧹 Conversation history cleared!", parse_mode=ParseMode.HTML)
