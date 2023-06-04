from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import sys

sys.path.append('frontend')
sys.path.append('backend')
from frontend.windows import *
import threading
import math
import datetime


class Client:
    def __init__(self):
        self.mainWin = MainWin()

        self.registered = False

        self.database = None
        self.init_signal_slots()

        self.question_search_keys = self.mainWin.getQuestionSearchKey()
        self.old_user_info = None


    def init_signal_slots(self):

        self.mainWin.pageSignal.connect(self.turn_page)
        self.mainWin.logoutBtn.clicked.connect(self.log_out)
        self.mainWin.searchQuestionBtn.clicked.connect(self.search_question)



    def log_out(self):
        reply = QMessageBox.question(self.mainWin,
                                     '询问',
                                     "确定要退出吗？",
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.registered = False

            self.mainWin.close_flag = False
            self.mainWin.close()
            self.mainWin.close_flag = True
        else:
            pass


    def update_question_table(self, keys, page_num=1):
        if self.database:
            offset = (page_num - 1) * 20
            table, total_time = self.database.search_question(*keys, limit=20, offset=offset)
            if table:
                self.mainWin.updateQuestionTable(table)
                self.mainWin.showQuestionTime(total_time)
        else:
            QMessageBox.warning(self.mainWin, '警告', '请先链接至数据库！')

    def search_question(self):
        # id, name, author, press, release_date, ISBN
        # 可以为空
        self.question_search_keys = self.mainWin.getQuestionSearchKey()
        if not self.question_search_keys:
            return

        total_num = self.database.get_book_num(*self.question_search_keys)
        total_page = math.ceil(total_num / 20)
        self.mainWin.setTotalPage('book', total_page)
        self.mainWin.showQuestionNum(total_num)
        self.update_question_table(keys=self.question_search_keys)

        return




    # SECTION: 翻页
    def turn_page(self, signal):
        type = signal[0]
        command = signal[1]
        page = int(signal[2])  # 可以是上一次的current page，也可以是target page
        total_page = self.mainWin.totalPage(type)

        if command == 'first':
            cur_page = str(1)
        elif command == 'pre':
            if page == 1:  # 当前页面已经是第一页
                QMessageBox.information(self.mainWin, '提示', '已经是第一页了！')
                return
            cur_page = str(page - 1)
        elif command == 'next':
            if page == total_page:  # 当前页面已经是最后一页
                QMessageBox.information(self.mainWin, '提示', '已经是最后一页了！')
                return
            cur_page = str(page + 1)
        elif command == 'last':
            cur_page = str(total_page)
        elif command == 'jump':
            if page < 0 or page > total_page:  # 跳转超出范围
                QMessageBox.information(self.mainWin, '提示', '非法的跳转页码！')
                return
            cur_page = str(page)
        else:
            QMessageBox.critical(self.mainWin, '错误', '未知指令类型！')
            return

        if type == 'book':
            self.mainWin.questionPage.setText('{} / {}'.format(cur_page, total_page))
            self.update_question_table(keys=self.question_search_keys, page_num=int(cur_page))
        else:
            QMessageBox.critical(self.mainWin, '错误', '未知数据类型！')
            return


if __name__ == '__main__':
    app = QApplication([])
    client = Client()
    client.mainWin.show()
    sys.exit(app.exec())
