from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import sys
import json

sys.path.append('frontend')
sys.path.append('backend')
from frontend.windows import *
import time
import math
import datetime
import io
from backend.ConnDB import Database
from backend.examSP import ExamScanner, ExamParser, extract_questions

class ScannerThread(QThread): # 词法分析线程
    scannerSignal = pyqtSignal(list)
    scannerErrorSignal = pyqtSignal(str)
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
            self.scannerErrorSignal.emit(str(e))
            self.scannerSignal.emit([])


class ParserThread(QThread): # 语法分析线程
    parserSignal = pyqtSignal(dict)
    processSignal = pyqtSignal(str)
    parserErrorSignal = pyqtSignal(str)
    def __init__(self, file_path, parent=None):
        super(ParserThread, self).__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            parser = ExamParser(self.file_path)
            result, process_output = parser.parse()

            self.parserSignal.emit(result)
            self.processSignal.emit(process_output)
        except Exception as e:
            print(e)
            self.parserErrorSignal.emit(str(e))
            self.parserSignal.emit({})

class SyntaxThread(QThread): # 语义分析线程
    syntaxSignal = pyqtSignal(list)
    syntaxErrorSignal = pyqtSignal(str)
    def __init__(self, ast, parent=None):
        super(SyntaxThread, self).__init__(parent)
        self.ast = ast

    def run(self):
        try:
            questions = extract_questions(self.ast, self.ast.get('title'))
            self.syntaxSignal.emit(questions)
        except Exception as e:
            print(e)
            self.syntaxErrorSignal.emit(str(e))
            self.syntaxSignal.emit([])




