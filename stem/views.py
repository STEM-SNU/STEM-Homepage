import datetime

# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring

import flask
import flask_login
import flask_restful
from flask_restful import fields
from flask_restful import reqparse
from flask_mobility import decorators as mobility_decorators
import itsdangerous
import pytz
from sqlalchemy import and_

from stem import admin_views
from stem import api
from stem import app
from stem import db
from stem import forms
from stem import helper
from stem import login_manager
from stem import member_help
from stem import models

timed_serializer = itsdangerous.URLSafeTimedSerializer(app.config['SECRET_KEY'])


class AnonymousUser(flask_login.AnonymousUserMixin):

    def __init__(self):
        super().__init__()
        self.member = None


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def LoadUser(user_id):
    return models.User.query.get(int(user_id))


robot_text = open('robots.txt', 'r').read()


@app.route('/robots.txt')
def Robots():
    resp = flask.make_response(robot_text)
    resp.headers['content-type'] = 'text/plain'
    return resp


@app.route('/')
@mobility_decorators.mobile_template('/{mobile/}main.html')
def Main(template):
    banners = models.Banner.query.order_by(models.Banner.id.desc()).all()

    boardpublic_ids = [1, 2, 4, 5]
    # 1 : Notice, 2 : News, 4 : Freeboard, 5 : Q&A

    board_recents = list()
    boards = list()

    for bid in boardpublic_ids:
        board = models.BoardPublic.query.get(bid)
        if not board:
            continue
        boards.append(board)
        board_recents.append(
            db.session.query(
                models.PostPublic).filter_by(boardpublic_id=bid).order_by(
                    models.PostPublic.timestamp.desc()).limit(5).all())

    for recent_posts in board_recents:
        for post in recent_posts:
            now = datetime.datetime.utcnow()
            post.date = post.timestamp.strftime('%m.%d')
            if now - post.timestamp < datetime.timedelta(days=3):
                post.new = True

    return flask.render_template(
        template,
        bannerRec=banners,
        boardRec=board_recents,
        boards=boards,
        form=forms.LoginForm())


@app.route('/reset', methods=['GET', 'POST'])
def Reset():
    form = forms.ResetForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(email=form.email.data).first()
        if user is not None:
            if (form.username.data == user.username) and (
                    form.nickname.data == user.nickname):
                subject = 'Password reset requested'

                token = timed_serializer.dumps(user.email, salt='recover-key')

                recover_url = flask.url_for(
                    'reset_with_token', token=token, _external=True)

                html = flask.render_template(
                    'member/recover.html', recover_url=recover_url)

                helper.send_email(user.email, subject, html)

                return flask.render_template('reset_finish.html')
            else:
                flask.flash('해당하는 회원 정보가 존재하지 않습니다.')
                return flask.redirect('/reset')
        else:
            flask.flash('해당하는 회원 정보가 존재하지 않습니다.')
            return flask.redirect('/reset')
    return flask.render_template('reset.html', form=form)


@app.route('/findID', methods=['GET', 'POST'])
def FindId():
    form = forms.FindIDForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(email=form.email.data).first()
        if user is not None:
            if form.nickname.data == user.nickname:
                return flask.render_template('findID_result.html', user=user)
            else:
                flask.flash('해당하는 회원 정보가 존재하지 않습니다.')
                return flask.redirect('/findID')
        else:
            flask.flash('해당하는 회원 정보가 존재하지 않습니다.')
            return flask.redirect('/findID')
    return flask.render_template('findID.html', form=form)


@app.route('/reset/<token>', methods=['GET', 'POST'])
def ResetWithToken(token):
    try:
        email = timed_serializer.loads(token, salt='recover-key', max_age=3600)
    except:
        flask.abort(404)

    form = forms.ResetPassword()

    if form.validate_on_submit():
        user = models.User.query.filter_by(email=email).first_or_404()

        user.password = form.password.data

        db.session.add(user)
        db.session.commit()

        return flask.render_template('reset_finish.html')

    return flask.render_template(
        'reset_with_token.html', form=form, token=token)


