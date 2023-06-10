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
from backend.ConnDB import Database
from backend.examSP import ExamScanner, ExamParser, extract_questions

class ScannerThread(QThread):
    scannerSignal = pyqtSignal(list)
    def __init__(self, file_path, parent=None):
        super(ScannerThread, self).__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            scanner = ExamScanner(self.file_path)
            result = scanner.scan()
            self.scannerSignal.emit(result)
        except Exception as e:
            print(e)
            self.scannerSignal.emit([])


class ParserThread(QThread):
    parserSignal = pyqtSignal(dict)
    def __init__(self, file_path, parent=None):
        super(ParserThread, self).__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            parser = ExamParser(self.file_path)
            result = parser.parse()
            self.parserSignal.emit(result)
        except Exception as e:
            print(e)
            self.parserSignal.emit({})

class SyntaxThread(QThread):
    syntaxSignal = pyqtSignal(list)
    def __init__(self, ast, parent=None):
        super(SyntaxThread, self).__init__(parent)
        self.ast = ast

    def run(self):
        try:
            questions = extract_questions(self.ast, self.ast.get('title'))
            self.syntaxSignal.emit(questions)
        except Exception as e:
            print(e)
            self.syntaxSignal.emit([])




class Client:
    def __init__(self):
        self.mainWin = MainWin()

        self.file_path = None

        self.ast = None

        self.database = None
        self.init_signal_slots()

        self.question_search_keys = self.mainWin.getQuestionSearchKey()
        self.old_user_info = None

        self.create_connection()

        self.scannerThread = None



    def init_signal_slots(self):

        self.mainWin.pageSignal.connect(self.turn_page)
        self.mainWin.logoutBtn.clicked.connect(self.log_out)
        self.mainWin.searchQuestionBtn.clicked.connect(self.search_question)

        self.mainWin.uploadBtn.clicked.connect(self.uploadFile)
        self.mainWin.makeExam.clicked.connect(self.download_exam)

        self.mainWin.startScannerBtn.clicked.connect(self.start_scanner)
        self.mainWin.startParserBtn.clicked.connect(self.start_parser)
        self.mainWin.startSyntaxBtn.clicked.connect(self.start_syntax)

    def create_connection(self):
        self.database = Database()
        self.database.create_connection()


    def log_out(self):
        reply = QMessageBox.question(self.mainWin,
                                     '询问',
                                     "确定要退出吗？",
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:

            self.mainWin.close_flag = False
            self.mainWin.close()
            self.mainWin.close_flag = True
        else:
            pass


    def update_question_table(self, keys, page_num=1):
        if self.database:
            offset = (page_num - 1) * 20
            table = self.database.search_question(*keys, limit=20, offset=offset)
            if table:
                self.mainWin.updateQuestionTable(table)
        else:
            QMessageBox.warning(self.mainWin, '警告', '请先链接至数据库！')

    def search_question(self):
        # id, content, subject, year, type, answer
        # 可以为空
        self.question_search_keys = self.mainWin.getQuestionSearchKey()
        if not self.question_search_keys:
            return

        total_num = self.database.get_question_num(*self.question_search_keys)
        total_page = math.ceil(total_num / 20)
        self.mainWin.setTotalPage('question', total_page)
        self.mainWin.showQuestionNum(total_num)
        self.update_question_table(keys=self.question_search_keys)

        return

    # SECTION: Scanner

    def uploadFile(self):
        self.file_path, _ = QFileDialog.getOpenFileName(self.mainWin, '选择文件', '', '*.txt;;*.doc;;*.docx;;*.pdf;;All Files (*)')
        if self.file_path:
            self.mainWin.uploadDisplay.setText(self.file_path)
            self.mainWin.uploadDisplay_2.setText(self.file_path)
            self.mainWin.uploadDisplay_3.setText(self.file_path)
            self.mainWin.scannerCheck.setText('未完成')
            self.mainWin.scannerCheck.setStyleSheet("color: #ff0000;")
            self.mainWin.scannerCheck_2.setText('未完成')
            self.mainWin.scannerCheck_2.setStyleSheet("color: #ff0000;")
            self.mainWin.parserCheck.setText('未完成')
            self.mainWin.parserCheck.setStyleSheet("color: #ff0000;")


    def start_scanner(self):
        if not self.file_path:
            QMessageBox.warning(self.mainWin, '警告', '请先选择文件！')
            return
        self.mainWin.startScannerBtn.setEnabled(False)
        self.mainWin.startParserBtn.setEnabled(False)
        self.mainWin.startSyntaxBtn.setEnabled(False)

        self.scannerThread = ScannerThread(self.file_path)
        self.scannerThread.scannerSignal.connect(self.scanner_callback)
        self.scannerThread.start()

    def scanner_callback(self, result):
        if result:
            #前端显示
            QMessageBox.information(self.mainWin, '提示', '词法分析完成！')
            self.mainWin.scannerCheck.setText('已完成')
            self.mainWin.scannerCheck.setStyleSheet("color: #00ff00;")
            self.mainWin.scannerCheck_2.setText('已完成')
            self.mainWin.scannerCheck_2.setStyleSheet("color: #00ff00;")
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)
            #更新词法分析结果
            self.mainWin.updateLexemeTable(result)
        else:
            QMessageBox.warning(self.mainWin, '警告', '词法分析失败！')

    # SECTION: Parser

    def start_parser(self):
        if not self.file_path:
            QMessageBox.warning(self.mainWin, '警告', '请先选择文件！')
            return
        if not self.mainWin.scannerCheck.text() == '已完成':
            QMessageBox.warning(self.mainWin, '警告', '请先完成词法分析！')
            return
        self.mainWin.startScannerBtn.setEnabled(False)
        self.mainWin.startParserBtn.setEnabled(False)
        self.mainWin.startSyntaxBtn.setEnabled(False)

        self.parserThread = ParserThread(self.file_path)
        self.parserThread.parserSignal.connect(self.parser_callback)
        self.parserThread.start()

    def parser_callback(self, ast):
        if ast:
            self.ast = ast
            QMessageBox.information(self.mainWin, '提示', '语法分析完成！')
            self.mainWin.parserCheck.setText('已完成')
            self.mainWin.parserCheck.setStyleSheet("color: #00ff00;")
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)

            add_items(self.mainWin.parserTree.invisibleRootItem(), ast)
            self.mainWin.parserTree.expandAll()
        else:
            QMessageBox.warning(self.mainWin, '警告', '语法分析失败！')


    # SECTION: Syntax
    def start_syntax(self):
        if not self.file_path:
            QMessageBox.warning(self.mainWin, '警告', '请先选择文件！')
            return
        if not self.mainWin.scannerCheck.text() == '已完成':
            QMessageBox.warning(self.mainWin, '警告', '请先完成词法分析！')
            return
        if not self.mainWin.parserCheck.text() == '已完成':
            QMessageBox.warning(self.mainWin, '警告', '请先完成语法分析！')
            return
        self.mainWin.startScannerBtn.setEnabled(False)
        self.mainWin.startParserBtn.setEnabled(False)
        self.mainWin.startSyntaxBtn.setEnabled(False)

        self.syntaxThread = SyntaxThread(self.ast)
        self.syntaxThread.syntaxSignal.connect(self.syntax_callback)
        self.syntaxThread.start()

    def syntax_callback(self, questions):
        if questions:
            QMessageBox.information(self.mainWin, '提示', '语义分析完成！')
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)

            self.mainWin.updateSyntaxTable(questions)
        else:
            QMessageBox.warning(self.mainWin, '警告', '语义分析失败！')


    def write_syntax2db(self, syntaxTbl):
        if self.database:
            for row in syntaxTbl:
                self.database.add_question(*row[1:])
        else:
            QMessageBox.warning(self.mainWin, '警告', '请先链接至数据库！')

    # SECTION: Question

    def download_exam(self):
        download_path = filename, _ = QFileDialog.getSaveFileName(None, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if download_path:
            pass
        else:
            QMessageBox.warning(self.mainWin, '警告', '非法保存路径！')


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

#将Parser结果转为树形结构
def add_items(parent, elements):#递归添加子项
    if isinstance(elements, dict):
        for key, value in elements.items():
            item = QTreeWidgetItem()
            item.setText(0, f"{key}")
            parent.addChild(item)
            if isinstance(value, dict) or isinstance(value, list):
                add_items(item, value)
            else:
                item.setText(1, f"{value}")
    elif isinstance(elements, list):
        for subvalue in elements:
            add_items(parent, subvalue)

if __name__ == '__main__':
    app = QApplication([])
    client = Client()
    client.mainWin.show()
    sys.exit(app.exec())
