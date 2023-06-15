import re
import io
import sys

#################### 词法分析器 ####################

tokens = ( # 单词类型对应的token列表，提供给词法分析器
    'QUESTION',
    'OPTION',
    'ANSWER',
    'HEADER',
    'QUESTIONHEADER',
)

# 定义每种单词类型的匹配规则
# 由词法分析器通过反射的形式调用
# 这里的单词不需要复杂的处理动作，所以直接给出其正则表达式进行匹配即可
# 需要复杂处理动作的单词将在后面出现
t_QUESTION = r'\n*\d+\. .*?[.。？?！!]' #题目
t_OPTION = r'[a-zA-Z]{1}\.\w+\ *' #选项
t_ANSWER = r'答案[:：].*' #答案
t_HEADER = r'\d{4}年 .*?试卷' #试卷头
t_QUESTIONHEADER = r'[一二三四五六七八九十]、.{2}题[:：]' #题型号

# 忽略空格和制表符
t_ignore = ' \t'

# 词法分析的异常类
class LexicalError(Exception):
    def __init__(self, errors):
        error_messages = ["At line %s: Invalid token %s" % (error[0], error[1].replace("\n", "")) for error in errors] 
        self.message = "\n".join(error_messages) # 根据词法错误，生成错误信息，包含行号和对应的错误token

    def __str__(self): # str方法，在输出该类对象时输出错误信息
        return self.message

class ParserError(Exception):
    def __init__(self, error): 
        self.message = error # 语法错误信息

    def __str__(self):
        return self.message # str方法，在输出该类对象时输出错误信息


def init_lexer(lexer):  # 初始化行号
    lexer.lineno = 1


def t_error(t):
    # 报错处理
    match = None
    error_buffer = ""  # 用于记录错误的字符串
    current_pos = t.lexer.lexpos  # 记录当前位置
    while current_pos < len(t.lexer.lexdata):  # 从当前位置开始逐个字符匹配
        for token_name in tokens:
            rule = globals()[f"t_{token_name}"]  # 获取对应的匹配规则
            match = re.match(rule, t.lexer.lexdata[current_pos:])  # 匹配成功则跳出循环
            if match:
                break
        if match:
            t.lexer.skip(len(error_buffer))  # 跳过错误的字符
            break
        else:
            error_buffer += t.lexer.lexdata[current_pos]  # 记录错误的字符
            current_pos += 1  # 继续匹配下一个字符
    if not hasattr(t.lexer, 'errors'):  # 如果没有错误列表则创建
        t.lexer.errors = []
        t.lexer.errors.append([t.lexer.lineno, error_buffer])
    else:  # 如果有错误列表则添加
        t.lexer.errors.append([t.lexer.lineno, error_buffer])

# 需要复杂处理动作的单词的例子
def t_newline(t): # 记录行号
    r'\n+' # 字符串表示匹配的模式
    t.lexer.lineno += len(t.value) # 动作是在匹配到换行时将行号增加，实现对行号的记录


# build the lexer
import ply.lex as lex
lexer = lex.lex() # 实例化lex对象，在之后调用进行词法分析
#################### 词法分析器 ####################

#################### 语法分析器 ####################

# ply对yacc进行了封装
# 每一个非终结符号的分析过程被表示成一个python函数
# 以p_<符号名>作为函数名
# 函数名下方的字符串表示一组产生式规则
# 函数内的语句表示一组相关动作
# 这样的模式固然便利代码的编写，但也存在一些问题
# 问题在于产生式的获取需要依赖解释器的调试信息，这使得ply的第一次执行必须在调试模式下
# 才能正确生成解释器，当然，只需要生成一次即可

# 由于我们程序的主要目的是解析试卷，产生试卷结构，将题目结构解析
# 分析其类型并写入数据库中，最后用于组卷输出
# 故语法的主要动作为对非终结符产生对应的树节点类型和树结构
# 提供给后续的语义分析和展示模块

def p_paper(p): # 解析试卷
    'paper : HEADER questionheaders'
    p[0] = ('paper', p[1], p[2]) 
    # 树结构，第一个元素为节点类型标记
    # 第二个元素是HEADER节点
    # 第三个元素是questionheaders节点


def p_questionheaders(p):  # 题型列表
    '''questionheaders : questionheader questionheaders
                        | questionheader'''
    if len(p) > 2: # 当len大于2时，是questionheaders : questionheader questionheaders
        # 因此将第一个元素questionheader的树结构解析完成后
        # 在后面直接拼接第二个questionheaders的解析内容
        p[0] = ('questionheaders', p[1]) + p[2]
    else:
        # 此时没有第二个问题，故直接产生树结构
        p[0] = ('questionheaders', p[1])


def p_questionheader(p):  # 题型
    '''questionheader : QUESTIONHEADER questions'''
    p[0] = ('questionheader', p[1], p[2])
    # 树结构，第一个元素为节点类型标记
    # 第二个元素是QUESTIONHEADER节点
    # 第三个元素是questions节点


def p_questions(p):  # 题目列表
    '''questions : question questions
                    | question'''
    if len(p) > 2:# 当len大于2时，是questions : question questions
        # 因此将第一个元素question的树结构解析完成后
        # 在后面直接拼接第二个questions的解析内容
        p[0] = ('questions', p[1]) + p[2]
    else:
        # 此时没有第二个问题，故直接产生树结构
        p[0] = ('questions', p[1])


