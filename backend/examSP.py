import re
import io
import sys

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
    best_match = None
    best_length = 0
    for token_name in tokens:
        rule = globals()[f"t_{token_name}"]
        match = re.match(rule, t.lexer.lexdata[t.lexpos:])
        if match and len(match.group(0)) > best_length:
            best_match = token_name
            best_length = len(match.group(0))
    start = max(0, t.lexer.lexpos - 5)  # 从错误位置往前取20个字符
    end = t.lexer.lexpos + 5  # 从错误位置往后取20个字符
    context = t.lexer.lexdata[start:end].replace('\n', '')
    if best_match is None:
        print("Illegal character '%s' at position %s" % (t.value[0], t.lexpos))
    else:
        print("Illegal character '%s' at position %s, did you mean '%s'?" % (t.value[0], t.lexpos, best_match))
    print("Context: %s" % context)
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

    def parse(self, raw=False):
        with open(self.filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        # 创建一个StringIO对象用于接收输出
        process_output = io.StringIO()
        # 保存当前的stdout，然后将stdout重定向到StringIO对象
        old_stdout = sys.stderr
        sys.stderr = process_output
        if raw:
            result = parser.parse(content)
            # 恢复原来的stdout
            sys.stderr = old_stdout
            return result, process_output.getvalue()
        else:
            result = parser.parse(content, debug=True)
            # 恢复原来的stdout
            sys.stderr = old_stdout
            return parse_ast(result), process_output.getvalue()

def parse_ast(node): # 将AST转为字典
    if not isinstance(node, tuple):
        return node
    if node[0] == 'paper':
        return {
            'type': 'paper',
            'title': node[1],
            'content': parse_ast(node[2])
        }
    elif node[0] == 'questionheaders':
        return [parse_ast(child) for child in node[1:]]
    elif node[0] == 'questionheader':
        return {
            'type': 'questionheader',
            'title': node[1],
            'questions': parse_ast(node[2])
        }
    elif node[0] == 'questions':
        return [parse_ast(child) for child in node[1:]]
    elif node[0] == 'question':
        content = node[1]
        answer = parse_ast(node[2])
        # Check if the next node is 'options'
        if len(node) > 3 and node[2][0] == 'options':
            options = parse_ast(node[2])
            answer = parse_ast(node[3])
            # Append options to the question content
            content += ' ' + ' '.join(options['choices'])
        return {
            'type': 'question',
            'content': content,
            'answer': answer
        }
    elif node[0] == 'answer':
        return {
            'type': 'answer',
            'content': node[1]
        }
    elif node[0] == 'options':
        return {
            'type': 'options',
            'choices': filter(lambda x: x != 'options', node[1:])
        }
    else:
        return node

def extract_questions(elements, paper_title, question_type=None): # 从AST中提取题目
    questions = []
    if isinstance(elements, dict):
        for key, value in elements.items():
            if key == "type" and value == "question":  # 找到题目的字典
                question_content = elements.get("content")[2:] # 删去题目前面的编号
                question_answer = elements.get("answer").get("content")[3:] # 删去答案前面的“答案：”
                question_type = question_type
                question_number = elements.get("content").split(".")[0] if "content" in elements else None
                questions.append([question_number, question_content, paper_title, question_type, question_answer])
            if key == "type" and value == "questionheader":  # 找到题型的字典
                question_type = elements.get("title").split("、")[-1][:-1] # 掐头去尾只留下题型
            elif isinstance(value, dict) or isinstance(value, list):
                questions.extend(extract_questions(value, paper_title, question_type)) # 递归遍历子字典或列表
    elif isinstance(elements, list):
        for subvalue in elements:
            questions.extend(extract_questions(subvalue, paper_title, question_type)) # 递归遍历子字典或列表
    return questions



if __name__ == "__main__":
    # scanner = ExamScanner('../test/maked.txt')
    # result = scanner.scan()
    e_parser = ExamParser('../test/test.txt')
    result = e_parser.parse()
    questions = extract_questions(result,result.get('title'))
    print(result)
    print(questions)
