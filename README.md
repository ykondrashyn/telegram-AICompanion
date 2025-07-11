# Telegram AI Companion

Telegram AI Companion is a Python-based Telegram bot that can engage in intelligent conversations within Telegram group chats. Now featuring dual AI support with **xAI's Grok** as the default provider and **OpenAI's GPT** as an alternative, this bot offers flexible AI interactions with easy mode switching and customizable system prompts.

## Features

- **Dual AI Support**: Switch between xAI's Grok (default) and OpenAI's GPT-4o with simple commands
- **Native Image Understanding**: Both Grok and GPT-4o can analyze images directly in conversations
- **Smart Text Conversations**: Contextually relevant and responsive dialogues powered by advanced AI models
- **Mode Switching**: Users can individually choose their preferred AI provider with `/mode` command
- **Customizable Prompts**: Switch between different personality prompts (DAN, friendly, professional, creative, sarcastic, concise)
- **Group Message Engagement**: Engages with both text and image messages in a group setting
- **YouTube Integration**: Special handling for YouTube links with video information and thumbnail analysis
- **Link Preview**: Automatic link analysis and preview generation with image understanding
- **Persistent Preferences**: User preferences for AI mode and prompts are remembered
## Architecture

The bot is organized as a Python package `ai_companion` separating AI providers, prompt management, handlers and utilities. The `bot.py` entry point simply calls `ai_companion.main.run()`.

## Prerequisites

- Python 3.10+ (required for xAI SDK)
- Telegram Bot Token
- xAI API Key (for Grok with vision support)
- OpenAI API Key (optional, for GPT-4o with vision support)
- YouTube API Key (optional, for enhanced YouTube link handling)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ykondrashyn/telegram-AICompanion.git
   cd telegram-AICompanion
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate virtual environment
   # On Linux/macOS:
   source venv/bin/activate

   # On Windows:
   # venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your actual API keys:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   XAI_API_KEY=your_xai_api_key
   OPENAI_API_KEY=your_openai_api_key  # Optional
   YT_API_KEY=your_youtube_api_key     # Optional
   DB_FILENAME=bot_database.db
   DEFAULT_AI_MODE=grok
   ```

## Usage

1. **Activate Virtual Environment** (if not already active):
   ```bash
   # On Linux/macOS:
   source venv/bin/activate

   # On Windows:
   # venv\Scripts\activate
   ```

2. **Test Setup** (optional but recommended):
   ```bash
   python test_setup.py
   ```

3. **Run the Bot**:
   ```bash
   python bot.py
   ```

4. **Interact on Telegram**: Add the bot to your group, and it will start responding to messages based on the conversation context.

5. **Deactivate Virtual Environment** (when done):
   ```bash
   deactivate
   ```

## Commands

### AI Mode Switching
- `/mode` - Show current AI mode and available options
- `/mode grok` - Switch to xAI's Grok
- `/mode gpt` - Switch to OpenAI's GPT (if configured)

### Prompt Switching
- `/prompt` - Show current prompt and available options
- `/prompt friendly` - Switch to friendly personality
- `/prompt professional` - Switch to professional tone
- `/prompt creative` - Switch to creative personality
- `/prompt sarcastic` - Switch to sarcastic/witty responses
- `/prompt concise` - Switch to brief, direct responses
- `/prompt dan` - Switch to DAN (Do Anything Now) mode
- `/prompt reload` - Reload prompts from files

### Other Commands
- `/offtopic [message]` - Start a new conversation topic
- Reply to any bot message to continue the conversation

## System Prompts

The bot includes several pre-configured personality prompts in the `prompts/` directory:

- **DAN**: Unrestricted and creative personality
- **Friendly**: Warm and approachable with emojis
- **Professional**: Formal and knowledgeable
- **Creative**: Imaginative and artistic
- **Sarcastic**: Witty and humorous
- **Concise**: Brief and direct

You can add custom prompts by creating new `.txt` files in the `prompts/` directory. See `prompts/README.md` for details.

## Configuration

### Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required)
- `XAI_API_KEY`: Your xAI API key for Grok (required)
- `OPENAI_API_KEY`: Your OpenAI API key (optional, for GPT fallback)
- `YT_API_KEY`: YouTube Data API key (optional, for enhanced YouTube features)
- `DB_FILENAME`: Database file name (default: bot_database.db)
- `DEFAULT_AI_MODE`: Default AI mode - "grok" or "gpt" (default: grok)

### Database

The bot uses SQLite to store user preferences and conversation history. The database is automatically created on first run.
Indexes are created on common lookup fields to keep queries fast even as the database grows. The helper in `ai_companion/db.py` wraps SQLite access and keeps a single connection open.

## Features in Detail

### AI Mode Switching
Users can switch between different AI providers:
- **Grok**: xAI's advanced AI model with vision support (default)
- **GPT**: OpenAI's GPT-4o with vision support (fallback option)

### Native Image Understanding
Both AI providers now support native image analysis:
- **Photo Messages**: Send photos directly to the bot for analysis and discussion
- **YouTube Thumbnails**: Automatic analysis of video thumbnails for better context
- **Link Previews**: Image analysis for website thumbnails and previews
- **Integrated Conversations**: Images are part of the conversation flow, not separate analysis

### Prompt Personalities
Each user can choose their preferred AI personality:
- Prompts are loaded from the `prompts/` directory
- Changes take effect in new conversations
- Prompts can be reloaded without restarting the bot

### YouTube Integration
- Automatic detection of YouTube URLs
- Fetches video title, description, and thumbnail
- Shows top-rated comments
- AI provides commentary on the video content

### Link Preview
- Generates previews for web links
- Extracts title, description, and images
- AI provides commentary on linked content

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`
2. **API Key Errors**: Verify your API keys are correctly set in the `.env` file
3. **Permission Errors**: Ensure the bot has permission to read messages in your group
4. **Prompt Not Found**: Use `/prompt reload` to refresh available prompts

### Logs

The bot logs important events and errors. Check the console output for debugging information.

## Testing

Unit tests live in the `tests/` directory and use `pytest` with
`pytest-asyncio` for asynchronous handlers. Install the extra dependencies and
run the suite from the project root:

```bash
pip install -r requirements.txt pytest pytest-asyncio
pytest -q
```

See `tests/README.md` for a description of each test.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Support

For issues and questions, please open an issue on the GitHub repository.