@app.route('/m_login', methods=['GET', 'POST'])
def MobileLogin():
    form = forms.LoginForm()
    if form.validate_on_submit():
        flask_login.login_user(form.user)
        if flask_login.current_user.ismember:

            if not flask_login.current_user.last_mod:
                flask.flash('회원정보 수정내역이 없습니다. 정보를 업데이트해주세요.')
            elif datetime.datetime.utcnow(
            ) - flask_login.current_user.last_mod > datetime.timedelta(days=90):
                flask.flash('회원정보를 수정한 지 90일이 지났습니다. 정보를 업데이트해주세요.')

            if flask.request.host in [
                    'gongwoo.snu.ac.kr', 'eng-stem.snu.ac.kr', 'honor.snu.ac.kr'
            ]:
                if (flask.request.referrer.find('/stem/') >
                        -1) or (flask.request.referrer.find('/stem-') > -1):
                    return flask.redirect(flask.request.referrer)
                else:
                    return flask.redirect('/stem')
            else:
                return flask.redirect('/stem')

        return flask.redirect('/')

    return flask.render_template('member/mlogin.html', form=form)


@app.route('/vm_confirm')
def VisionMentoringConfirm():
    key = flask.request.args.get('key')
    if not key:
        flask.abort(404)
    if flask_login.current_user.is_anonymous() or not flask_login.current_user.ismember:
        return flask.render_template('vm.html', form=forms.LoginForm())
    return flask.render_template(
        'vm_confirm.html', form=forms.LoginForm(), key=key)


