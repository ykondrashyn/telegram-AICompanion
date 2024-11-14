# Telegram AI Companion

Telegram AI Companion is a Python-based Telegram bot that can engage in intelligent conversations and analyze images within Telegram group chats. Powered by OpenAI’s GPT-3.5 for text interactions and the BLIP model through Replicate for image analysis, this bot can respond to both text and image inputs, making group conversations more interactive and informative.

## Features

- **Smart Text Conversations**: Contextually relevant and responsive dialogues powered by GPT-3.5.
- **Image Analysis**: Uses the BLIP model via Replicate to analyze images, generate captions, and answer image-related questions.
- **Group Message Engagement**: Engages with both text and image messages in a group setting.
- **Customizable**: Easily modify response behavior, prompt style, and image analysis settings.

## Prerequisites

- Python 3.7+
- Telegram Bot Token
- OpenAI API Key
- Replicate API Key (for BLIP image analysis)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ykondrashyn/telegram-AICompanion.git
   cd telegram-AICompanion
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key
   REPLICATE_API_KEY=your_replicate_api_key
   ```

## Usage

1. **Run the Bot**:
   ```bash
   python bot.py
   ```

2. **Interact on Telegram**: Add the bot to your group, and it will start responding to messages, both text and images, based on the conversation context.

## Example Prompts

- **Text Message**: 
   - **User**: "Summarize our last few messages."
   - **Bot**: "Based on recent messages, it looks like you're discussing project deadlines."

- **Image Analysis**:
   - **User**: (Sends an image of a sunset)
   - **Bot**: "This appears to be a beautiful sunset with orange and pink hues in the sky."

## Database Schema

The bot uses a relational database to manage and track users, messages, and conversations.

### Tables

1. **messages**
   - `id`: INTEGER (Primary Key) - Unique identifier for each message.
   - `user_id`: INTEGER (Foreign Key: users.id) - Links each message to the user who sent it.
   - `content`: TEXT - The actual text content of the message (if any).
   - `timestamp`: DATETIME - The time when the message was sent.

2. **users**
   - `id`: INTEGER (Primary Key) - Unique identifier for each user.
   - `username`: TEXT - Username of the user.
   - `first_name`: TEXT - First name of the user.
   - `last_name`: TEXT - Last name of the user.

3. **conversations**
   - `id`: INTEGER (Primary Key) - Unique identifier for each conversation.
   - `title`: TEXT - Title or description of the conversation.
   - `created_at`: DATETIME - When the conversation was created.

4. **message_conversations**
   - `message_id`: INTEGER (Foreign Key: messages.id) - Links each entry to a specific message.
   - `conversation_id`: INTEGER (Foreign Key: conversations.id) - Links each entry to a specific conversation.

### Relationships

- **messages** are linked to **users** via `user_id`, associating each message with its sender.
- **messages** are linked to **conversations** through the **message_conversations** table, allowing messages to be associated with one or more conversations.

## Customization

### 1. **Modifying the Bot's Prompt**

   The bot uses a predefined prompt to engage in conversation. Here’s the current prompt:
   
   ```python
   prompt = """
   You are a friendly and helpful assistant in a Telegram group chat. Respond thoughtfully to each message, 
   keeping in mind the conversation context and the group setting. Avoid overly long answers unless necessary, 
   and be sure to stay on topic with the current discussion. Your responses should feel natural, engaging, 
   and provide valuable input to the group conversation.
   """
   ```

   - **Customizing**: You can adjust the prompt to change the tone or style, such as making it more formal or topic-specific.

### 2. **Image Analysis Settings**

   The bot uses the BLIP model from Replicate for image analysis, which can generate captions and respond to visual questions. To modify how the bot processes images:
   
   ```python
   # Pseudo-code for image analysis call
   response = replicate.run(
       "salesforce/blip:latest",
       input={"image": image_url}
   )
   ```

   - **Customizing Responses**: Adjust the image analysis prompt within the BLIP integration to change how detailed or descriptive the captions are.

### 3. **Adjusting Response Length**

   Modify `max_tokens` in the OpenAI API call to control response length:
   
   ```python
   response = openai.Completion.create(
       model="gpt-3.5-turbo",
       prompt=prompt,
       max_tokens=100  # Adjust for desired length
   )
   ```

### 4. **Adding Custom Trigger Words**

   Customize when the bot responds by adding keywords:
   
   ```python
   if "help" in message.content.lower() or "question" in message.content.lower():
       response = generate_response(message.content)
   ```

   - **Example**: Only respond when specific words are mentioned, making it more selective in responses.

### 5. **Language and Regional Adaptation**

   Adjust the language in the prompt to support multiple languages if your group uses a non-English language.
