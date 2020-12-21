import datetime
import enum
import re
import uuid

import pytz
import sqlalchemy_utils
from stem import app
from stem import db

timezone = pytz.timezone('Asia/Seoul')
utc = pytz.utc


class Activity(db.Model):
    __tablename__ = 'activity'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, default=0)  # 0 : 정규활동, 1 : 특별활동, 2 : 소그룹활동
    name = db.Column(db.Unicode(256))
    totalscore = db.Column(db.Integer)
    quarter_id = db.Column(db.Integer, db.ForeignKey('quarter.id'))
    members = db.relationship(
        'User',
        passive_deletes=True,
        secondary='member_activity',
        backref='activity',
        lazy='dynamic',
        order_by='User.nickname')

    def __init__(self, activity_type=0, name='', totalscore=0, quarter=None):
        self.type = activity_type
        self.name = name
        self.totalscore = totalscore
        self.quarter = quarter

    def __repr__(self):
        return '[Activity %s]' % self.name


class Banner(db.Model):
    __tablename__ = 'banner'
    id = db.Column(db.Integer, primary_key=True)
    src = db.Column(db.Unicode(512))
    href = db.Column(db.Unicode(512))
    description = db.Column(db.Unicode(1024))

    def __repr__(self):
        return '[Banner %r]' % self.description

    def __init__(self, src='', href='', description=''):
        self.src = src
        self.href = href
        self.description = description


class Bgroup(db.Model):
    __tablename__ = 'bgroup'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(64))
    boards = db.relationship('BoardMember', backref='group', lazy='dynamic')

    def __init__(self, name=''):
        self.name = name

    def __repr__(self):
        return '[Group %d - %s]' % (self.id, self.name)


class BoardMember(db.Model):
    __tablename__ = 'boardmember'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(64))
    group_id = db.Column(db.Integer, db.ForeignKey('bgroup.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    preferred_members = db.relationship(
        'User',
        passive_deletes=True,
        secondary='member_preference',
        backref='boardmember',
        lazy='dynamic')
    posts = db.relationship('PostMember', backref='boardmember', lazy='dynamic')

    def __init__(self, title='', owner=None, group=None):
        self.title = title
        self.owner = owner
        self.group = group

    def __repr__(self):
        return '[Board %r]' % self.title


class BoardPublic(db.Model):
    __tablename__ = 'boardpublic'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80), unique=True)
    description = db.Column(db.Unicode(200))
    posts = db.relationship('PostPublic', backref='boardpublic', lazy='dynamic')

    def __init__(self, name='', description=''):
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Board %r>' % self.name


class CommentMember(db.Model):
    __tablename__ = 'commentmember'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Unicode(1024))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    postmember_id = db.Column(db.Integer, db.ForeignKey('postmember.id'))

    def __init__(self, body='', membercommenter=None, postmember=None):
        self.body = body
        self.membercommenter = membercommenter
        self.postmember = postmember
        self.timestamp = datetime.datetime.now()
        if postmember:
            postmember.commentCount += 1
            db.session.commit()

    def __repr__(self):
        return '[Comment %d of Post_Member %d]' % (self.id, self.postmember_id)

    def remove(self):
        if self.postmember:
            self.postmember.commentCount -= 1
        db.session.delete(self)
        db.session.commit()


class CommentPublic(db.Model):
    __tablename__ = 'commentpublic'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Unicode(1024))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    postpublic_id = db.Column(db.Integer, db.ForeignKey('postpublic.id'))

    def __init__(self, body='', publiccommenter=None, postpublic=None):
        self.body = body
        self.publiccommenter = publiccommenter
        self.postpublic = postpublic
        self.timestamp = datetime.datetime.now()
        if postpublic:
            postpublic.commentCount += 1
            db.session.commit()

    def __repr__(self):
        return '[Comment %d of Post_Public %d]' % (self.id, self.postpublic_id)

    def remove(self):
        if self.postpublic:
            self.postpublic.commentCount -= 1
        db.session.delete(self)
        db.session.commit()


