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
| `test_bot_reply_new_user` | Confirms the bot greets new users who reply to its messages. |
| `test_offtopic_handler` | Tests the `/offtopic` command which starts a new conversation thread. |
| `test_url_handler_generic` | Validates that URLs in regular messages trigger a generic link preview response. |


