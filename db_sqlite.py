import sqlite3
import logging

"""
A class for interaction with SQLITE DB

"""

class DBsqlite(object):    

    def __init__(self, database='database.db', statements=None):
        self.database = database
        if statements is None:
            statements = []
        self.statement = ''
        self.display = False
        self.connect()
        self.execute(statements)

    def connect(self):
        self.connection = sqlite3.connect(self.database)
        #self.connection.row_factory = lambda cursor, row: row[1]
        self.cursor = self.connection.cursor()
        self.connection.set_trace_callback(print)
        self.connected = True

    def close(self): 
        self.connection.commit()
        self.connection.close()
        print("Closed")
        self.connected = False

    def register_message(self, message, message_sent):
        if not self.connected:
            self.connect()
            close = True
        try:
            self.cursor.execute(
            """
            INSERT INTO messages (id, tmsg_id, chat_id, user_id, forwarded_from_id) values \
                ((?), (?), (SELECT id FROM chats WHERE tchat_id=?), \
                (SELECT id FROM users WHERE tuser_id=?), (?));
            """, \
                (None, message_sent.message_id, message.chat.id, message.from_user.id, message.forward_from)).fetchall()
        except sqlite3.Error as error:
            self.close()
            logging.debug('Terrible error has occurred:', error)
        # close connection if one was opened
        if close:
            self.close()   

    def register_user(self, user):
        
        if not self.connected:
            self.connect()
            close = True
        try:
            self.cursor.execute(
            """
            INSERT OR IGNORE INTO users (id, tuser_id, nickname, fname, lname) \
                values (?, ?, ?, ?, ?)
            """, \
                (None, user.id, user.username, user.first_name, user.last_name)).fetchall()
        except sqlite3.Error as error:
            self.close()
            logging.debug('An error occurred:', error.args[0])
        # close connection if one was opened
        if close:
            self.close()


    def register_chat(self, message):
        
        if not self.connected:
            self.connect()
            close = True
        try:
            self.cursor.execute(
            """
            INSERT OR IGNORE INTO chats (id, tchat_id, name, nickname, description) \
                values (?, ?, ?, ?, ?);
            """, \
                (None, message.chat.id, message.chat.title, message.chat.username, message.chat.description))
        except sqlite3.Error as error:
            self.close()
            logging.debug('An error occurred:', error.args[0])
        # close connection if one was opened
        if close:
            self.close()   
    
    def check_user(self, message):
        
        if not self.connected:
            self.connect()
            close = True
        try:
            data = self.cursor.execute(
            """
            SELECT *
            FROM messages
            WHERE user_id =\
                    (SELECT id FROM users WHERE tuser_id=?)\
                    AND\
                    chat_id =\
                    (SELECT id FROM chats WHERE tchat_id=?)\
            LIMIT 1;
            """, \
                (message.from_user.id, message.chat.id)).fetchall()
        except sqlite3.Error as error:
            self.close()
            logging.debug('An error occurred:', error.args[0])
        # close connection if one was opened
        if close:
            self.close()
        return data 

    def execute(self, statement, args=None):
        queries = []
        close = True
        if not self.connected:
               self.connect()
               close = True
        try:
            logging.debug(statement)
            if args:
                self.cursor.execute(statement, *args)
            else:
                self.cursor.execute(statement)
            #retrieve selected data
            data = self.cursor.fetchone()
            if statement.upper().startswith('SELECT'):
                #append query results
                queries.append(data)

        except sqlite3.Error as error:
            self.close()
            logging.debug('An error occurred:', error.args[0])
            logging.debug('For the statement:', statement)
        # close connection if one was opened
        if close:
            self.close()   
        if self.display:      
            for result in queries:
                if result:
                    for row in result:
                        logging.debug(row)
                else:
                    logging.debug(result)
        else:
            return queries