class CommentRecord(db.Model):
    __tablename__ = 'commentrecord'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Unicode(1024))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    record_id = db.Column(db.Integer,
                          db.ForeignKey('record.id', ondelete='CASCADE'))

    def __init__(self, body='', recordcommenter=None, record=None):
        self.body = body
        self.recordcommenter = recordcommenter
        self.record = record
        self.timestamp = datetime.datetime.now()
        if record:
            record.commentCount += 1
            db.session.commit()

    def __repr__(self):
        return '[Comment %d of Record %d]' % (self.id, self.record_id)

    def remove(self):
        if self.record:
            self.record.commentCount -= 1
        db.session.delete(self)
        db.session.commit()


class Conference(db.Model):
    __tablename__ = 'conference'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(256))
    quarter_id = db.Column(db.Integer, db.ForeignKey('quarter.id'))
    record_id = db.Column(db.Integer,
                          db.ForeignKey('record.id', ondelete='CASCADE'))
    members = db.relationship(
        'User',
        passive_deletes=True,
        secondary='member_conference',
        backref='conference',
        lazy='dynamic',
        order_by='User.nickname')

    def __init__(self, name='', quarter=None, record=None):
        self.name = name
        self.quarter = quarter
        self.record = record

    def __repr__(self):
        return '[Conference %r]' % self.name


class Configuration(db.Model):
    __tablename__ = 'configuration'
    id = db.Column(db.Integer, primary_key=True)
    option = db.Column(db.Unicode(64))
    value = db.Column(db.Boolean)

    def __init__(self, option='', value=0):
        self.option = option
        self.value = value

    def __repr__(self):
        return '[Config %r]' % self.option


class DeptStem(db.Model):
    __tablename__ = 'deptstem'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(32))
    members = db.relationship('User', backref='deptstem', lazy='dynamic')

    def __repr__(self):
        return '%s' % self.name


class DeptUniv(db.Model):
    __tablename__ = 'deptuniv'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(32))
    members = db.relationship('User', backref='deptuniv', lazy='dynamic')

    def __repr__(self):
        return '%s' % self.name


class File(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(256))
    link = db.Column(db.Unicode(1024))
    postmember_id = db.Column(db.Integer, db.ForeignKey('postmember.id'))
    postpublic_id = db.Column(db.Integer, db.ForeignKey('postpublic.id'))
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'))

    def __init__(self, name='', link='', post=None):
        self.name = name
        self.link = link
        if post.__class__ == PostMember:
            self.postmember = post
        elif post.__class__ == PostPublic:
            self.postpublic = post
        elif post.__class__ == Record:
            self.record = post

    def __repr__(self):
        return '[File %r]' % self.name


class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Unicode(512))
    starttime = db.Column(db.DateTime)
    endtime = db.Column(db.Unicode(64))

    def __init__(self, content='', starttime=None, endtime=''):
        timezero = datetime.time(tzinfo=utc)
        self.content = content
        self.starttime = datetime.datetime.combine(starttime, timezero)
        if endtime and endtime != starttime:
            endtime = datetime.datetime.combine(endtime, timezero)
            self.endtime = str(endtime.timestamp())

    def __repr__(self):
        return '[History %r]' % self.content


class MemberActivity(db.Model):
    __tablename__ = 'member_activity'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'))
    score = db.Column(db.Integer, default=0)

    def __init__(self, member=None, activity=None, score=0):
        self.member = member
        self.activity = activity
        self.score = score


class MemberComment(db.Model):
    __tablename__ = 'member_comment'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Unicode(1024))
    timestamp = db.Column(db.DateTime)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    writer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self,
                 body='',
                 profilecommentreceiver=None,
                 profilecommentwriter=None):
        self.body = body
        self.timestamp = datetime.datetime.now()
        self.member = profilecommentreceiver
        self.writer = profilecommentwriter

    def __repr__(self):
        return '[%d Comment by %d]' % (self.member_id, self.writer_id)

    def remove(self):
        db.session.delete(self)
        db.session.commit()


