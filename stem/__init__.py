import datetime
import os

import flask
import flask_admin
import flask_login
import flask_mail
import flask_mobility
import flask_restful
import flask_sqlalchemy
import flask_apscheduler

from stem import config

app = flask.Flask(__name__)

flask_mobility.Mobility(app)
app.config['MOBILE_COOKIE'] = False

app.config.from_object('config')
app.secret_key = '0087a3768e5285b2580d'

_ALLOWED_EXTENSIONS_DOCUMENT = {
    'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'hwp', 'txt', 'pdf'
}
_ALLOWED_EXTENSIONS_IMAGE = {'jpg', 'png', 'gif', 'bmp'}
_ALLOWED_EXTENSIONS_ARCHIVE = {'zip', '7z', 'alz', 'gz', 'gzip'}
_ALLOWED_EXTENSIONS_MEDIA = {'avi', 'wmv', 'mkv;mp4_mp3_wma', 'wav', 'ogg'}
_ALLOWED_EXTENSIONS_CODE = {
    'c', 'cc', 'cpp', 'h', 'hpp', 'py', 'rb', 'md', 'rkt', 'ml', 'js', 'html',
    'css', 'sass', 'less'
}

app.config['ALLOWED_EXTENSIONS'] = (
    _ALLOWED_EXTENSIONS_DOCUMENT | _ALLOWED_EXTENSIONS_IMAGE
    | _ALLOWED_EXTENSIONS_ARCHIVE | _ALLOWED_EXTENSIONS_MEDIA
    | _ALLOWED_EXTENSIONS_CODE)

app.config['DISALLOWED_EXTENSIONS'] = {'php', 'asp', 'exe', 'html', 'js'}

app.config['APP_ROOT'] = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['APP_ROOT'],
                                           'static/upload')
mail = flask_mail.Mail(app)

app.config.update(
    DEBUG=True,
    # EMAIL SETTINGS
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USE_TSL=False,
    MAIL_USERNAME='stemsnu.noreply@gmail.com',
    MAIL_DEFAULT_SENDER='공우_발신전용',
    MAIL_PASSWORD=config.MAIL_PASSWORD)

mail = flask_mail.Mail(app)

db = flask_sqlalchemy.SQLAlchemy(app)
api = flask_restful.Api(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
admin = flask_admin.Admin(url='/admin_stemware', template_mode='bootstrap3')


from stem import models
from stem import notification
from stem import views
from stem import filters
from stem.member_app import member_app

app.register_blueprint(member_app, url_prefix='/stem')


def daily():
    members = models.User.query.filter_by(ismember=1).all()
    for member in members:
        if member.birthday and member.birthday > datetime.date(1970, 1, 2):
            today = datetime.datetime.now()
            if (member.birthday.month == today.month and
                    member.birthday.day == today.day):
                target = member
                notification.Push(member,
                                  models.User.query.filter_by(
                                      ismember=1).all(), target,
                                  models.NotificationAction.update, 'Birthday')
    records = models.Record.query.filter_by(body='').all()
    limit = datetime.datetime.now() - datetime.timedelta(days=2)
    for record in records:
        if record.confday <= limit:
            db.session.delete(record)
    db.session.commit()


class Config(object):
    JOBS = [{
            'id': 'daily',
            'func': daily,
            'trigger': 'interval',
            'seconds': 86400,
            'start_date': '2010-07-14 00:00:05'
            }]

    SCHEDULER_API_ENABLED = True


app.config.from_object(Config())
scheduler = flask_apscheduler.APScheduler()
scheduler.init_app(app)
scheduler.start()
