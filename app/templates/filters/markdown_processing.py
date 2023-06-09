import markdown2 as md


def markdown(value):
    return md.markdown(value)
# from pygments import highlight
# from pygments.lexers import get_lexer_by_name
# from pygments.formatters import HtmlFormatter


# def markdown(value):
#     # Markdown 변환
#     html = md.markdown(value)
#
#     # 코드 하이라이팅 적용
#     formatter = HtmlFormatter()
#     lexer = get_lexer_by_name('python', stripall=True)
#     code_highlighted = highlight(html, lexer, formatter)
#
#     return code_highlighted