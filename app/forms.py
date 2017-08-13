#-*- coding: utf-8 -*-
import os

from datetime import datetime
from flask import redirect, url_for, request
from flask.ext.login import current_user
from flask.ext.wtf import Form
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Email
from wtforms import IntegerField, TextField, PasswordField, HiddenField, \
    validators
from werkzeug import secure_filename
from urllib.parse import urlparse, urljoin
from itsdangerous import URLSafeTimedSerializer
from app import app, models, db, notification
from sqlalchemy.sql.expression import func

ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (test_url.scheme in ('http', 'https') and
            ref_url.netloc == test_url.netloc)


def get_redirect_target():
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target

class RedirectForm(Form):
    next = HiddenField()

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target() or ''

    def redirect(self, endpoint='main', **values):
        if is_safe_url(self.next.data):
            return redirect(self.next.data)
        target = get_redirect_target()
        return redirect(target or url_for(endpoint, **values))


class LoginForm(RedirectForm):
    userid = TextField('ID')
    password = PasswordField('PW')
    next = TextField('next')
    user = None

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        user = models.User.query.filter_by(username=self.userid.data).first()
        if user is None:
            self.userid.errors.append('존재하지 않는 사용자입니다.')
            return False
        if user.password != self.password.data:
            self.password.errors.append('잘못된 암호입니다.')
            return False

        if self.next.data == "":
            self.next.data = "/"
        self.user = user
        return True


class RegisterForm(RedirectForm):
    name = TextField('Name')
    userid = TextField('ID')
    passwd = PasswordField('PW')
    email = TextField('E-mail', validators=[DataRequired(), Email()])
    user = None


    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        user = models.User.query.filter_by(username=self.userid.data).first()
        if user is not None:
            self.userid.errors.append('Duplicate')
            return False

        self.userid.data = self.userid.data.strip()
        self.name.data = self.name.data.strip()
        self.passwd.data = self.passwd.data.strip()
        self.email.data = self.email.data.strip()


        user = models.User.query.filter_by(email=self.email.data).first()
        if user and user.username[0: 11] == 'stem_member' and \
           user.nickname == self.name.data:

            member = models.User(True, self.userid.data, self.passwd.data,
                                    self.name.data, self.email.data)
            
            user.username = member.username
            user.password = member.password

            db.session.add(user)

            idnum = db.session.query(func.max(models.User.id).label("id")).first().id
            boardmember = models.BoardMember()
            boardmember.title = '개인게시판 ' + str(idnum + 1)
            boardmember.group_id = 10
            boardmember.owner_id = user.id

            db.session.add(boardmember)
            db.session.commit()

            self.user=user
            return True
        elif user:
            self.userid.errors.append('Duplicate')
            return False

        user = models.User(False, self.userid.data, self.passwd.data,
                           self.name.data, self.email.data)

        db.session.add(user)
        db.session.commit()

        self.user = user
        return True


class ModifyForm(RedirectForm):
    passwd = PasswordField('PW')
    passwd_original = PasswordField('PW-original')
    email = TextField('E-mail', validators=[DataRequired(), Email()])
    user = current_user
    errors = []

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False
        self.errors = []
        if self.user.password != self.passwd_original.data:
            self.errors.append("비밀번호가 맞지 않습니다.")
            return False

        users = models.User.query.filter_by(email=self.email.data).first()
        if users and (users.email != current_user.email) :
            self.errors.append("이미 사용 중인 이메일입니다. 다른 이메일을 입력하세요.")
            return False

        if self.passwd.data != '':
            self.user.password = self.passwd.data
        if self.email.data != '':
            self.user.email = self.email.data
        db.session.commit()
        return True

class ModifyMemberForm(ModifyForm):
    cell = TextField('Cell Phone')
    birthday = TextField('Birthday')
    cycle = IntegerField('Cycle')
    addr = TextField('Address')
    photo = FileField('Photo',
                      validators=[FileAllowed(['png', 'jpg', 'gif'],
                                              'PNG/JPG/GIF file only')])
    cover = FileField('Cover',
                      validators=[FileAllowed(['png', 'jpg', 'gif'],
                                              'PNG/JPG/GIF file only')])
    department = IntegerField('Department')
    stem_department = IntegerField('STEM_Department')
    cvpublic = TextField('CV')
    cvmember = TextField('Comment')
    social = TextField('Social Network')
    position = TextField('Position')

    def validate(self):
        rv = super().validate()
        if not rv:
            return False

        if self.cell.data != '':
            self.user.phone = self.cell.data
        if self.birthday.data != '':
            self.user.birthday = datetime.strptime(self.birthday.data,
                                                          '%Y-%m-%d').date()
        if self.photo.data.filename != '':
            ext = self.photo.data.filename.rsplit('.', 1)[1]
            filename = 'profile/%d.' % self.user.id + ext
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            self.photo.data.save(file_path)
            self.user.img = filename
        if self.cover.data.filename != '':
            ext = self.cover.data.filename.rsplit('.', 1)[1]
            filename = 'cover/%d.' % self.user.id + ext
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            self.cover.data.save(file_path)
            self.user.cover = filename
        if self.cycle.data != '':
            self.user.cycle = self.cycle.data

        self.user.addr = self.addr.data

        self.user.cvpublic = self.cvpublic.data

        self.user.cvmember = self.cvmember.data

        if self.social.data != '':
            if self.social.data[0:4] != 'http':
                self.social.data = 'http://' + self.social.data

        self.user.social = self.social.data

        self.user.position = self.position.data

        self.user.last_mod = datetime.now()

        self.user.deptuniv_id = self.department.data
        self.user.deptstem_id = self.stem_department.data

        db.session.commit()

        target = models.User.query.filter_by(id=current_user.id).first()
        notification.Push(self.user, models.User.query.filter_by(ismember=1).all(),
                          target, models.NotificationAction.update)

        return True

class ResetForm(Form):
    nickname = TextField('Name', validators=[DataRequired()])
    username = TextField('ID', validators=[DataRequired()])
    email = TextField('E-mail', validators=[DataRequired(), Email()])

class FindIDForm(Form):
    nickname = TextField('Name', validators=[DataRequired()])
    email = TextField('E-mail', validators=[DataRequired(), Email()])

class ResetPassword(Form):
    password = PasswordField('PW', validators=[DataRequired()])

class SearchForm(Form):
    search = TextField('Search')
    searchstr = TextField('String')

class ModifyStemDeptOnly(Form):
    memberid = IntegerField('MemberID', validators=[DataRequired()])
    stem_department = IntegerField('STEM_Department', validators=[DataRequired()])