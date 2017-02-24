#-*-coding:utf-8-*-
#!venv/bin/python
from app import app

if __name__ == '__main__':
    app.debug = True  # change before commit
    app.run(host='0.0.0.0',port=80, use_reloader=False)
