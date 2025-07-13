"""Handler package providing Telegram bot callbacks."""

import asyncio
import logging
import os
import sqlite3

from ..db import DBsqlite
from ..prompts import (
    PromptManager,
    ServicePrompt,
    prompt_loader,
    set_db_instance,
    get_user_ai_mode,
    set_user_ai_mode,
    get_user_prompt,
    set_user_prompt,
)
from ..ai import generic_chat, download_and_encode_image
from ..utils import generate_link_preview, extract_video_id, get_video_info_api, get_highest_rated_comments

from ..config import DB_FILENAME

logger = logging.getLogger(__name__)

# database initialization

def init_database() -> DBsqlite:
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        tables_exist = cursor.fetchone() is not None
        conn.close()
        if not tables_exist:
            schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'db.schema')
            with open(schema_path, 'r') as f:
                schema = f.read()
            return DBsqlite(DB_FILENAME, schema)
        return DBsqlite(DB_FILENAME)
    except Exception:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'db.schema')
        with open(schema_path, 'r') as f:
            schema = f.read()
        return DBsqlite(DB_FILENAME, schema)

DB = init_database()
try:
    asyncio.run(set_db_instance(DB))
except Exception:
    logger.debug("Could not attach DB instance to prompts")

# global prompts

dan_prompt = [{"role": "system", "content": prompt_loader.get_prompt('dan') or 'You are a friendly assistant'}]

global_prompt = PromptManager(dan_prompt, 10)
service_prompt = ServicePrompt(dan_prompt, 1)

# import sub-modules and expose their handlers
from .commands import (
    offtopic_command_handler,
    mode_command_handler,
    prompt_command_handler,
    clear_history_command_handler,
    global_prompt as _g1, service_prompt as _s1, DB as _db1,
)
from .messages import (
    joined,
    ignore_private,
    mention_handler,
    bot_reply_handler,
    global_prompt as _g2, service_prompt as _s2, DB as _db2,
)
from .media import (
    photo_msg_handler,
    url_msg_handler,
    global_prompt as _g3, DB as _db3,
)

# assign shared instances to modules
for mod in [__import__(__name__ + '.commands', fromlist=['a']), __import__(__name__ + '.messages', fromlist=['a']), __import__(__name__ + '.media', fromlist=['a'])]:
    mod.global_prompt = global_prompt
    if hasattr(mod, 'service_prompt'):
        mod.service_prompt = service_prompt
    mod.DB = DB

__all__ = [
    'offtopic_command_handler',
    'mode_command_handler',
    'prompt_command_handler',
    'clear_history_command_handler',
    'joined',
    'ignore_private',
    'mention_handler',
    'bot_reply_handler',
    'photo_msg_handler',
    'url_msg_handler',
    'generic_chat',
    'download_and_encode_image',
    'get_video_info_api',
    'get_highest_rated_comments',
    'extract_video_id',
    'generate_link_preview',
    'get_user_ai_mode',
    'set_user_ai_mode',
    'get_user_prompt',
    'set_user_prompt',
]
