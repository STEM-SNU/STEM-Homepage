#-*-coding: utf-8 -*-
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext import restful
from flask.ext.admin import Admin
from flask.ext.mail import Mail
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.mobility import Mobility
from .config import MAIL_PASSWORD
import os

app = Flask(__name__)

Mobility(app)
app.config['MOBILE_COOKIE'] = False

app.config.from_object('config')
app.secret_key = '0087a3768e5285b2580d'

ALLOWED_EXTENSIONS_DOCUMENT = \
    set('doc_docx_ppt_pptx_xls_xlsx_hwp_txt_pdf'.split('_'))
ALLOWED_EXTENSIONS_IMAGE = \
    set('jpg_png_gif_bmp'.split('_'))
ALLOWED_EXTENSIONS_ARCHIVE = \
    set('zip_7z_alz_gz_gzip'.split('_'))
ALLOWED_EXTENSIONS_MEDIA = \
    set('avi_wmv_mkv_mp4_mp3_wma_wav_ogg'.split('_'))
ALLOWED_EXTENSIONS_CODE = \
    set('c_cpp_h_hpp_py_rb_md_rkt_ml'.split('_'))

app.config['ALLOWED_EXTENSIONS'] = \
    ALLOWED_EXTENSIONS_DOCUMENT | \
    ALLOWED_EXTENSIONS_IMAGE | \
    ALLOWED_EXTENSIONS_ARCHIVE | \
    ALLOWED_EXTENSIONS_MEDIA | \
    ALLOWED_EXTENSIONS_CODE

app.config['DISALLOWED_EXTENSIONS'] = set('php_asp_exe_html_js'.split('_'))

app.config['APP_ROOT'] = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app.config['APP_ROOT'],
                                           'static/upload')
mail = Mail(app)

app.config.update(
        DEBUG=True,
        #EMAIL SETTINGS
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,
        MAIL_USE_SSL=True,
        MAIL_USE_TSL=False,
        MAIL_USERNAME='stemsnu.noreply@gmail.com',
        MAIL_DEFAULT_SENDER='공우_발신전용',
        MAIL_PASSWORD= MAIL_PASSWORD
        )

mail = Mail(app)

db = SQLAlchemy(app)
api = restful.Api(app)
lm = LoginManager()
lm.init_app(app)
admin = Admin(url='/admin_stemware', template_mode='bootstrap3')

from app.member_app import member_app
app.register_blueprint(member_app, url_prefix='/stem')

from app import views, models, forms, config, admin_views, filters

from flask_apscheduler import APScheduler
from datetime import date, datetime, timedelta

def daily():
    members = models.User.query.filter_by(ismember=1).all()
    for member in members:
        if member.birthday and member.birthday > date(1970,1,2):
            if member.birthday.strftime('%m-%d') == datetime.now().strftime('%m-%d'):
                target = member
                notification.Push(member, models.User.query.filter_by(ismember=1).all(),
                          target, models.NotificationAction.update, "Birthday")
    records = models.Record.query.filter_by(body='').all()
    limit = datetime.now() - timedelta(days=2)
    for record in records:
        if record.confday <= limit:
            db.session.delete(record)
    db.session.commit()


class Config(object):
    JOBS = [
        {
            'id': 'daily',
            'func': daily,
            'trigger': 'interval',
            'seconds': 86400,
            'start_date': '2010-07-14 00:00:05'
        }
    ]

    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
