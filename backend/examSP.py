import re

#################### 词法分析器 ####################
tokens = (
    'QUESTION',
    'OPTION',
    'ANSWER',
    'HEADER',
    'QUESTIONHEADER',
)

# 定义每种单词类型的匹配规则
t_QUESTION = r'\n*\d+\. .*?[.。？?！!]' #题目
t_OPTION = r'[a-zA-Z]{1}\.\w+\ *' #选项
t_ANSWER = r'答案[:：].*' #答案
t_HEADER = r'\d{4}年 .*?试卷' #试卷头
t_QUESTIONHEADER = r'[一二三四五六七八九十]、.{2}题[:：]' #题型号

# 忽略空白和换行符
t_ignore = ' \t\n'

def t_error(t):
    # 报错
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

#build the lexer
import ply.lex as lex
lexer = lex.lex()
#################### 词法分析器 ####################

#################### 语法分析器 ####################
def p_paper(p):
    'paper : HEADER questionheaders'
    p[0] = ('paper', p[1], p[2])

def p_questionheaders(p): # 题型列表
    '''questionheaders : questionheader questionheaders
                        | questionheader'''
    if len(p) > 2:
        p[0] = ('questionheaders', p[1]) + p[2]
    else:
        p[0] = ('questionheaders', p[1])

def p_questionheader(p): #题型
    '''questionheader : QUESTIONHEADER questions'''
    p[0] = ('questionheader', p[1], p[2])

def p_questions(p): #题目列表
    '''questions : question questions
                    | question'''
    if len(p) > 2:
        p[0] = ('questions', p[1]) + p[2]
    else:
        p[0] = ('questions', p[1])

def p_question(p): #题型
    '''question : QUESTION
                    | QUESTION options
                    | QUESTION answer
                    | QUESTION options answer'''
    if len(p) > 3:
        p[0] = ('question', p[1], p[2], p[3])
    elif len(p) > 2:
        p[0] = ('question', p[1], p[2])
    else:
        p[0] = ('question', p[1])

def p_answer(p): #答案
    '''answer : ANSWER'''
    if len(p) > 1:
        p[0] = ('answer', p[1])
    else:
        p[0] = ('answer', '')


def p_options(p): #选项
    '''options : OPTION options
               | OPTION'''
    if len(p) > 2:
        p[0] = ('options', p[1]) + p[2]
    else:
        p[0] = ('options', p[1])

def p_error(p):
    print("Syntax error in {}".format(p))

# 构建解析器
import ply.yacc as yacc
parser = yacc.yacc()
#################### 语法分析器 ####################

class ExamScanner:
    def __init__(self, filepath):
        self.filepath = filepath

    def scan(self):
        with open(self.filepath, 'r', encoding='utf-8') as file:
            content = file.read()

        lexer.input(content)
        tokens = []
        while True:
            # 读取一个token
            tok = lexer.token()
            if not tok:
                break
            tokens.append((tok.value, tok.type))
        # 返回token列表
        return tokens

class ExamParser:
    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self):
        with open(self.filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        return parser.parse(content)


if __name__ == "__main__":
    # scanner = ExamScanner('../test/test.txt')
    # result = scanner.scan()
    e_parser = ExamParser('../test/test.txt')
    result = e_parser.parse()
    print(result)
    print(type(result))