class Client:
    def __init__(self):
        self.mainWin = MainWin()
        self.fileView = FileView()
        self.processView = ProcessView()

        self.file_load_path = None
        self.file_save_path = None
        self.file_modified = False

        self.ast = None
        self.syntaxTbl = None
        self.process_output = None

        self.database = None
        self.init_signal_slots()

        self.question_search_keys = self.mainWin.getQuestionSearchKey()

        self.create_connection()

        self.scannerThread = None



    def init_signal_slots(self): # 初始化信号槽

        self.mainWin.pageSignal.connect(self.turn_page)
        self.mainWin.logoutBtn.clicked.connect(self.log_out)
        self.mainWin.searchQuestionBtn.clicked.connect(self.search_question)

        self.mainWin.uploadBtn.clicked.connect(self.uploadFile)
        self.mainWin.makeExam.clicked.connect(self.download_exam)

        self.mainWin.startScannerBtn.clicked.connect(self.start_scanner)
        self.mainWin.startParserBtn.clicked.connect(self.start_parser)
        self.mainWin.startSyntaxBtn.clicked.connect(self.start_syntax)
        self.mainWin.addQuestionBtn.clicked.connect(self.write_syntax2db)

        self.mainWin.viewBtn.clicked.connect(self.view_file)
        self.mainWin.viewBtn_2.clicked.connect(self.view_file)
        self.mainWin.viewBtn_3.clicked.connect(self.view_file)

        self.mainWin.parserProcessViewBtn.clicked.connect(self.view_process)

        self.mainWin.saveScanResultBtn.clicked.connect(self.save_scanner_result)
        self.mainWin.saveParserTreeBtn.clicked.connect(self.save_parser_tree)
        self.mainWin.saveQuestionBtn.clicked.connect(self.save_question)

    def create_connection(self): # 创建数据库连接
        self.database = Database()
        self.database.create_connection('backend/test.db')


    def log_out(self): # 退出
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


    def update_question_table(self, keys, page_num=1): # 更新题目表
        if self.database:
            offset = (page_num - 1) * 20
            table = self.database.search_question(*keys, limit=20, offset=offset)
            if table:
                self.mainWin.updateQuestionTable(table)
        else:
            QMessageBox.warning(self.mainWin, '警告', '请先链接至数据库！')

    def search_question(self): # 搜索题目
        # id, content, origin, type, answer
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

    # SECTION: 查看/编辑文件

    def view_file(self): # 查看文件
        if self.file_load_path:
            self.fileView.uploadDisplay.setText(self.file_load_path)
            self.fileView.filepath = self.file_load_path
            self.fileView.fileBrowser.clear()
            with open(self.file_load_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.fileView.fileBrowser.setText(content)
            self.file_modified = self.fileView.exec()
            if self.file_modified:# 如果文件被修改则需要重新扫描
                self.mainWin.scannerCheck.setText('未完成')
                self.mainWin.scannerCheck.setStyleSheet("color: #ff0000;")
                self.mainWin.scannerCheck_2.setText('未完成')
                self.mainWin.scannerCheck_2.setStyleSheet("color: #ff0000;")
                self.mainWin.parserCheck.setText('未完成')
                self.mainWin.parserCheck.setStyleSheet("color: #ff0000;")
        else:
            QMessageBox.warning(self.mainWin, '警告', '请先上传文件！')

    # SECTION: Scanner

    def uploadFile(self): # 上传文件
        self.file_load_path, _ = QFileDialog.getOpenFileName(self.mainWin, '选择文件', '', '*.txt;;*.doc;;*.docx;;*.pdf;;All Files (*)')
        if self.file_load_path:
            self.mainWin.uploadDisplay.setText(self.file_load_path)
            self.mainWin.uploadDisplay_2.setText(self.file_load_path)
            self.mainWin.uploadDisplay_3.setText(self.file_load_path)
            self.mainWin.scannerCheck.setText('未完成')
            self.mainWin.scannerCheck.setStyleSheet("color: #ff0000;")
            self.mainWin.scannerCheck_2.setText('未完成')
            self.mainWin.scannerCheck_2.setStyleSheet("color: #ff0000;")
            self.mainWin.parserCheck.setText('未完成')
            self.mainWin.parserCheck.setStyleSheet("color: #ff0000;")

    def start_scanner(self): # 词法分析
        if not self.file_load_path:
            QMessageBox.warning(self.mainWin, '警告', '请先选择文件！')
            return
        self.mainWin.startScannerBtn.setEnabled(False)
        self.mainWin.startParserBtn.setEnabled(False)
        self.mainWin.startSyntaxBtn.setEnabled(False)

        self.scannerThread = ScannerThread(self.file_load_path)
        self.scannerThread.scannerSignal.connect(self.scanner_callback)
        self.scannerThread.scannerErrorSignal.connect(self.scanner_error_callback)
        self.scannerThread.start()

    def scanner_callback(self, result): # 词法分析回调
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
            self.mainWin.saveScanResultBtn.setEnabled(True)
            #更新词法分析结果
            self.mainWin.lexemeTbl.clearContents()
            self.mainWin.updateLexemeTable(result)

            self.fileView.modified = False # 词法分析完成后将文件修改标志置为False
        else:
            QMessageBox.warning(self.mainWin, '警告', '词法分析失败！')
            self.mainWin.lexemeTbl.clearContents()
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)
            self.mainWin.saveScanResultBtn.setEnabled(False)

    def scanner_error_callback(self, error): # 词法分析错误回调
        QMessageBox.warning(self.mainWin, '警告', "词法分析错误！\n 非法字符：\n" + error +
                            '\n请检查文件是否符合规范！' +
                            '正确格式如下：\n' +
                            '1. 试卷标题要以XXXX年开头，“试卷”结尾\n' +
                            '2. 题目要以“（题号）.”开头，以[。.?？]中的一个结尾\n' +
                            '3. 选项要以[a-zA-Z].开头\n' +
                            '4. 答案要以“答案[:：]”开头\n' +
                            '5. 题型形如“一、XX题[:：]”')

    def save_scanner_result(self): # 保存词法分析结果
        QUESTIONS = []
        QUESTION_HEADERS = []
        HEADERS = []
        ANSWERS = []
        OPTIONS = []
        if self.mainWin.scannerCheck.text() == '已完成':
            self.file_save_path, _ = QFileDialog.getSaveFileName(self.mainWin, '保存词法分析结果', '', '*.txt;;All Files (*)')
            if self.file_save_path:
                with open(self.file_save_path, 'w', encoding='utf-8') as f:
                    f.write('——————————————单词串——————————————\n')
                    for i in range(self.mainWin.lexemeTbl.rowCount()):
                        if self.mainWin.lexemeTbl.item(i, 1).text() == 'QUESTION':
                            QUESTIONS.append("["+str(i)+"]"+self.mainWin.lexemeTbl.item(i, 0).text())
                        elif self.mainWin.lexemeTbl.item(i, 1).text() == 'QUESTIONHEADER':
                            QUESTION_HEADERS.append("["+str(i)+"]"+self.mainWin.lexemeTbl.item(i, 0).text())
                        elif self.mainWin.lexemeTbl.item(i, 1).text() == 'HEADER':
                            HEADERS.append("["+str(i)+"]"+self.mainWin.lexemeTbl.item(i, 0).text())
                        elif self.mainWin.lexemeTbl.item(i, 1).text() == 'ANSWER':
                            ANSWERS.append("["+str(i)+"]"+self.mainWin.lexemeTbl.item(i, 0).text())
                        elif self.mainWin.lexemeTbl.item(i, 1).text() == 'OPTION':
                            OPTIONS.append("["+str(i)+"]"+self.mainWin.lexemeTbl.item(i, 0).text())
                        f.write("["+str(i)+"]"+self.mainWin.lexemeTbl.item(i, 0).text() + '\n')
                    f.write('——————————————单词表——————————————\n')

                    f.write('试卷头HEADER：\n\n')
                    for i in HEADERS:
                        f.write(i + '\n')
                    f.write('\n')

                    f.write('题型头QUESTIONHEADER：\n\n')
                    for i in QUESTION_HEADERS:
                        f.write(i + '\n')
                    f.write('\n')

                    f.write('题目QUESTION：\n\n')
                    for i in QUESTIONS:
                        f.write(i + '\n')
                    f.write('\n')

                    f.write('选项OPTION：\n\n')
                    for i in OPTIONS:
                        f.write(i + '\n')
                    f.write('\n')

                    f.write('答案ANSWER：\n\n')
                    for i in ANSWERS:
                        f.write(i + '\n')
                    f.write('\n')
                QMessageBox.information(self.mainWin, '提示', '保存成功！')
            else:
                QMessageBox.warning(self.mainWin, '警告', '非法保存路径！')
        else:
            QMessageBox.warning(self.mainWin, '警告', '请先完成词法分析！')

    # SECTION: Parser

    def start_parser(self): # 语法分析
        if not self.file_load_path:
            QMessageBox.warning(self.mainWin, '警告', '请先选择文件！')
            return
        if not self.mainWin.scannerCheck.text() == '已完成':
            QMessageBox.warning(self.mainWin, '警告', '请先完成词法分析！')
            return
        self.mainWin.startScannerBtn.setEnabled(False)
        self.mainWin.startParserBtn.setEnabled(False)
        self.mainWin.startSyntaxBtn.setEnabled(False)

        self.parserThread = ParserThread(self.file_load_path)
        self.parserThread.parserSignal.connect(self.parser_callback)
        self.parserThread.processSignal.connect(self.process_callback)
        self.parserThread.parserErrorSignal.connect(self.parser_error_callback)
        self.parserThread.start()

    def parser_callback(self, ast): # 语法分析回调
        if ast:
            self.ast = ast
            QMessageBox.information(self.mainWin, '提示', '语法分析完成！')
            self.mainWin.parserCheck.setText('已完成')
            self.mainWin.parserCheck.setStyleSheet("color: #00ff00;")
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)
            self.mainWin.saveParserTreeBtn.setEnabled(True)
            #更新语法分析结果
            self.mainWin.parserTree.clear()
            add_items(self.mainWin.parserTree.invisibleRootItem(), ast)
            self.mainWin.parserTree.expandAll()

            self.fileView.modified = False # 语法分析完成后将文件修改标志置为False
        else:
            QMessageBox.warning(self.mainWin, '警告', '语法分析失败！')
            self.mainWin.parserTree.clear()
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)
            self.mainWin.saveParserTreeBtn.setEnabled(False)

    def process_callback(self, process): # 语法分析过程回调
        self.mainWin.parserProcessViewBtn.setEnabled(True)
        self.process_output = process

    def parser_error_callback(self, error): # 语法分析错误回调
        QMessageBox.warning(self.mainWin, '警告', "语法分析错误！\n 非法的语法结构：\n" + error +
                            '\n请检查文件是否符合规范！')

    def save_parser_tree(self): # 保存语法分析结果
        if self.mainWin.parserCheck.text() == '已完成':
            self.file_save_path, _ = QFileDialog.getSaveFileName(self.mainWin, '保存语法分析结果', '', '*.txt;;All Files (*)')
            if self.file_save_path:
                with open(self.file_save_path, 'w', encoding='utf-8') as f:
                    tree_text = ""
                    root = self.mainWin.parserTree.invisibleRootItem()
                    for i in range(root.childCount()):
                        tree_text += traverse_tree(root.child(i))
                    f.write(tree_text)
                QMessageBox.information(self.mainWin, '提示', '保存成功！')
            else:
                QMessageBox.warning(self.mainWin, '警告', '非法保存路径！')
        else:
            QMessageBox.warning(self.mainWin, '警告', '请先完成语法分析！')

    def view_process(self): # 查看语法分析过程
        if self.process_output:
            self.mainWin.parserProcessViewBtn.setEnabled(True)
            self.processView.processBrowser.clear()
            self.processView.processBrowser.setText(self.process_output)
            self.processView.exec()
        else:
            QMessageBox.warning(self.mainWin, '警告', '导出语法分析过程失败！')



    # SECTION: Syntax
    def start_syntax(self): # 开始语义分析
        if not self.file_load_path:
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
        self.syntaxThread.syntaxErrorSignal.connect(self.syntax_error_callback)
        self.syntaxThread.start()

    def syntax_callback(self, questions): # 语义分析回调函数
        if questions:
            QMessageBox.information(self.mainWin, '提示', '语义分析完成！')
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)
            self.mainWin.addQuestionBtn.setEnabled(True)
            self.mainWin.saveQuestionBtn.setEnabled(True)

            #更新语义分析结果
            self.mainWin.syntaxTbl.clearContents()
            self.mainWin.updateSyntaxTable(questions)
            self.syntaxTbl = questions

            self.fileView.modified = False # 语义分析完成后将文件修改标志置为False
        else:
            QMessageBox.warning(self.mainWin, '警告', '语义分析失败！')
            self.mainWin.syntaxTbl.clearContents()
            self.mainWin.startScannerBtn.setEnabled(True)
            self.mainWin.startParserBtn.setEnabled(True)
            self.mainWin.startSyntaxBtn.setEnabled(True)
            self.mainWin.addQuestionBtn.setEnabled(False)
            self.mainWin.saveQuestionBtn.setEnabled(False)

    def syntax_error_callback(self, error): # 语义分析错误回调
        QMessageBox.warning(self.mainWin, '警告', error)

    def write_syntax2db(self): # 将语义分析结果写入数据库
        try:
            if self.database:
                for row in self.syntaxTbl:
                    self.database.add_question(*row[1:])
                QMessageBox.information(self.mainWin, '提示', '语义分析结果写入数据库成功！')
            else:
                QMessageBox.warning(self.mainWin, '警告', '请先链接至数据库！')
        except Exception as e:
            QMessageBox.warning(self.mainWin, '警告', '语义分析结果写入数据库失败！')

    def save_question(self): # 保存语义分析结果
        self.file_save_path, _ = QFileDialog.getSaveFileName(self.mainWin, '保存语义分析结果', '', '*.txt;;All Files (*)')
        if self.file_save_path:
            with open(self.file_save_path, 'w', encoding='utf-8') as f:
                for row in self.syntaxTbl:
                    f.write(row[0] + '\t' + row[1] + '\t' + row[2] + '\t' + row[3] + '\t' + row[4] + '\n')
            QMessageBox.information(self.mainWin, '提示', '保存成功！')
        else:
            QMessageBox.warning(self.mainWin, '警告', '非法保存路径！')

    # SECTION: Question

    def download_exam(self):
        download_path, _ = QFileDialog.getSaveFileName(None, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if download_path:
            # 创建分类存储
            choice_questions = []
            judgment_questions = []
            fill_questions = []
            #数字到中文序号的映射
            num2chn = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五'}
            with open(download_path, 'w', encoding='utf-8') as f:
                selected_rows = set(index.row() for index in self.mainWin.questionTbl.selectedIndexes())
                for row in selected_rows:
                    question_content_item = self.mainWin.questionTbl.item(row, 1)
                    question_type_item = self.mainWin.questionTbl.item(row, 3)
                    answer_item = self.mainWin.questionTbl.item(row, 4)
                    if question_type_item.text() == '选择题': # 选中题目中的选择题
                        choice_questions.append((question_content_item.text(), answer_item.text()))
                    elif question_type_item.text() == '判断题': # 选中题目中的判断题
                        judgment_questions.append((question_content_item.text(), answer_item.text()))
                    elif question_type_item.text() == '填空题': # 选中题目中的填空题
                        fill_questions.append((question_content_item.text(), answer_item.text()))
                    else:
                        QMessageBox.warning(self.mainWin, '警告', '未知题型！')
                f.write('{}年xxx考试试卷\n'.format(time.strftime("%Y", time.localtime()))) # 年份
                cur_question_header = 1
                cur_question_num = 1
                if choice_questions: # 选择题部分
                    f.write('{}、选择题:\n'.format(num2chn[cur_question_header]))
                    for i, question in enumerate(choice_questions):
                        f.write(str(cur_question_num) + '.' + question[0] + ' ')
                        f.write('答案：' + question[1] + '\n')
                        cur_question_num += 1
                    cur_question_header += 1
                if judgment_questions: # 判断题部分
                    f.write('{}、判断题:\n'.format(num2chn[cur_question_header]))
                    for i, question in enumerate(judgment_questions):
                        f.write(str(cur_question_num) + '.' + question[0] + ' ')
                        f.write('答案：' + question[1] + '\n')
                        cur_question_num += 1
                    cur_question_header += 1
                if fill_questions: # 填空题部分
                    f.write('{}、填空题:\n'.format(num2chn[cur_question_header]))
                    for i, question in enumerate(fill_questions):
                        f.write(str(cur_question_num) + '.' + question[0] + ' ')
                        f.write('答案：' + question[1] + '\n')
                        cur_question_num += 1
                    cur_question_header += 1
                QMessageBox.information(self.mainWin, '提示', '试卷创建成功！')
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

        if type == 'question':
            self.mainWin.questionPage.setText('{} / {}'.format(cur_page, total_page)) # 更新页码
            self.update_question_table(keys=self.question_search_keys, page_num=int(cur_page)) # 更新表格
        else:
            QMessageBox.critical(self.mainWin, '错误', '未知数据类型！')
            return

#深度优先遍历树形结构
def traverse_tree(item, depth=0):
    result = '\t' * depth + item.text(0) + ' ' + item.text(1) + '\n'
    for i in range(item.childCount()):
        result += traverse_tree(item.child(i), depth + 1)
    return result

#将Parser结果转为树形结构
def add_items(parent, elements):#递归添加子项
    if isinstance(elements, dict):
        def _additem(key,value):
            item = QTreeWidgetItem()
            item.setText(0, f"{key}")
            parent.addChild(item)
            if isinstance(value, dict) or isinstance(value, list):
                add_items(item, value)
            else:
                item.setText(1, f"{value}")

        if 'type' in elements and 'title' in elements:
            _additem(elements['type'],elements['title'])
        
        if 'type' in elements and 'content' in elements:
            _additem(elements['type'],elements['content'])

        for key, value in elements.items():
            if key != 'type' and key != 'content' and key != 'title':
                _additem(key, value)
            
    elif isinstance(elements, list):
        for subvalue in elements:
            add_items(parent, subvalue)

if __name__ == '__main__':
    app = QApplication([])
    client = Client()
    client.mainWin.show()
    sys.exit(app.exec())
