import os
import re
import uuid

from werkzeug import secure_filename
from app import app, db, models, mail
from flask.ext.mail import Mail, Message

# returns tuple (add, sub)
# add: elements that are added to target
# sub: elements that are removed from original
def list_diff(original, target):
    original = set(original)
    target = set(target)
    return (list(target-original), list(original-target))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() \
           in app.config['ALLOWED_EXTENSIONS']


def process_file(file, parent):
    if not file:
        return False

    if not allowed_file(file.filename):
        return False

    filename = file.filename

    extension = ''
    if '.' in filename:
        extension = filename.rsplit('.', 1)[1]

    save_name = str(uuid.uuid4()).replace('-', '') + '.%s' % extension
    file_data = models.File(file.filename, save_name, parent)
    db.session.add(file_data)

    file.save(os.path.join(app.config['UPLOAD_FOLDER'], save_name))

    return file_data

def delete_file(save_name):

    delete_file = models.File.query.filter_by(link=save_name).first()

    if delete_file is None :
        return False
    else :
        db.session.delete(delete_file)
        db.session.commit()
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], save_name))

    return True

def get_tags(text):
    html = re.compile('<.*?>')
    tag = re.compile('#\w+')
    reject = re.compile('#\d+')
    words = re.split("\s+", html.sub(' ', text))
    tags = []
    for word in words:
        if not word:
            continue
        match = tag.match(word)
        if match and not reject.match(word):
            tags.append(match.group(0)[1:].lower())
    return tags

def send_email(to, subject, template, **kwargs):
    msg = Message(
           subject,
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to])
    msg.html = template
    mail.send(msg)