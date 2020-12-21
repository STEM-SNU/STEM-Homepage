#!venv/bin/python

import stem

if __name__ == '__main__':
    stem.app.debug = False  # change before commit
    stem.app.run(host='0.0.0.0',port=80, use_reloader=False)