def p_question(p):  # 题型
    '''question : QUESTION
                    | QUESTION options
                    | QUESTION answer
                    | QUESTION options answer'''
    # 判断题目类型
    if len(p) > 3: #len(p)的长度大于三，表示该问题是选择题
        # 产生树结构时将 QUESTION option 插入结构中
        p[0] = ('question', p[1], p[2], p[3])
    elif len(p) > 2: # 表示该问题是填空或判断题
        # 产生树结构时将 QUESTION option 插入结构中
        p[0] = ('question', p[1], p[2])
    else: # 第一个产生式
        p[0] = ('question', p[1])


def p_answer(p):  # 答案
    '''answer : ANSWER'''
    if len(p) > 1: # 答案的树结构
        p[0] = ('answer', p[1])
    else:
        p[0] = ('answer', '')


def p_options(p):  # 选项
    '''options : OPTION options
               | OPTION'''
    if len(p) > 2: # 当len大于2时，是options : OPTION options
        # 因此将第一个元素OPTION的树结构解析完成后
        # 在后面直接拼接第二个options的解析内容
        p[0] = ('options', p[1]) + p[2]
    else:
        # 直接产生option的结构
        p[0] = ('options', p[1])

def p_error(p): # 报错
    # 获取出错位置
    print("Syntax error in {} at line {}".format(p, p.lexer.lineno))
    # 抛出自定义的语法分析异常
    raise ParserError("Syntax error in {} at line {}".format(p, p.lexer.lineno))


# 构建解析器
import ply.yacc as yacc
parser = yacc.yacc() # 实例化yacc对象，在之后调用进行语义分析
#################### 语法分析器 ####################

class ExamScanner:  # 词法分析器
    def __init__(self, filepath):
        self.filepath = filepath # 初始化，指定解析路径

    def scan(self):  # 扫描
        with open(self.filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        lexer.lineno = 1
        lexer.input(content) # 将文件输入词法分析器
        tokens = []
        while True:
            # 读取一个token
            tok = lexer.token() # 该函数每调用一次返回一个token
            if not tok:
                break
            tokens.append((tok.value, tok.type, tok.lineno))
        if hasattr(lexer, 'errors') and lexer.errors: # 出错
            print(tokens)
            errors = lexer.errors
            lexer.errors = []
            raise LexicalError(errors) # 抛出词法分析错误的异常类
        # 返回token列表
        return tokens


class ExamParser:  # 语法分析器
    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self, raw=False):  # 解析
        with open(self.filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        # 创建一个StringIO对象用于接收输出
        process_output = io.StringIO()
        # 保存当前的stdout，然后将stdout重定向到StringIO对象
        old_stdout = sys.stderr
        sys.stderr = process_output

        lexer.lineno = 1  # 初始化行号
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


def parse_ast(node):  # 递归将AST转为字典
    if not isinstance(node, tuple):
        return node
    if node[0] == 'paper': # 试卷类型
        return {
            'type': 'paper',
            'title': node[1],
            'content': parse_ast(node[2]) # 递归解析
        }
    elif node[0] == 'questionheaders': # 解析每一个问题类型
        return [parse_ast(child) for child in node[1:]]
    elif node[0] == 'questionheader': # 解析问题头
        return {
            'type': 'questionheader',
            'title': node[1],
            'questions': parse_ast(node[2]) # 递归解析内容
        }
    elif node[0] == 'questions': # 解析每一个问题
        return [parse_ast(child) for child in node[1:]]
    elif node[0] == 'question': # 解析问题
        content = node[1]
        answer = parse_ast(node[2])
        # Check if the next node is 'options'
        if len(node) > 3 and node[2][0] == 'options': # 选择题
            options = parse_ast(node[2]) # 解析选项
            answer = parse_ast(node[3]) # 解析答案
            # Append options to the question content
            content += ' ' + ' '.join(options['choices']) # 将选项放在题目内容中一并展示
        return {
            'type': 'question',
            'content': content,
            'answer': answer
        }
    elif node[0] == 'answer':
        return {
            'type': 'answer', # 解析答案
            'content': node[1]
        }
    elif node[0] == 'options':
        return {
            'type': 'options',
            'choices': filter(lambda x: x != 'options', node[1:]) # 过滤多余的option字样
        }
    else:
        return node


def extract_questions(elements, paper_title, question_type=None):  # 从AST中提取题目
    questions = []
    if isinstance(elements, dict):
        for key, value in elements.items():
            if key == "type" and value == "question":  # 找到题目的字典
                question_content = elements.get("content")[2:]  # 删去题目前面的编号
                question_answer = elements.get("answer").get("content")[3:]  # 删去答案前面的“答案：”
                question_type = question_type
                question_number = elements.get("content").split(".")[0] if "content" in elements else None
                questions.append([question_number, question_content, paper_title, question_type, question_answer])
            if key == "type" and value == "questionheader":  # 找到题型的字典
                question_type = elements.get("title").split("、")[-1][:-1]  # 掐头去尾只留下题型
            elif isinstance(value, dict) or isinstance(value, list):
                questions.extend(extract_questions(value, paper_title, question_type))  # 递归遍历子字典或列表
    elif isinstance(elements, list):
        for subvalue in elements:
            questions.extend(extract_questions(subvalue, paper_title, question_type))  # 递归遍历子字典或列表
    return questions


if __name__ == "__main__":
    scanner = ExamScanner('../test/test.txt')
    result = scanner.scan()
    # e_parser = ExamParser('../test/test.txt')
    # result = e_parser.parse(raw=True)
    # questions = extract_questions(result,result.get('title'))
    print(result)
    # print(questions)
