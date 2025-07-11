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
