import sqlite3
import numpy as np
import traceback

class Database:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.question_attr = ('q_id', 'q_content', 'q_origin', 'q_type', 'q_answer')


    def create_connection(self, db_file):
        try:
            # 打开数据库连接
            self.conn = sqlite3.connect(db_file)
            self.cursor = self.conn.cursor()
        except Exception as e:
            print(e)
            return False
        self.check_table()
        return True

    def check_table(self):
        # 检测Question表是否存在，并且属性是否正确
        sql = "SELECT * FROM question"
        if self.conn:
            try:
                self.cursor.execute(sql)
            except Exception as e:
                self.create_question_table()

            else:
                table = self.cursor.fetchone()
                if table is None:
                    self.create_question_table()
                else:
                    # 检查属性
                    sql = "PRAGMA table_info('question')"
                    self.cursor.execute(sql)
                    table = self.cursor.fetchall()
                    if len(table) != len(self.question_attr):
                        self.create_question_table()
                    else:
                        for i, attr in enumerate(self.question_attr):
                            if table[i][1] != attr:
                                self.create_question_table()
                                break

    def create_question_table(self):
        # 删除question表
        sql = "DROP TABLE IF EXISTS question"
        self.cursor.execute(sql)
        self.conn.commit()
        # 创建question表
        sql = '''CREATE TABLE question (
            q_id INTEGER PRIMARY KEY AUTOINCREMENT,
            q_content TEXT NOT NULL,
            q_origin TEXT NOT NULL,
            q_type TEXT NOT NULL,
            q_answer TEXT NOT NULL
        )'''
        self.cursor.execute(sql)
        self.conn.commit()



    # SECTION: Question

    def add_question(self, q_content, q_origin, q_type, q_answer):
        sql = "INSERT INTO question (q_content, q_origin, q_type, q_answer) VALUES (?, ?, ?, ?)"
        if self.conn:
            try:
                self.cursor.execute(sql, (q_content, q_origin, q_type, q_answer))
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

    def get_question_num(self, q_content='', q_origin='', q_type=''):
        sql = "SELECT COUNT(*) FROM question WHERE q_content LIKE %s AND q_origin LIKE %s AND q_type LIKE %s"
        sql = sql % (
            "'%" + q_content + "%'", "'%" + q_origin + "%'", "'%" + q_type + "%'")

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

    def search_question(self, q_content='', q_origin = '', q_type='', limit=10, offset=0):

        sql = "SELECT * FROM question WHERE q_content LIKE %s AND q_origin LIKE %s AND q_type LIKE %s"
        sql = sql % ("'%" + q_content + "%'", "'%" + q_origin + "%'", "'%" + q_type + "%'")
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
    database.create_connection('test.db')
    database.add_question('test', 'test', 'test', 'test')
    print(database.get_question_num())