class MemberConference(db.Model):
    __tablename__ = 'member_conference'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    conference_id = db.Column(db.Integer, db.ForeignKey('conference.id'))
    state = db.Column(db.Integer, default=0)

    # 0 : 출석, 1 : 지각, 2 : 공결, 3 : 공결+회의록미확인, 4 : 결석, 5 : 결석+회의록미확인

    def __init__(self, member=None, conference=None, state=0):
        self.member = member
        self.conference = conference
        self.state = state


class MemberPreference(db.Model):
    __tablename__ = 'member_preference'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    boardmember_id = db.Column(db.Integer, db.ForeignKey('boardmember.id'))

    def __init__(self, member=None, boardmember=None):
        self.member = member
        self.boardmember = boardmember


class Memo(db.Model):
    __tablename__ = 'memo'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(256))
    body = db.Column(db.Unicode(65536))
    timestamp = db.Column(db.DateTime)
    writer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __init__(self, title='', body='', writer=None):
        self.title = title
        self.body = body
        self.timestamp = datetime.datetime.now()
        self.writer = writer

    def __repr__(self):
        return '[Memo %d]' % self.id


class Note(db.Model):
    __tablename__ = 'note'
    id = db.Column(db.Integer, primary_key=True)
    recv_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sent_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.Unicode(2048))
    timestamp = db.Column(db.DateTime)
    recv_read = db.Column(db.Boolean)
    recv_del = db.Column(db.Boolean)
    sent_del = db.Column(db.Boolean)

    def __init__(self, receiver=None, sender=None, body=''):
        self.receiver = receiver
        self.sender = sender
        self.body = body
        self.timestamp = datetime.datetime.now()
        self.recv_read = False
        self.recv_del = False
        self.sent_del = False

    def __repr__(self):
        return '[Note %d]' % self.id


class NotificationAction(enum.IntEnum):
    create = 1
    update = 2
    delete = 3


class ObjectType(enum.IntEnum):
    User = 1
    #   Member = 2
    Post = 3
    Comment = 4
    Board = 5
    #    Task = 6
    #    TaskComment = 7
    #    Tag = 8
    Birthday = 9


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    object_type = db.Column(db.Integer())
    object_id = db.Column(db.Integer)
    verb = db.Column(db.Integer())
    timestamp = db.Column(db.DateTime)
    is_read = db.Column(db.Boolean)
    message = db.Column(db.Unicode(256))

    def __init__(self, sender, receiver, target, verb, message):
        type_parser = re.compile(r'models\.(\w*)')
        try:
            target_type = type_parser.findall(str(type(target)))[0]
            target_type = ObjectType[target_type]
        except IndexError:
            print('Invalid Object type - not a model')
            raise IndexError
        except KeyError:
            print('Invalid Object type - no such model')
            raise KeyError
        self.sender = sender
        self.receiver = receiver
        self.object_type = target_type
        self.object_id = target.id
        self.verb = verb
        self.timestamp = datetime.datetime.now()
        self.is_read = False
        self.message = message

    def __repr__(self):
        global_type = globals()[ObjectType(self.object_type).name]
        target = global_type.query.get(self.object_id)

        return '[Notification for %r, about %r-%s, sent by %r]' % (
            self.receiver, target, NotificationAction(
                self.verb).name, self.sender)


class PostMember(db.Model):
    __tablename__ = 'postmember'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(256))
    body = db.Column(db.Unicode(66536))
    hitCount = db.Column(db.Integer)
    commentCount = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime)
    writer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    boardmember_id = db.Column(db.Integer, db.ForeignKey('boardmember.id'))
    comments = db.relationship(
        'CommentMember', backref='postmember', lazy='joined')
    files = db.relationship('File', backref='postmember', lazy='joined')

    def __init__(self, title='', body='', memberwriter=None, boardmember=None):
        self.title = title
        self.body = body
        self.memberwriter = memberwriter
        self.boardmember = boardmember
        self.timestamp = datetime.datetime.now()
        self.hitCount = 0
        self.commentCount = 0

    def __repr__(self):
        return '[PostMember %r %r]' % (self.id, self.title)


