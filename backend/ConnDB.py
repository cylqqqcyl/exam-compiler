import sqlite3
import numpy as np
import traceback

class Database:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.question_attr = ('q_id', 'q_content', 'q_subject', 'q_year', 'q_type', 'q_answer')


    def create_connection(self):
        try:
            # 打开数据库连接
            self.conn = sqlite3.connect('test.db')
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(e)
            return False
        self.check_table()
        return True

    def check_table(self):
        # 检测Question表是否存在
        sql = "SELECT * FROM question"
        try:
            self.cursor.execute(sql)
        except Exception as e:
            print(e)
            traceback.print_exc()
            self.create_question_table()

    def create_question_table(self):
        # 创建question表
        sql = '''CREATE TABLE question (
            q_id INTEGER PRIMARY KEY AUTOINCREMENT,
            q_content TEXT NOT NULL,
            q_subject TEXT NOT NULL,
            q_year TEXT NOT NULL,
            q_type TEXT NOT NULL,
            q_answer TEXT NOT NULL
        )'''
        self.cursor.execute(sql)
        self.conn.commit()



    # SECTION: Question

    def add_question(self, q_content, q_subject, q_year, q_type, q_answer):
        sql = "INSERT INTO question (q_content, q_subject, q_year, q_type, q_answer) VALUES (%s, %s, %s, %s, %s)"
        if self.conn:
            try:
                self.cursor.execute(sql, (q_content, q_subject, q_year, q_type, q_answer))
            except Exception as e:
                self.conn.rollback()
                print(e)
            else:
                self.conn.commit()

    def read_question(self,limit,offset=0):
        sql = "SELECT * FROM question LIMIT %d OFFSET %d" % (limit, offset)
        if self.conn:
            try:
                self.cursor.execute(sql)
            except Exception as e:
                self.conn.rollback()
                print(e)
                return None
            else:
                book_table = self.cursor.fetchall()
                return book_table

    def get_question_num(self, q_content='', q_subject='', q_year='', q_type=''):
        sql = "SELECT COUNT(*) FROM question WHERE q_content LIKE %s AND q_subject LIKE %s AND q_year LIKE %s AND q_type LIKE %s"
        sql = sql % (
            "'%" + q_content + "%'", "'%" + q_subject + "%'", "'%" + q_year + "%'", "'%" + q_type + "%'")

        if self.conn:
            try:
                self.cursor.execute(sql)
            except Exception as e:
                self.conn.rollback()
                print(e)
                return None
            else:
                num = self.cursor.fetchone()
                return num[0]

    def search_question(self, q_content='', q_subject='', q_year='', q_type='', limit=10, offset=0):

        sql = "SELECT * FROM question WHERE q_content LIKE %s AND q_subject LIKE %s AND q_year LIKE %s AND q_type LIKE %s"
        sql = sql % ("'%" + q_content + "%'", "'%" + q_subject + "%'", "'%" + q_year + "%'", "'%" + q_type + "%'")
        sql += " LIMIT %d OFFSET %d" % (limit, offset)
        if self.conn:
            try:
                self.cursor.execute(sql)
            except Exception as e:
                self.conn.rollback()
                print(e)
                return None
            else:
                book_table = self.cursor.fetchall()
                return book_table




if __name__ == '__main__':
    database = Database()
    database.create_connection()
