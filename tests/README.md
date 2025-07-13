# Test Suite

This directory contains unit tests for the Telegram handlers. The tests use
`pytest` together with `pytest-asyncio` for running asynchronous code.

## Running the tests

1. Install dependencies (preferably in a virtual environment):
   ```bash
   pip install -r ../requirements.txt pytest pytest-asyncio
   ```
2. Execute the test suite from the repository root:
   ```bash
   pytest -q
   ```

## Test overview

| Test name | Description |
|-----------|-------------|
| `test_mode_show_current` | Verifies that `/mode` without arguments returns the current AI mode. |
| `test_mode_set_valid` | Checks that `/mode <mode>` switches to a valid mode and sends a confirmation. |
| `test_prompt_invalid` | Ensures `/prompt <name>` with an unknown name replies with an error. |
| `test_mode_set_invalid` | Passing an invalid mode shows an error message. |
| `test_prompt_show_current` | `/prompt` without arguments shows the current prompt. |
| `test_prompt_reload` | `/prompt reload` reloads prompt files. |
| `test_bot_reply_new_user` | Confirms the bot greets new users who reply to its messages. |
| `test_bot_reply_existing_user` | Ensures no greeting is sent when a known user replies again. |
| `test_ignore_private` | Messages in private chats are ignored. |
| `test_reply_not_to_bot` | Replying to another user triggers a single AI response without greeting. |
| `test_offtopic_handler` | Tests the `/offtopic` command which starts a new conversation thread. |
| `test_url_handler_generic` | Validates that URLs in regular messages trigger a generic link preview response. |
| `test_url_handler_youtube` | YouTube links trigger video info lookup and AI reply. |
| `test_photo_handler` | Sending a photo results in an AI reply after processing the image. |
| `test_photo_handler_caption_url` | Photo caption URLs are parsed and included in the prompt. |
| `test_joined_bot_added` | When the bot joins a group it sends a welcome message and registers the chat. |
| `test_joined_regular_user` | No action is taken when a regular user joins the group. |
| `test_clear_history_command` | `/clearhistory` removes a user's conversation history. |
| `test_add_and_get_history` | Verifies database history storage functions. |


