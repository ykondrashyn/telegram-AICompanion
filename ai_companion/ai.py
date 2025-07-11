import logging
import os
import base64
import urllib.request
from openai import OpenAI
from .config import OPENAI_API_KEY, XAI_API_KEY

logger = logging.getLogger(__name__)

try:
    from xai_sdk import Client as XAIClient
    from xai_sdk.chat import system, user, image
    XAI_AVAILABLE = True
except ImportError:
    XAI_AVAILABLE = False

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def download_and_encode_image(file_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        opener = urllib.request.build_opener()
        opener.addheaders = list(headers.items())
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(file_url, 'temp_image.jpg')
        with open('temp_image.jpg', 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        os.remove('temp_image.jpg')
        return image_data
    except Exception as e:
        logger.error(f"Error downloading/encoding image: {e}")
        return None

def create_image_message_content(text, image_data=None, image_url=None):
    content = [{"type": "text", "text": text}]
    if image_data:
        content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{image_data}"}})
    elif image_url:
        content.append({"type":"image_url","image_url":{"url":image_url}})
    return content

def _openai_chat(promptObj):
    if not openai_client:
        raise ValueError("OpenAI API key not configured")
    response = openai_client.chat.completions.create(model="gpt-4o", messages=promptObj.prompt)
    return response.choices[0].message.content

def _grok_chat(promptObj):
    if not XAI_AVAILABLE or not XAI_API_KEY:
        raise ValueError("xAI SDK not available")
    client = XAIClient(api_key=XAI_API_KEY)
    chat = client.chat.create(model="grok-4")
    for msg in promptObj.prompt:
        if msg["role"] == "system":
            try:
                chat.append(system(msg["content"]))
            except Exception:
                logger.debug("System messages not supported")
        elif msg["role"] == "user":
            if isinstance(msg["content"], str):
                chat.append(user(msg["content"]))
            elif isinstance(msg["content"], list):
                text_content = ""
                image_content = None
                for item in msg["content"]:
                    if item["type"] == "text":
                        text_content = item["text"]
                    elif item["type"] == "image_url":
                        image_content = item["image_url"]["url"]
                if image_content:
                    chat.append(user(text_content, image(image_url=image_content, detail="high")))
                else:
                    chat.append(user(text_content))
    response = chat.sample()
    return response.content

def generic_chat(promptObj, user_text, user_id=None, image_data=None, image_url=None, ai_mode="grok"):
    if image_data or image_url:
        user_content = create_image_message_content(user_text, image_data, image_url)
        promptObj._prompt.append({"role":"user","content":user_content})
        promptObj.calls += 1
    else:
        promptObj.communicate(user_text)
    if ai_mode == "grok" and XAI_AVAILABLE and XAI_API_KEY:
        try:
            ai_reply = _grok_chat(promptObj)
        except Exception as e:
            logger.error(f"Grok error: {e}")
            if openai_client and OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
                try:
                    ai_reply = _openai_chat(promptObj)
                except Exception as openai_e:
                    logger.error(f"OpenAI fallback error: {openai_e}")
                    ai_reply = "Sorry, I'm experiencing technical difficulties with both AI services. Please try again later."
            else:
                ai_reply = "Sorry, I'm experiencing technical difficulties. Please try again later."
    else:
        if openai_client and OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                ai_reply = _openai_chat(promptObj)
            except Exception as e:
                logger.error(f"OpenAI error: {e}")
                ai_reply = "Sorry, I'm experiencing technical difficulties. Please try again later."
        else:
            ai_reply = "Sorry, OpenAI is not properly configured. Please check your API key."
    promptObj.save_feedback(ai_reply)
    return ai_reply
