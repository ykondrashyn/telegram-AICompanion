"""Asynchronous SQLite helper used by the bot."""

import logging
import aiosqlite

class DBsqlite:
    def __init__(self, database: str = "database.db", statements=None) -> None:
        self.database = database
        self.connection: aiosqlite.Connection | None = None
        self.statements = statements

    async def connect(self) -> None:
        if self.connection:
            return
        self.connection = await aiosqlite.connect(self.database)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA foreign_keys = ON;")
        if self.statements:
            if isinstance(self.statements, str):
                await self.connection.executescript(self.statements)
            else:
                for stmt in self.statements:
                    await self.connection.execute(stmt)
            await self.connection.commit()

    async def close(self) -> None:
        if not self.connection:
            return
        try:
            await self.connection.commit()
            await self.connection.close()
        except Exception as exc:
            logging.error("Error closing database connection: %s", exc)
        finally:
            self.connection = None

    async def register_message(self, message, message_sent) -> None:
        await self.connect()
        try:
            await self.connection.execute(
                """
                INSERT INTO messages (tmsg_id, chat_id, user_id, forwarded_from_id)
                SELECT ?, c.id, u.id, ?
                FROM chats c, users u
                WHERE c.tchat_id=? AND u.tuser_id=?
                """,
                (
                    message_sent.message_id,
                    None,
                    message.chat.id,
                    message.from_user.id,
                ),
            )
            await self.connection.commit()
        except Exception as error:
            logging.error("Database error in register_message: %s", error)

    async def register_user(self, user) -> None:
        await self.connect()
        try:
            await self.connection.execute(
                """
                INSERT OR IGNORE INTO users (tuser_id, nickname, fname, lname)
                VALUES (?, ?, ?, ?)
                """,
                (user.id, user.username, user.first_name, user.last_name),
            )
            await self.connection.commit()
        except Exception as error:
            logging.error("Database error in register_user: %s", error)

    async def register_chat(self, message) -> None:
        await self.connect()
        desc = getattr(message.chat, "description", None)
        try:
            await self.connection.execute(
                """
                INSERT OR IGNORE INTO chats (tchat_id, name, nickname, description)
                VALUES (?, ?, ?, ?)
                """,
                (message.chat.id, message.chat.title, message.chat.username, desc),
            )
            await self.connection.commit()
        except Exception as error:
            logging.debug("An error occurred: %s", error)

    async def check_user(self, message):
        await self.connect()
        try:
            cursor = await self.connection.execute(
                """
                SELECT 1
                FROM messages m
                JOIN users u ON m.user_id=u.id
                JOIN chats c ON m.chat_id=c.id
                WHERE u.tuser_id=? AND c.tchat_id=?
                LIMIT 1
                """,
                (message.from_user.id, message.chat.id),
            )
            row = await cursor.fetchone()
            return row is not None
        except Exception as error:
            logging.error("Database error in check_user: %s", error)
            return False

    async def execute(self, statement: str, args: tuple | None = None):
        await self.connect()
        try:
            cursor = await self.connection.execute(statement, args or ())
            await self.connection.commit()
            if statement.lstrip().upper().startswith("SELECT"):
                return await cursor.fetchall()
            return cursor.rowcount
        except Exception as error:
            logging.debug("An error occurred: %s", error)
            logging.debug("For the statement: %s", statement)
            return None

    async def get_all_preferences(self):
        await self.connect()
        try:
            cursor = await self.connection.execute(
                "SELECT u.tuser_id as tuser_id, p.ai_mode, p.system_prompt "
                "FROM user_preferences p JOIN users u ON p.user_id=u.id"
            )
            rows = await cursor.fetchall()
            prefs = {}
            for row in rows:
                prefs[row["tuser_id"]] = {
                    "ai_mode": row["ai_mode"],
                    "system_prompt": row["system_prompt"],
                }
            return prefs
        except Exception as error:
            logging.error("Database error in get_all_preferences: %s", error)
            return {}

    async def save_user_ai_mode(self, tuser_id: int, mode: str) -> None:
        await self.connect()
        try:
            cursor = await self.connection.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return
            user_id = row["id"]
            await self.connection.execute(
                "INSERT OR IGNORE INTO user_preferences (user_id, ai_mode, system_prompt) VALUES (?, ?, 'dan')",
                (user_id, mode),
            )
            await self.connection.execute(
                "UPDATE user_preferences SET ai_mode=? WHERE user_id=?",
                (mode, user_id),
            )
            await self.connection.commit()
        except Exception as error:
            logging.error("Database error in save_user_ai_mode: %s", error)

    async def save_user_prompt(self, tuser_id: int, prompt_name: str) -> None:
        await self.connect()
        try:
            cursor = await self.connection.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return
            user_id = row["id"]
            await self.connection.execute(
                "INSERT OR IGNORE INTO user_preferences (user_id, ai_mode, system_prompt) VALUES (?, 'grok', ?)",
                (user_id, prompt_name),
            )
            await self.connection.execute(
                "UPDATE user_preferences SET system_prompt=? WHERE user_id=?",
                (prompt_name, user_id),
            )
            await self.connection.commit()
        except Exception as error:
            logging.error("Database error in save_user_prompt: %s", error)

    MAX_HISTORY = 50

    async def add_history(self, tuser_id: int, role: str, content: str, important: bool = False) -> None:
        await self.connect()
        try:
            cursor = await self.connection.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return
            user_id = row["id"]
            await self.connection.execute(
                "INSERT INTO conversation_history (user_id, role, content, important) VALUES (?, ?, ?, ?)",
                (user_id, role, content, int(important)),
            )
            oldest_kept_cur = await self.connection.execute(
                "SELECT id FROM conversation_history WHERE user_id=? AND important=0 ORDER BY id DESC LIMIT 1 OFFSET ?",
                (user_id, self.MAX_HISTORY - 1),
            )
            oldest_kept = await oldest_kept_cur.fetchone()
            if oldest_kept:
                await self.connection.execute(
                    "DELETE FROM conversation_history WHERE user_id=? AND important=0 AND id < ?",
                    (user_id, oldest_kept["id"]),
                )
            await self.connection.commit()
        except Exception as exc:
            logging.error("Database error in add_history: %s", exc)

    async def mark_history_important(self, history_id: int) -> None:
        await self.connect()
        try:
            await self.connection.execute(
                "UPDATE conversation_history SET important=1 WHERE id=?",
                (history_id,),
            )
            await self.connection.commit()
        except Exception as exc:
            logging.error("Database error in mark_history_important: %s", exc)

    async def clear_history(self, tuser_id: int) -> None:
        await self.connect()
        try:
            cursor = await self.connection.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return
            user_id = row["id"]
            await self.connection.execute(
                "DELETE FROM conversation_history WHERE user_id=?",
                (user_id,),
            )
            await self.connection.commit()
        except Exception as exc:
            logging.error("Database error in clear_history: %s", exc)

    async def get_history(self, tuser_id: int, limit: int = 10):
        await self.connect()
        try:
            cursor = await self.connection.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return []
            user_id = row["id"]
            cur2 = await self.connection.execute(
                "SELECT role, content FROM conversation_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
            rows = await cur2.fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except Exception as exc:
            logging.error("Database error in get_history: %s", exc)
            return []

    async def is_bot_message(self, tmsg_id: int) -> bool:
        """Return True if we have stored a message with this Telegram ID."""
        await self.connect()
        try:
            cur = await self.connection.execute(
                "SELECT 1 FROM messages WHERE tmsg_id=?", (tmsg_id,)
            )
            return await cur.fetchone() is not None
        except Exception as exc:
            logging.error("Database error in is_bot_message: %s", exc)
            return False