class PostPublic(db.Model):
    __tablename__ = 'postpublic'
    id = db.Column(db.Integer, primary_key=True)
    hidden = db.Column(db.Boolean)
    title = db.Column(db.Unicode(256))
    body = db.Column(db.Unicode(66536))
    hitCount = db.Column(db.Integer)
    commentCount = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime)
    writer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    boardpublic_id = db.Column(db.Integer, db.ForeignKey('boardpublic.id'))
    comments = db.relationship(
        'CommentPublic', backref='postpublic', lazy='joined')
    files = db.relationship('File', backref='postpublic', lazy='joined')

    def __init__(self,
                 hidden=False,
                 title='',
                 body='',
                 publicwriter=None,
                 boardpublic=None):
        self.title = title
        self.hidden = hidden
        self.body = body
        self.publicwriter = publicwriter
        self.boardpublic = boardpublic
        self.timestamp = datetime.datetime.now()
        self.hitCount = 0
        self.commentCount = 0

    def __repr__(self):
        return '[PostPublic %r %r]' % (self.id, self.title)


class Quarter(db.Model):
    __tablename__ = 'quarter'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    semester = db.Column(db.Integer)  # 1 봄 2 여름 3 가을 4 겨울
    activity_score = db.Column(db.Integer)  # 이수기준점수
    conference_absence = db.Column(db.Integer)  # 회의페널티
    description = db.Column(db.Unicode(128))
    activities = db.relationship('Activity', backref='quarter', lazy='dynamic')
    conferences = db.relationship(
        'Conference', backref='quarter', lazy='dynamic')

    def __init__(self, year=1970, semester=1):
        self.year = year
        self.semester = semester
        self.activity_score = 0
        self.conference_absence = 0
        self.description = ''

    def __repr__(self):
        return '[Year %d Quarter %d]' % (self.year, self.semester)


