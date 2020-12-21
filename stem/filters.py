import re

import jinja2

from stem import app

_PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')


@app.template_filter('newline2br')
@jinja2.evalcontextfilter
def newline2br(eval_ctx, value):
    print(_PARAGRAPH_RE.split(jinja2.escape(value)))
    result = '<br>'.join(p.replace('\n', Markup('<br>\n'))
    	for p in _PARAGRAPH_RE.split(jinja2.escape(value)))
    print(result)
    if eval_ctx.autoescape:
        result = jinja2.Markup(result)
    return result
