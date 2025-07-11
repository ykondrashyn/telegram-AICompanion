import os
import uuid
import logging
from .config import DEFAULT_AI_MODE

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

DEFAULT_PROMPT = "dan"
user_prompts = {}
user_ai_modes = {}

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

    def communicate(self, text:str):
        if self.calls < self.reset_after_calls:
            self._prompt.append({"role":"user","content":text})
            self.calls += 1
            return self._prompt
        raise ValueError("Maximum number of calls reached")

    def save_feedback(self, text:str):
        self._prompt.append({"role":"assistant","content":text})
        return self._prompt

class ServicePrompt(PromptManager):
    def save_feedback(self, text:str):
        self.reset()


def get_user_ai_mode(user_id):
    return user_ai_modes.get(user_id, DEFAULT_AI_MODE)

def set_user_ai_mode(user_id, mode):
    user_ai_modes[user_id] = mode
    return True

def get_user_prompt(user_id):
    return user_prompts.get(user_id, DEFAULT_PROMPT)

def set_user_prompt(user_id, prompt_name):
    if prompt_name in prompt_loader.list_prompts():
        user_prompts[user_id] = prompt_name
        return True
    return False

def get_user_system_prompt(user_id):
    prompt_name = get_user_prompt(user_id)
    prompt_content = prompt_loader.get_prompt(prompt_name)
    if prompt_content:
        return [{"role": "system", "content": prompt_content}]
    return [{"role": "system", "content": "You are a friendly assistant"}]