@app.route('/apply')
def StemApply():
    fout = open('apply_log.log', 'a+')
    fout.write('Page viewed on ' +
               datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
    if datetime.datetime.now() < datetime.datetime(2016, 3, 10):
        display = 1
    else:
        display = 2
    fout.close()
    return flask.render_template(
        'apply.html', form=forms.LoginForm(), display=display)


@app.route('/sub/<string:sub>')
def ShowSub(sub):
    m_num = sub[0]
    s_num = sub[2]
    if m_num == '5':
        return flask.redirect('/sub/' + sub + '/1')  # showBoard(sub, 1)
    elif m_num == '2' and s_num == '5':
        year = datetime.date.today().year
        return flask.redirect('/sub/2-5/%d' % year)
    if not flask.request.MOBILE:
        return flask.render_template(
            'sub' + m_num + '_' + s_num + '.html',
            current=member_help.Current(),
            m_num=int(m_num),
            s_num=int(s_num),
            form=forms.LoginForm())
    else:
        return flask.render_template(
            'mobile/sub' + m_num + '_' + s_num + '.html',
            current=member_help.Current(),
            m_num=int(m_num),
            s_num=int(s_num),
            form=forms.LoginForm())


@app.route('/sub/<string:sub>/<int:page>', methods=['GET', 'POST'])
def ShowBoard(sub, page):
    m_num = sub[0]
    s_num = sub[2]
    searchform = forms.SearchForm()
    if m_num == '5':
        if s_num == '3':
            flask.abort(404)

        pagenation = models.PostPublic.query.filter_by(
            boardpublic_id=int(s_num)).order_by(
                models.PostPublic.timestamp.desc()).paginate(
                    page, per_page=10)

        if searchform.search.data == 'title':
            pagenation = models.PostPublic.query.filter(
                and_(
                    models.PostPublic.boardpublic_id == int(s_num),
                    models.PostPublic.title.contains(
                        searchform.searchstr.data))).order_by(
                            models.PostPublic.timestamp.desc()).paginate(
                                page, per_page=10)
        elif searchform.search.data == 'writer':
            user_id = models.User.query.filter(
                models.User.nickname == searchform.searchstr.data).first()
            if user_id is not None:
                user_id = user_id.id
            else:
                user_id = '-1'
            pagenation = models.PostPublic.query.filter(
                and_(models.PostPublic.boardpublic_id == int(s_num),
                     models.PostPublic.writer_id == user_id)).order_by(
                         models.PostPublic.timestamp.desc()).paginate(
                             page, per_page=10)
        elif searchform.search.data == 'content':
            pagenation = models.PostPublic.query.filter(
                and_(models.PostPublic.boardpublic_id == int(s_num),
                     models.PostPublic.body.contains(
                         searchform.searchstr.data))).order_by(
                             models.PostPublic.timestamp.desc()).paginate(
                                 page, per_page=10)

        board = models.BoardPublic.query.get(int(s_num))
        limit = datetime.datetime.utcnow() - datetime.timedelta(days=5)

        if not board:
            flask.abort(404)

        if not flask.request.MOBILE:
            return flask.render_template(
                'sub' + m_num + '.html',
                page=page,
                totalpage=pagenation.pages,
                posts=pagenation.items,
                board=board,
                m_num=int(m_num),
                s_num=int(s_num),
                limit=limit,
                form=forms.LoginForm(),
                searchform=searchform,
                admin_users=admin_views.ADMIN_USERS)
        else:
            return flask.render_template(
                '/mobile/sub' + m_num + '.html',
                page=page,
                totalpage=pagenation.pages,
                posts=pagenation.items,
                board=board,
                m_num=int(m_num),
                s_num=int(s_num),
                limit=limit,
                form=forms.LoginForm(),
                searchform=searchform,
                admin_users=admin_views.ADMIN_USERS)

    elif m_num == '2' and s_num == '5':
        return ShowHistory(sub, page)

    return ShowSub(sub)


def ShowHistory(sub, page):
    m_num = sub[0]
    s_num = sub[2]

    year = datetime.date.today().year
    years = list(range(2010, year + 1))
    if page not in years:
        page = year
    start = datetime.datetime(page, 1, 1, tzinfo=pytz.utc)
    end = datetime.datetime(page, 12, 31, tzinfo=pytz.utc)
    all_records = db.session.query(models.History).filter(
        models.History.starttime.between(start, end)).order_by(
            models.History.starttime).all()

    for post in all_records:
        post.period = post.starttime.strftime('%m.%d')
        if post.endtime:
            end_date = datetime.datetime.utcfromtimestamp(float(post.endtime))
            post.period = post.period + ' ~ ' + end_date.strftime('%m.%d')

    if not flask.request.MOBILE:
        return flask.render_template(
            'sub2_5.html',
            mNum=int(m_num),
            sNum=int(s_num),
            form=forms.LoginForm(),
            years=years,
            page=page,
            history=all_records,
            admin_users=admin_views.ADMIN_USERS)
    else:
        return flask.render_template(
            'mobile/sub2_5.html',
            mNum=int(m_num),
            sNum=int(s_num),
            form=forms.LoginForm(),
            years=years,
            page=page,
            history=all_records,
            admin_users=admin_views.ADMIN_USERS)


@app.route('/post/<int:post_id>')
@app.route('/post/<int:post_id>/view')
def ViewPost(post_id):
    post = models.PostPublic.query.get(post_id)
    if not post or not post.boardpublic:
        return flask.abort(404)
    #    if post.boardpublic_id == 5 and not flask_login.current_user.ismember:
    #        return flask.abort(403)
    if post.hidden:
        if flask_login.current_user.is_anonymous():
            return flask.abort(403)
        elif not ((flask_login.current_user.id == post.writer_id) or
                  (flask_login.current_user.username in admin_views.ADMIN_USERS)):
            return flask.abort(404)
    post.hitCount = post.hitCount + 1
    board = models.BoardPublic.query.get(post.boardpublic_id)
    db.session.commit()
    prev_post = models.PostPublic.query.filter(
        and_(models.PostPublic.id < post_id,
             models.PostPublic.boardpublic_id == post.boardpublic_id)).order_by(
                 models.PostPublic.timestamp.desc()).first()
    next_post = models.PostPublic.query.filter(
        and_(models.PostPublic.id > post_id,
             models.PostPublic.boardpublic_id == post.boardpublic_id)).order_by(
                 models.PostPublic.timestamp.asc()).first()

    return flask.render_template(
        'mobile/sub5.html' if flask.request.MOBILE else 'sub5.html',
        m_num=5,
        s_num=post.boardpublic_id,
        mode='view',
        post=post,
        board=board,
        prev=prev_post,
        next=next_post,
        form=forms.LoginForm(),
        admin_users=admin_views.ADMIN_USERS)


@app.route('/login', methods=['GET', 'POST'])
def Login():
    form = forms.LoginForm()
    if form.validate_on_submit():
        flask_login.login_user(form.user)
        if flask_login.current_user.ismember:

            if not flask_login.current_user.last_mod:
                flask.flash('회원정보 수정내역이 없습니다. 정보를 업데이트해주세요.')
            elif datetime.datetime.utcnow(
            ) - flask_login.current_user.last_mod > datetime.timedelta(days=90):
                flask.flash('회원정보를 수정한 지 90일이 지났습니다. 정보를 업데이트해주세요.')

            if flask.request.host in [
                    'gongwoo.snu.ac.kr', 'eng-stem.snu.ac.kr', 'honor.snu.ac.kr'
            ]:
                if flask.request.referrer.find('/stem/') > -1:
                    return flask.redirect(flask.request.referrer)
                else:
                    return flask.redirect('/stem')
            else:
                return flask.redirect('/stem')

        return flask.redirect('/')

    return flask.render_template('member/login.html', form=form)


@app.route('/member/register', methods=['GET', 'POST'])
def Register():
    if not flask_login.current_user.is_anonymous():
        return flask.abort(403)

    registerform = forms.RegisterForm()
    form = forms.LoginForm()
    if registerform.validate_on_submit():
        flask_login.login_user(registerform.user)
        if flask_login.current_user.ismember:
            flask.flash('가입을 축하드립니다. 회원님의 정보를 업데이트해주세요.')
        return flask.redirect('/')
    else:
        if not flask.request.MOBILE:
            return flask.render_template(
                'member/register.html', registerform=form, form=form)
        else:
            return flask.render_template(
                'mobile/member/register.html', registerform=form, form=form)


@app.route('/member/modify', methods=['GET', 'POST'])
@mobility_decorators.mobile_template('/{mobile/}member/modify.html')
@flask_login.login_required
def Modify(template):
    if flask_login.current_user.ismember:
        form = forms.ModifyMemberForm()
        departments = models.DeptUniv.query.all()
        deptstems = models.DeptStem.query.all()
        if form.validate_on_submit():
            return flask.render_template(
                template,
                form=form,
                departments=departments,
                deptstems=deptstems,
                message='수정이 완료되었습니다.')
        return flask.render_template(
            template, form=form, departments=departments, deptstems=deptstems)
    else:
        form = forms.ModifyForm()
        if form.validate_on_submit():
            return flask.render_template(
                template, form=form, message='수정이 완료되었습니다.')
        return flask.render_template(template, form=form)


@app.route('/logout')
def Logout():
    flask_login.logout_user()
    return flask.redirect('/')


@app.errorhandler(401)
def Unauthorized(unused_e):
    return flask.render_template('member/login.html', form=forms.LoginForm())


@app.errorhandler(403)
def Forbidden(unused_e):
    return flask.render_template('403.html', form=forms.LoginForm()), 403


@app.errorhandler(404)
def NotFound(unused_e):
    return flask.render_template('404.html', form=forms.LoginForm()), 404


@app.route('/notfound')
def NotFound2():
    return flask.render_template('404.html', form=forms.LoginForm()), 404


class WritePost(flask_restful.Resource):

    @flask_login.login_required
    def get(self):
        board_parser = reqparse.RequestParser()
        board_parser.add_argument('board', type=int, required=True)
        args = board_parser.parse_args()
        board = models.BoardPublic.query.get(args['board'])
        if not board:
            return flask.abort(404)
        if (login.current_user.username not in admin_views.ADMIN_USERS and
                board.id in (1, 2, 3)):
            return flask.abort(403)

        if not flask.request.MOBILE:
            return flask.Response(
                flask.render_template(
                    'sub5.html',
                    m_num=5,
                    s_num=args['board'],
                    mode='write',
                    board=board,
                    form=forms.LoginForm()),
                mimetype='text/html')
        else:
            return flask.Response(
                flask.render_template(
                    'mobile/sub5.html',
                    m_num=5,
                    s_num=args['board'],
                    mode='write',
                    board=board,
                    form=forms.LoginForm()),
                mimetype='text/html')

    @flask_login.login_required
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('title', type=str)
        post_parser.add_argument('body', type=str)
        post_parser.add_argument('boardID', type=int)
        post_parser.add_argument('hidden', type=int)

        args = post_parser.parse_args()
        board = models.BoardPublic.query.get(args['boardID'])
        if not board:
            return flask.abort(404)


#        if board.id == 5 and not flask_login.current_user.ismember:
#            return flask.abort(403)

#        print (args)

        post = models.PostPublic(args['hidden'], args['title'], args['body'],
                                 flask_login.current_user, board)
        db.session.add(post)

        files = flask.request.files.getlist('files')

        for file in files:
            helper.process_file(file, post)

        db.session.commit()

        return flask.redirect('/sub/5-%d' % args['boardID'])


class ModifyPost(flask_restful.Resource):

    @flask_login.login_required
    def get(self, post_id):
        post = models.PostPublic.query.get(post_id)

        if not post:
            return flask.abort(404)

        if flask_login.current_user.id != post.writer_id:
            return flask.Response(
                flask.render_template('403.html', form=forms.LoginForm()),
                mimetype='text/html',
                status=403)

        if not flask.request.MOBILE:
            return flask.Response(
                flask.render_template(
                    'sub5.html',
                    m_num=5,
                    s_num=post.boardpublic_id,
                    mode='modify',
                    post=post,
                    board=models.BoardPublic.query.get(post.boardpublic_id),
                    form=forms.LoginForm()),
                mimetype='text/html')
        else:
            return flask.Response(
                flask.render_template(
                    'mobile/sub5.html',
                    m_num=5,
                    s_num=post.boardpublic_id,
                    mode='modify',
                    post=post,
                    board=models.BoardPublic.query.get(post.boardpublic_id),
                    form=forms.LoginForm()),
                mimetype='text/html')

    @flask_login.login_required
    def post(self, post_id):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('title', type=str)
        post_parser.add_argument('body', type=str)

        args = post_parser.parse_args()
        post = models.PostPublic.query.get(post_id)

        if not post:
            return flask.abort(404)


#        if post.boardpublic_id == 5 and not flask_login.current_user.ismember:
#            return flask.abort(403)

        if flask_login.current_user.id != post.writer_id:
            return flask.Response(
                flask.render_template(
                    'sub5_%d.html' % post.boardpublic_id,
                    m_num=5,
                    s_num=post.boardpublic_id,
                    mode='view',
                    post=post,
                    board=models.BoardPublic.query.get(post.boardpublic_id),
                    form=forms.LoginForm()),
                mimetype='text/html')

        post.title = args['title']
        post.body = args['body']

        files = flask.request.files.getlist('files')

        for file in files:
            helper.process_file(file, post)

        db.session.commit()

        return flask.redirect(flask.url_for('viewPost', id=id))


class DeletePost(flask_restful.Resource):

    @flask_login.login_required
    def post(self, post_id):
        post = models.PostPublic.query.get(post_id)
        if flask_login.current_user.id != post.writer_id:
            return 'Not Allowed', 403

        db.session.delete(post)
        db.session.commit()
        return 'Success', 200


class DeleteFile(flask_restful.Resource):

    @flask_login.login_required
    def get(self, save_name):
        file = models.File.query.filter_by(link=save_name).first()
        if file:
            if file.postpublic_id:
                posted = file.postpublic_id
                uploader = models.PostPublic.query.filter_by(id=posted).first()
                if flask_login.current_user != uploader.publicwriter:
                    return 'Not Allowed', 403
                else:
                    helper.delete_file(save_name)
                    return 'Success', 200
            elif file.postmember_id:
                posted = file.postmember_id
                uploader = models.PostMember.query.filter_by(id=posted).first()
                if flask_login.current_user != uploader.memberwriter:
                    return 'Not Allowed', 403
                else:
                    helper.delete_file(save_name)
                    return 'Success', 200
            elif file.record_id:
                posted = file.record_id
                uploader = models.Record.query.filter_by(id=posted).first()
                if flask_login.current_user != uploader.recordwriter:
                    return 'Not Allowed', 403
                else:
                    helper.delete_file(save_name)
                    return 'Success', 200
        else:
            return 'Not Allowed', 403


user_fields = {
    'id': fields.Integer,
    'nickname': fields.String,
    'username': fields.String,
}

comment_fields = {
    'id': fields.Integer,
    'author': fields.Nested(user_fields),
    'body': fields.String,
    'timestamp': fields.DateTime
}


class Comment(flask_restful.Resource):

    @flask_restful.marshal_with(comment_fields)
    def get(self, comment_id):
        comment = models.CommentPublic.query.get(comment_id)
        if comment:
            return comment
        return None, 404

    @flask_login.login_required
    @flask_restful.marshal_with(comment_fields)
    def post(self):
        comment_parser = reqparse.RequestParser()
        comment_parser.add_argument('body', type=str)
        comment_parser.add_argument('userID', type=int)
        comment_parser.add_argument('postID', type=int)

        args = comment_parser.parse_args()
        writer = models.User.query.get(args['userID'])
        post = models.PostPublic.query.get(args['postID'])
        if not post:
            return None, 404
        comment = models.CommentPublic(args['body'], writer, post)

        db.session.add(comment)
        db.session.commit()

        return comment, 201

    @flask_login.login_required
    def delete(self, comment_id):
        comment = models.CommentPublic.query.get(comment_id)
        if comment:
            if flask_login.current_user == comment.publiccommenter:
                comment.remove()
                return True, 200
            else:
                return False, 401
        else:
            return None, 404


class IdCheck(flask_restful.Resource):

    def post(self):
        idparser = reqparse.RequestParser()
        idparser.add_argument('userid', type=str)

        args = idparser.parse_args()
        user = models.User.query.filter_by(username=args['userid']).first()
        if user is not None:
            return {'duplicate': True}
        else:
            return {'duplicate': False}


member_fields = {
    'id': fields.Integer,
    'nickname': fields.String,
    'username': fields.String,
    'email': fields.String,
    'cycle': fields.Integer,
    'deptstem': fields.String,
    'deptuniv': fields.String,
    'cvpublic': fields.String,
    'cvmember': fields.String,
    'img': fields.String,
    'cover': fields.String,
    'addr': fields.String,
    'phone': fields.String,
    'birthday': fields.String,
    'social': fields.String,
    'position': fields.String
}

restricted_member_fields = {
    'id': fields.Integer,
    'nickname': fields.String,
    'cycle': fields.Integer,
    'deptstem': fields.String,
    'deptuniv': fields.String,
    'cvpublic': fields.String,
    'img': fields.String,
    'cover': fields.String,
}


class Members(flask_restful.Resource):

    @flask_restful.marshal_with(member_fields)
    def full_get(self, people):
        return people

    @flask_restful.marshal_with(restricted_member_fields)
    def restricted_get(self, people):
        return people

    def get(self):
        people = models.User.query.filter_by(ismember=1).filter(
            models.User.cycle != 0).order_by(models.User.cycle.desc()).order_by(
                models.User.nickname).all()

        if not flask_login.current_user.is_anonymous(
        ) and flask_login.current_user.ismember:
            return self.full_get(people)
        return self.restricted_get(people)


api.add_resource(Members, '/people')
api.add_resource(WritePost, '/post/write')
api.add_resource(ModifyPost, '/post/<int:post_id>/modify')
api.add_resource(DeletePost, '/post/<int:post_id>/delete')
api.add_resource(Comment, '/post/comment', '/post/comment/<int:comment_id>')
api.add_resource(IdCheck, '/member/register/idcheck')
api.add_resource(DeleteFile, '/deletefile/<string:save_name>')