class Record(db.Model):
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    conftype = db.Column(db.Integer)
    confday = db.Column(db.DateTime)
    confplace = db.Column(db.Unicode(64))
    title = db.Column(db.Unicode(256))
    body = db.Column(db.Unicode(65536))
    hitCount = db.Column(db.Integer)
    commentCount = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime)
    writer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comments = db.relationship(
        'CommentRecord', backref='record', lazy='joined', cascade='all, delete')
    conference = db.relationship(
        'Conference', backref='record', lazy='dynamic', cascade='all, delete')
    files = db.relationship('File', backref='record', lazy='joined')

    def __init__(self,
                 conftype=0,
                 confday=datetime.datetime.now(),
                 confplace='',
                 title='',
                 body='',
                 recordwriter=None):
        self.conftype = conftype
        self.confday = confday
        self.confplace = confplace
        self.title = title
        self.body = body
        self.hitCount = 0
        self.commentCount = 0
        self.timestamp = datetime.datetime.now()
        self.recordwriter = recordwriter

    def __repr__(self):
        return '[Record Type %d Day %r]' % (self.conftype,
                                            self.confday.strftime('%y%m%d'))


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    password = db.Column(
        sqlalchemy_utils.PasswordType(
            schemes=['pbkdf2_sha512', 'md5_crypt'], deprecated=['md5_crypt']))
    nickname = db.Column(db.Unicode(64), index=True)
    email = db.Column(db.String(120), index=True, unique=True)
    ismember = db.Column(db.Boolean)
    cycle = db.Column(db.Integer)
    deptuniv_id = db.Column(db.Integer, db.ForeignKey('deptuniv.id'))
    deptstem_id = db.Column(db.Integer, db.ForeignKey('deptstem.id'))
    cvpublic = db.Column(db.Unicode(1024))
    cvmember = db.Column(db.Unicode(1024))
    phone = db.Column(db.String(32))
    birthday = db.Column(db.Date)
    img = db.Column(db.Unicode(256))
    cover = db.Column(db.Unicode(256))
    addr = db.Column(db.Unicode(512))
    social = db.Column(db.Unicode(256))
    position = db.Column(db.Unicode(512))
    last_mod = db.Column(db.DateTime)
    sent_notifications = db.relationship(
        'Notification',
        backref='sender',
        lazy='dynamic',
        primaryjoin='Notification.sender_id==User.id',
        cascade='all, delete')
    received_notifications = db.relationship(
        'Notification',
        backref='receiver',
        lazy='dynamic',
        primaryjoin='Notification.receiver_id==User.id',
        cascade='all, delete')
    owned_boards = db.relationship(
        'BoardMember', backref='owner', lazy='dynamic', cascade='all, delete')
    member_comments = db.relationship(
        'CommentMember',
        backref='membercommenter',
        lazy='dynamic',
        cascade='all, delete')
    public_comments = db.relationship(
        'CommentPublic',
        backref='publiccommenter',
        lazy='dynamic',
        cascade='all, delete')
    record_comments = db.relationship(
        'CommentRecord',
        backref='recordcommenter',
        lazy='dynamic',
        cascade='all, delete')

    profile_comments_recv = db.relationship(
        'MemberComment',
        backref='profilecommentreceiver',
        lazy='dynamic',
        primaryjoin='MemberComment.member_id==User.id',
        cascade='all, delete')
    profile_comments_writ = db.relationship(
        'MemberComment',
        backref='profilecommentwriter',
        lazy='dynamic',
        primaryjoin='MemberComment.writer_id==User.id',
        cascade='all, delete')

    activities = db.relationship(
        'Activity',
        passive_deletes=True,
        secondary='member_activity',
        backref='member',
        lazy='dynamic',
        order_by='Activity.type')
    conferences = db.relationship(
        'Conference',
        passive_deletes=True,
        secondary='member_conference',
        backref='member',
        lazy='dynamic',
        order_by='Conference.record_id')
    received_profile_comments = db.relationship(
        'MemberComment',
        backref='member',
        lazy='dynamic',
        primaryjoin='MemberComment.member_id==User.id',
        cascade='all, delete')
    writing_profile_comments = db.relationship(
        'MemberComment',
        backref='writer',
        lazy='dynamic',
        primaryjoin='MemberComment.writer_id==User.id',
        cascade='all, delete')
    preferred_boards = db.relationship(
        'BoardMember',
        passive_deletes=True,
        secondary='member_preference',
        backref='member',
        lazy='dynamic')

    memoes = db.relationship(
        'Memo', backref='writer', lazy='dynamic', cascade='all, delete')
    sent_notes = db.relationship(
        'Note',
        backref='sender',
        lazy='dynamic',
        primaryjoin='Note.sent_id==User.id',
        cascade='all, delete')
    received_notes = db.relationship(
        'Note',
        backref='receiver',
        lazy='dynamic',
        primaryjoin='Note.recv_id==User.id',
        cascade='all, delete')
    member_posts = db.relationship(
        'PostMember',
        backref='memberwriter',
        lazy='dynamic',
        cascade='all, delete')
    public_posts = db.relationship(
        'PostPublic',
        backref='publicwriter',
        lazy='dynamic',
        cascade='all, delete')
    records = db.relationship('Record', backref='recordwriter', lazy='dynamic')

    def __init__(self,
                 ismember=False,
                 username='',
                 password=str(uuid.uuid4()).replace('-', ''),
                 nickname='',
                 email=''):
        self.username = username
        self.password = password
        self.nickname = nickname
        self.email = email
        self.ismember = ismember
        if not self.ismember:
            self.cycle = None
            self.deptuniv_id = None
            self.deptstem_id = None
            self.cvpublic = None
            self.cvmember = None
            self.phone = None
            self.birthday = None
            self.img = None
            self.cover = None
            self.addr = None
            self.social = None
            self.position = None
            self.last_mod = None
        else:
            self.cycle = 0
            self.deptuniv_id = 0
            self.deptstem_id = 0
            self.cvpublic = ''
            self.cvmember = ''
            self.phone = ''
            self.birthday = ''
            self.img = ''
            self.cover = ''
            self.addr = ''
            self.social = ''
            self.position = ''
            self.last_mod = ''

    def __repr__(self):
        if not self.ismember:
            return '[%d. User %r]' % (self.id, self.nickname)
        else:
            return '[%d. Member %r Cycle %d]' % (self.id, self.nickname,
                                                 self.cycle)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.id)
        except NameError:
            return str(self.id)
