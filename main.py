from flask import Flask, render_template
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://be3278fbbccac7:64de4292@us-cdbr-iron-east-01.cleardb.net/heroku_60fb971363678a5'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def __repr__(self):
        return '<User %r>' % self.username

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/test')
def test():
    lst = []
    for i in range(10):
        lst.append({'number':i, 'name': 'Item ' + str(i*3)})
    return render_template('test_one.html', items=lst)

@app.route('/static/<path:path>')
def send_file(path):
    return send_from_directory('./static', path)

    
if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')