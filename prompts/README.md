# System Prompts

This directory contains different system prompts that users can choose from to customize the bot's personality and behavior.

## Available Prompts

### `dan.txt`
The original DAN (Do Anything Now) prompt that gives the AI a more unrestricted and creative personality. This prompt encourages the AI to be more opinionated and less filtered.

### `friendly.txt`
A warm and approachable personality that's perfect for casual group conversations. Uses emojis and maintains a helpful, engaging tone.

### `professional.txt`
A formal and knowledgeable assistant that's ideal for work-related discussions or when you need accurate, well-structured information.

### `creative.txt`
An imaginative and artistic personality that approaches conversations with creativity, humor, and original thinking. Great for brainstorming and creative discussions.

### `sarcastic.txt`
A witty and sarcastic personality that responds with clever humor and mild sarcasm while still being helpful. Perfect for adding some humor to conversations.

### `concise.txt`
A direct and brief assistant that keeps responses short and to the point. Ideal when you want quick, no-nonsense answers.

## Usage

Users can switch between prompts using the `/prompt` command:

- `/prompt` - Show current prompt and list available options
- `/prompt friendly` - Switch to the friendly prompt
- `/prompt professional` - Switch to the professional prompt
- `/prompt creative` - Switch to the creative prompt
- `/prompt sarcastic` - Switch to the sarcastic prompt
- `/prompt concise` - Switch to the concise prompt
- `/prompt dan` - Switch to the DAN prompt
- `/prompt reload` - Reload all prompts from files (useful after editing)

## Adding New Prompts

To add a new prompt:

1. Create a new `.txt` file in this directory
2. Write your system prompt content in the file
3. Use `/prompt reload` to make it available
4. Users can then switch to it using `/prompt [filename]` (without the .txt extension)

## Editing Prompts

You can edit any of the existing prompt files to customize the bot's behavior. After making changes, use `/prompt reload` to apply the updates.

## Notes

- Each user can have their own prompt preference
- Prompt changes take effect in new conversations
- The default prompt is set to "concise" but can be changed in the environment variables
- Prompts are loaded at startup and can be reloaded without restarting the bot
