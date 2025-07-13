"""SQLite database helper used by the bot."""

import sqlite3
import logging


class DBsqlite:

    def __init__(self, database: str = "database.db", statements=None) -> None:
        """Connect to the SQLite database and run optional setup statements."""
        self.database = database
        self.connection: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None
        if statements is None:
            statements = []
        self.connect()
        if statements:
            if isinstance(statements, str):
                self.connection.executescript(statements)
            else:
                for stmt in statements:
                    self.connection.execute(stmt)
            self.connection.commit()

    def connect(self) -> None:
        """Open a database connection if not already connected."""
        if self.connection:
            return
        self.connection = sqlite3.connect(self.database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.connection.execute("PRAGMA foreign_keys = ON;")

    def close(self) -> None:
        """Close the database connection."""
        if not self.connection:
            return
        try:
            self.connection.commit()
            self.connection.close()
        except sqlite3.Error as exc:
            logging.error("Error closing database connection: %s", exc)
        finally:
            self.connection = None
            self.cursor = None

    def register_message(self, message, message_sent) -> None:
        """Save a sent message in the database."""
        self.connect()
        try:
            self.cursor.execute(
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
            self.connection.commit()
        except sqlite3.Error as error:
            logging.error("Database error in register_message: %s", error)

    def register_user(self, user) -> None:
        """Insert a Telegram user if it does not already exist."""
        self.connect()
        try:
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO users (tuser_id, nickname, fname, lname)
                VALUES (?, ?, ?, ?)
                """,
                (user.id, user.username, user.first_name, user.last_name),
            )
            self.connection.commit()
        except sqlite3.Error as error:
            logging.error("Database error in register_user: %s", error)


    def register_chat(self, message) -> None:
        """Insert a chat if it does not already exist."""
        self.connect()
        desc = getattr(message.chat, "description", None)
        try:
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO chats (tchat_id, name, nickname, description)
                VALUES (?, ?, ?, ?)
                """,
                (message.chat.id, message.chat.title, message.chat.username, desc),
            )
            self.connection.commit()
        except sqlite3.Error as error:
            logging.debug("An error occurred: %s", error)
    
    def check_user(self, message):
        """Return True if the user has interacted in the chat before."""
        self.connect()
        try:
            row = self.cursor.execute(
                """
                SELECT 1
                FROM messages m
                JOIN users u ON m.user_id=u.id
                JOIN chats c ON m.chat_id=c.id
                WHERE u.tuser_id=? AND c.tchat_id=?
                LIMIT 1
                """,
                (message.from_user.id, message.chat.id),
            ).fetchone()
            return row is not None
        except sqlite3.Error as error:
            logging.error("Database error in check_user: %s", error)
            return False

    def execute(self, statement: str, args: tuple | None = None):
        """Execute a raw SQL statement and return fetched rows if any."""
        self.connect()
        try:
            cur = self.cursor.execute(statement, args or ())
            self.connection.commit()
            if statement.lstrip().upper().startswith("SELECT"):
                return cur.fetchall()
            return cur.rowcount
        except sqlite3.Error as error:
            logging.debug("An error occurred: %s", error)
            logging.debug("For the statement: %s", statement)
            return None

    def get_all_preferences(self):
        """Return a dict of user preferences keyed by Telegram user id."""
        self.connect()
        try:
            rows = self.cursor.execute(
                "SELECT u.tuser_id as tuser_id, p.ai_mode, p.system_prompt "
                "FROM user_preferences p JOIN users u ON p.user_id=u.id"
            ).fetchall()
            prefs = {}
            for row in rows:
                prefs[row["tuser_id"]] = {
                    "ai_mode": row["ai_mode"],
                    "system_prompt": row["system_prompt"],
                }
            return prefs
        except sqlite3.Error as error:
            logging.error("Database error in get_all_preferences: %s", error)
            return {}

    def save_user_ai_mode(self, tuser_id: int, mode: str) -> None:
        """Persist user's preferred AI mode."""
        self.connect()
        try:
            row = self.cursor.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            ).fetchone()
            if not row:
                return
            user_id = row["id"]
            self.cursor.execute(
                "INSERT OR IGNORE INTO user_preferences (user_id, ai_mode, system_prompt) VALUES (?, ?, 'dan')",
                (user_id, mode),
            )
            self.cursor.execute(
                "UPDATE user_preferences SET ai_mode=? WHERE user_id=?",
                (mode, user_id),
            )
            self.connection.commit()
        except sqlite3.Error as error:
            logging.error("Database error in save_user_ai_mode: %s", error)

    def save_user_prompt(self, tuser_id: int, prompt_name: str) -> None:
        """Persist user's preferred system prompt."""
        self.connect()
        try:
            row = self.cursor.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            ).fetchone()
            if not row:
                return
            user_id = row["id"]
            self.cursor.execute(
                "INSERT OR IGNORE INTO user_preferences (user_id, ai_mode, system_prompt) VALUES (?, 'grok', ?)",
                (user_id, prompt_name),
            )
            self.cursor.execute(
                "UPDATE user_preferences SET system_prompt=? WHERE user_id=?",
                (prompt_name, user_id),
            )
            self.connection.commit()
        except sqlite3.Error as error:
            logging.error("Database error in save_user_prompt: %s", error)

    MAX_HISTORY = 50

    def add_history(self, tuser_id: int, role: str, content: str, important: bool = False) -> None:
        """Store a conversation turn for a user and maintain a circular buffer."""
        self.connect()
        try:
            row = self.cursor.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            ).fetchone()
            if not row:
                return
            user_id = row["id"]
            self.cursor.execute(
                "INSERT INTO conversation_history (user_id, role, content, important) VALUES (?, ?, ?, ?)",
                (user_id, role, content, int(important)),
            )
            # trim non-important history to MAX_HISTORY entries
            oldest_kept = self.cursor.execute(
                "SELECT id FROM conversation_history WHERE user_id=? AND important=0 ORDER BY id DESC LIMIT 1 OFFSET ?",
                (user_id, self.MAX_HISTORY - 1),
            ).fetchone()
            if oldest_kept:
                self.cursor.execute(
                    "DELETE FROM conversation_history WHERE user_id=? AND important=0 AND id < ?",
                    (user_id, oldest_kept["id"]),
                )
            self.connection.commit()
        except sqlite3.Error as exc:
            logging.error("Database error in add_history: %s", exc)

    def mark_history_important(self, history_id: int) -> None:
        """Mark a conversation history entry as important."""
        self.connect()
        try:
            self.cursor.execute(
                "UPDATE conversation_history SET important=1 WHERE id=?",
                (history_id,),
            )
            self.connection.commit()
        except sqlite3.Error as exc:
            logging.error("Database error in mark_history_important: %s", exc)

    def get_history(self, tuser_id: int, limit: int = 10):
        """Return the last ``limit`` conversation messages for a user."""
        self.connect()
        try:
            row = self.cursor.execute(
                "SELECT id FROM users WHERE tuser_id=?",
                (tuser_id,),
            ).fetchone()
            if not row:
                return []
            user_id = row["id"]
            rows = self.cursor.execute(
                "SELECT role, content FROM conversation_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except sqlite3.Error as exc:
            logging.error("Database error in get_history: %s", exc)
            return []

