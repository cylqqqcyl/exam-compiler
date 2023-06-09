import re
import ply.lex as lex

tokens = (
    'QUESTION',
    'OPTION',
    'ANSWER',
    'HEADER',
    'QUESTIONHEADER',
)

# 定义每种单词类型的匹配规则
t_QUESTION = r'\n*\d+\. .*?[.。？?！!]'
t_OPTION = r'[a-zA-Z]{1}\.\w+\ *'
t_ANSWER = r'答案[:：].*'
t_HEADER = r'\d{4}年 .*?试卷'
t_QUESTIONHEADER = r'[一二三四五六七八九十]、.{2}题[:：]'

# 忽略空白和换行符
t_ignore = ' \t\n'

def t_error(t):
    # 报错
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex()

class Scanner:
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

if __name__ == "__main__":
    scanner = Scanner('../test/test.txt')
    result = scanner.scan()
    print(result)
    print(type(result))
