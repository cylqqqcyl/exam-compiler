from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys

from mainWin import Ui_MainWindow
class MainWin(QMainWindow, Ui_MainWindow):
    pageSignal = pyqtSignal(list)

    def __init__(self):
        super(MainWin, self).__init__()

        self.setupUi(self)

        self.stackedWidget.setCurrentIndex(0)

        self.close_flag = True

        self.questionTbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.questionTbl.setColumnHidden(0, True)


        self.initSignalSlots()

    def initSignalSlots(self):
        self.toHomeBtn.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))
        self.toScannerBtn.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(2))
        self.toParserBtn.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(3))
        self.toSyntaxBtn.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(4))
        self.toAboutBtn.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(5))
        self.questionBtn.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(1))
        self.paperBtn.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(2))

        self.questionFirstBtn.clicked.connect(lambda: self.firstPage('question'))
        self.questionPreBtn.clicked.connect(lambda: self.prePage('question'))
        self.questionNextBtn.clicked.connect(lambda: self.nextPage('question'))
        self.questionLastBtn.clicked.connect(lambda: self.lastPage('question'))
        self.questionJumpBtn.clicked.connect(lambda: self.jumpPage('question'))

        self.uploadBtn.clicked.connect(self.uploadFile)


        self.questionPage.setText('1 / 10')  # debug use

    def showInfo(self, msg):
        QMessageBox.information(self, '提示', msg)

    def showWarning(self, msg):
        QMessageBox.warning(self, '警告', msg)

    def showError(self, msg):
        QMessageBox.critical(self, '错误', msg)

    # SECTION: Question Page
    def getQuestionSearchKey(self):
        subject = self.searchQuestionSubjectEdit.text()
        year = self.searchQuestionYearEdit.text()
        type = self.searchQuestionTypeEdit.text()

        return subject, year, type

    def getSelectedQuestionInfo(self):
        row = self.questionTbl.currentRow()

        id = self.questionTbl.item(row, 0).text()  # primary key, hidden
        content = self.questionTbl.item(row, 1).text()  # 题目
        subject = self.questionTbl.item(row, 2).text()  # 科目
        year = self.questionTbl.item(row, 3).text()  # 年份
        type = self.questionTbl.item(row, 4).text()  # 类型
        answer = self.questionTbl.item(row, 5).text()  # 答案

        return id, content, subject, year, type, answer

    def showQuestionNum(self, num):
        if num:
            self.questionNumLbl.setText(f'查询结果：共{num}条数据')
        else:
            self.questionNumLbl.setText(f'查询结果：共0条数据')

    def showQuestionTime(self, time):
        text = self.questionNumLbl.text()
        if time:
            self.questionNumLbl.setText(text + f'; 搜索用时：{time}毫秒')
        else:
            self.questionNumLbl.setText(text + f'; 搜索用时：0.000毫秒')

    def updateQuestionTable(self, table):
        assert table is not None
        self.questionTbl.setRowCount(0)
        self.questionTbl.clearContents()
        try:
            for i, row in enumerate(table):
                # id, name, author, press, release_date, ISBN, stock
                self.questionTbl.insertRow(i)
                self.questionTbl.setItem(i, 0, QTableWidgetItem(str(row[0])))
                self.questionTbl.setItem(i, 1, QTableWidgetItem(row[1]))
                self.questionTbl.setItem(i, 2, QTableWidgetItem(row[2]))
                self.questionTbl.setItem(i, 3, QTableWidgetItem(row[3]))
                self.questionTbl.setItem(i, 4, QTableWidgetItem(str(row[4])))
                self.questionTbl.setItem(i, 5, QTableWidgetItem(row[5]))
                self.questionTbl.setItem(i, 6, QTableWidgetItem(str(row[6])))
        except Exception as e:
            print(e)

    # SECTION: Scanner Page
    def uploadFile(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '选择文件', '', '*.txt;;*.doc;;*.docx;;*.pdf;;All Files (*)')
        if file_path:
            self.uploadDisplay.setText(file_path)

    # SECTION: 翻页
    def firstPage(self, type):
        self.pageSignal.emit([type, 'first', self.curPage(type)])

    def lastPage(self, type):
        self.pageSignal.emit([type, 'last', self.curPage(type)])

    def prePage(self, type):
        self.pageSignal.emit([type, 'pre', self.curPage(type)])

    def nextPage(self, type):
        self.pageSignal.emit([type, 'next', self.curPage(type)])

    def jumpPage(self, type):
        self.pageSignal.emit([type, 'jump', self.targetPage(type)])

    def curPage(self, type):
        # text的格式为 'cur_page / total_page'
        if type == 'question':
            text = self.questionPage.text()
        else:
            QMessageBox.critical(self, '错误', '未知数据类型！')
            return

        cur_page = int(text.split('/')[0].strip(' '))
        return cur_page

    def totalPage(self, type):
        if type == 'question':
            text = self.questionPage.text()
        else:
            QMessageBox.critical(self, '错误', '未知数据类型！')
            return

        total_page = int(text.split('/')[1].strip(' '))
        return total_page

    def setTotalPage(self, type, total_page):
        if type == 'question':
            self.questionPage.setText('1 / {}'.format(total_page))
        else:
            QMessageBox.critical(self, '错误', '未知数据类型！')
            return

    def targetPage(self, type):
        if type == 'question':
            text = self.questionJumpEdit.text()
        else:
            QMessageBox.critical(self, '错误', '未知数据类型！')
            return
        try:
            target_page = int(text)
        except:
            return -1  # 输入了非法页码

        return target_page

    def closeEvent(self, e):
        if self.close_flag:
            reply = QMessageBox.question(self,
                                         '询问',
                                         "确定要退出吗？",
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            if reply == QMessageBox.Yes:
                e.accept()
                sys.exit(0)
            else:
                e.ignore()
        else:
            self.close()



