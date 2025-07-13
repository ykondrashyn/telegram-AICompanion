import os
import uuid
import logging
from .config import DEFAULT_AI_MODE, DB_FILENAME
from .db import DBsqlite
import asyncio
from .ai import openai_client

logger = logging.getLogger(__name__)

class PromptLoader:
    def __init__(self, prompts_dir="prompts"):
        self.prompts_dir = prompts_dir
        self.prompts_cache = {}
        self.load_all_prompts()

    def load_all_prompts(self):
        try:
            if not os.path.exists(self.prompts_dir):
                logger.warning(f"Prompts directory {self.prompts_dir} not found")
                return
            for filename in os.listdir(self.prompts_dir):
                if filename.endswith('.txt'):
                    prompt_name = filename[:-4]
                    with open(os.path.join(self.prompts_dir, filename), 'r', encoding='utf-8') as f:
                        self.prompts_cache[prompt_name] = f.read().strip()
                    logger.info(f"Loaded prompt: {prompt_name}")
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")

    def get_prompt(self, name):
        return self.prompts_cache.get(name)

    def list_prompts(self):
        return list(self.prompts_cache.keys())

    def reload_prompts(self):
        self.prompts_cache.clear()
        self.load_all_prompts()

prompt_loader = PromptLoader()

# Use a concise default prompt to keep replies short and focused
DEFAULT_PROMPT = "concise"
user_prompts = {}
user_ai_modes = {}

# Optional database instance for persisting preferences
db_instance: DBsqlite | None = None

async def set_db_instance(db: DBsqlite):
    """Attach a DB instance and load stored preferences."""
    global db_instance
    db_instance = db
    await load_preferences_from_db()

async def load_preferences_from_db():
    if not db_instance:
        return
    try:
        prefs = await db_instance.get_all_preferences()
        for uid, pref in prefs.items():
            if pref.get("ai_mode"):
                user_ai_modes[uid] = pref["ai_mode"]
            if pref.get("system_prompt"):
                user_prompts[uid] = pref["system_prompt"]
    except Exception as exc:
        logger.error("Failed loading preferences: %s", exc)

class Conversation:
    def __init__(self):
        self.id = uuid.uuid4()
        self.messages = {}

    def add_message(self, message_id:int):
        self.messages[message_id] = True

    def reset(self):
        self.id = uuid.uuid4()
        self.messages = {}

    def check_message(self, message_id):
        return message_id in self.messages

class PromptManager:
    def __init__(self, initial_prompt:list, reset_after_calls:int):
        self.conversation = Conversation()
        self._prompt = initial_prompt.copy()
        self.initial_prompt = initial_prompt
        self.reset_after_calls = reset_after_calls
        self.calls = 0

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, new_prompt:list):
        self._prompt = new_prompt
        self.calls = 0

    def reset(self):
        self._prompt = self.initial_prompt.copy()
        self.calls = 0
        self.conversation.reset()

    def communicate(self, text: str):
        """Append user text, resetting conversation if needed."""
        if self.calls >= self.reset_after_calls:
            self.reset()
        self._prompt.append({"role": "user", "content": text})
        self.calls += 1
        return self._prompt

    def save_feedback(self, text:str):
        self._prompt.append({"role":"assistant","content":text})
        return self._prompt

class ServicePrompt(PromptManager):
    def save_feedback(self, text:str):
        self.reset()


def get_user_ai_mode(user_id):
    return user_ai_modes.get(user_id, DEFAULT_AI_MODE)

async def set_user_ai_mode(user_id, mode):
    mode = mode.lower()
    valid = {"grok", "gpt"}
    if mode not in valid:
        return False
    if mode == "gpt" and not openai_client:
        return False
    user_ai_modes[user_id] = mode
    if db_instance:
        try:
            await db_instance.save_user_ai_mode(user_id, mode)
        except Exception as exc:
            logger.error("Failed to save AI mode: %s", exc)
    return True

def get_user_prompt(user_id):
    return user_prompts.get(user_id, DEFAULT_PROMPT)

async def set_user_prompt(user_id, prompt_name):
    if prompt_name in prompt_loader.list_prompts():
        user_prompts[user_id] = prompt_name
        if db_instance:
            try:
                await db_instance.save_user_prompt(user_id, prompt_name)
            except Exception as exc:
                logger.error("Failed to save prompt: %s", exc)
        return True
    return False

def get_user_system_prompt(user_id):
    prompt_name = get_user_prompt(user_id)
    prompt_content = prompt_loader.get_prompt(prompt_name)
    if prompt_content:
        return [{"role": "system", "content": prompt_content}]
    return [{"role": "system", "content": "You are a friendly assistant"}]

async def get_prompt_with_history(user_id: int, db: DBsqlite, limit: int = 20):
    """Return system prompt combined with user's conversation history."""
    system_prompt = get_user_system_prompt(user_id)
    try:
        history = await db.get_history(user_id, limit)
    except Exception:
        history = []
    return system_prompt + history

