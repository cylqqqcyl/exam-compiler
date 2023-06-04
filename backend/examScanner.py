import re

class Parser:
    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self):
        with open(self.filepath, 'r', encoding='utf-8') as file:
            content = file.read()

        # 试卷头部信息的匹配规则
        header_pattern = re.compile(r'试卷名称：(.*?)科目：(.*?)年级：(.*?)日期：(.*?)\n')
        header_match = header_pattern.search(content)
        header_info = header_match.groups() if header_match else ("", "", "", "")

        # 题目的匹配规则
        question_pattern = re.compile(r'\n(\d+)\. \[(.*?)\] (.*?) 答案：(.*?) 分值：(\d+)')
        questions = question_pattern.findall(content)

        # 选择题选项的匹配规则
        option_pattern = re.compile(r'\n\(\w+\) (.*?)\n')
        options = option_pattern.findall(content)

        # 返回解析结果
        return {
            'header': header_info,
            'questions': questions,
            'options': options,
        }

if __name__ == "__main__":
    parser = Parser('test_paper.txt')
    result = parser.parse()
    print(result)
