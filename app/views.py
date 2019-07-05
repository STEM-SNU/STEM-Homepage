#-*-coding: utf-8 -*-
from app import app, api, db, models, lm
from flask import render_template, Response, redirect, url_for, request, abort, flash, make_response
from flask.ext.restful import Resource, reqparse, fields, marshal_with
from flask.ext.login import login_user, logout_user, current_user, \
    login_required, AnonymousUserMixin
from flask.ext.mobility.decorators import mobile_template, mobilized
from .admin_views import admin_users
from .forms import LoginForm, RegisterForm, ModifyForm, ModifyMemberForm, \
    ResetForm, ResetPassword, FindIDForm, SearchForm, ts
from .helper import process_file, delete_file, send_email
from .member_help import Current

from sqlalchemy import and_

import datetime
import pytz

class AnonymousUser(AnonymousUserMixin):
    def __init__(self):
        super().__init__()
        self.member = None

lm.anonymous_user = AnonymousUser

@lm.user_loader
def load_user(id):
    return models.User.query.get(int(id))

robot_text = open('robots.txt','r').read()
@app.route('/robots.txt')
def robots():
    resp = make_response(robot_text)
    resp.headers['content-type'] = 'text/plain'
    return resp

@app.route('/')
@mobile_template('/{mobile/}main.html')
def main(template):
    bannerRec = models.Banner.query.order_by(models.Banner.id.desc()).all()

    boardpublic_ids = [1, 2, 4, 5]
    # 1 : Notice, 2 : News, 4 : Freeboard, 5 : Q&A

    boardRec = list()
    boards = list()

    for bid in boardpublic_ids:
        board = models.BoardPublic.query.get(bid)
        if not board:
            continue
        boards.append(board)
        boardRec.append(
            db.session.query(models.PostPublic)
                      .filter_by(boardpublic_id=bid)
                      .order_by(models.PostPublic.timestamp.desc())
                      .limit(5).all())

    for rec in boardRec:
        for post in rec:
            now = datetime.datetime.utcnow()
            post.date = post.timestamp.strftime('%m.%d')
            if now - post.timestamp < datetime.timedelta(days=3):
                post.new = True

    return render_template(template,
                           bannerRec=bannerRec,
                           boardRec=boardRec,
                           boards=boards,
                           form=LoginForm())

@app.route('/reset', methods=["GET", "POST"])
def reset():
    form = ResetForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(email=form.email.data).first()
        if user is not None:
	        if (form.username.data == user.username) and (form.nickname.data == user.nickname):
		        subject = "Password reset requested"

		        token = ts.dumps(user.email, salt='recover-key')

		        recover_url = url_for(
		            'reset_with_token',
		            token=token,
		            _external=True)

		        html = render_template(
		            'member/recover.html',
		            recover_url=recover_url)

		        send_email(user.email, subject, html)

		        return render_template('reset_finish.html')
	        else:
	        	flash('해당하는 회원 정보가 존재하지 않습니다.')
	        	return redirect('/reset')
        else:
        	flash('해당하는 회원 정보가 존재하지 않습니다.')
        	return redirect('/reset')
    return render_template('reset.html', form=form)

@app.route('/findID', methods=["GET", "POST"])
def findid():
    form = FindIDForm()
    if form.validate_on_submit():
        user = models.User.query.filter_by(email=form.email.data).first()
        if user is not None:
	        if (form.nickname.data == user.nickname):
		        return render_template('findID_result.html', user=user)
	        else:
	        	flash('해당하는 회원 정보가 존재하지 않습니다.')
	        	return redirect('/findID')
        else:
        	flash('해당하는 회원 정보가 존재하지 않습니다.')
        	return redirect('/findID')
    return render_template('findID.html', form=form)

@app.route('/reset/<token>', methods=["GET", "POST"])
def reset_with_token(token):
    try:
        email = ts.loads(token, salt="recover-key", max_age=3600)
    except:
        abort(404)

    form = ResetPassword()

    if form.validate_on_submit():
        user = models.User.query.filter_by(email=email).first_or_404()

        user.password = form.password.data

        db.session.add(user)
        db.session.commit()

        return render_template('reset_finish.html')

    return render_template('reset_with_token.html', form=form, token=token)

@app.route('/m_login', methods=['GET', 'POST'])
def moblogin():
    form = LoginForm()
    if form.validate_on_submit():
        login_user(form.user)
        if current_user.ismember:

            if not current_user.last_mod:
                flash('회원정보 수정내역이 없습니다. 정보를 업데이트해주세요.')
            elif datetime.datetime.utcnow() - current_user.last_mod > datetime.timedelta(days=90):
                flash('회원정보를 수정한 지 90일이 지났습니다. 정보를 업데이트해주세요.')

            if request.host in ['gongwoo.snu.ac.kr', 'eng-stem.snu.ac.kr', 'honor.snu.ac.kr']:
                if (request.referrer.find('/stem/') > -1) or (request.referrer.find('/stem-') > -1):
                    return redirect(request.referrer)
                else:
                    return redirect('/stem')
            else:
                return redirect('/stem')

        return redirect('/')

    return render_template('member/mlogin.html', form=form)

@app.route('/vm_confirm')
def vmConfirm():
    key = request.args.get('key')
    if not key:
        abort(404)
    if current_user.is_anonymous() or not current_user.ismember:
        return render_template('vm.html', form=LoginForm())
    return render_template('vm_confirm.html', form=LoginForm(), key=key)

@app.route('/apply')
def stemApply():
    fout = open('apply_log.log', 'a+')
    fout.write('Page viewed on ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
    if datetime.datetime.now() < datetime.datetime(2016,3,10):
        display = 1
    else:
        display = 2
    fout.close()
    return render_template('apply.html', form=LoginForm(), display=display)

@app.route('/sub/<string:sub>')
def showSub(sub):
    mNum = sub[0]
    sNum = sub[2]
    if mNum == '5':
        return redirect('/sub/' + sub + '/1') # showBoard(sub, 1)
    elif mNum == '2' and sNum == '5':
        year = datetime.date.today().year
        return redirect('/sub/2-5/%d' % year)
    if request.MOBILE == False:
        return render_template('sub' + mNum + '_' + sNum + '.html',
                               current=Current(),
                               mNum=int(mNum),
                               sNum=int(sNum),
                               form=LoginForm())
    else:
        return render_template('mobile/sub' + mNum + '_' + sNum + '.html',
                               current=Current(),
                               mNum=int(mNum),
                               sNum=int(sNum),
                               form=LoginForm())

@app.route('/sub/<string:sub>/<int:page>', methods=['GET', 'POST'])
def showBoard(sub, page):
    mNum = sub[0]
    sNum = sub[2]
    searchform = SearchForm()
    if mNum == '5':
        if sNum == '3':
            abort(404)

        pagenation = models.PostPublic.query.filter_by(
            boardpublic_id=int(sNum)).order_by(models.PostPublic.timestamp.desc()) \
                               .paginate(page, per_page=10)

        if not searchform.searchstr.data == '':
            if searchform.search.data == 'title':
                pagenation = models.PostPublic.query.filter(
                    and_(models.PostPublic.boardpublic_id == int(sNum), models.PostPublic.title.contains(searchform.searchstr.data))) \
                    .order_by(models.PostPublic.timestamp.desc()).paginate(page, per_page=10)
            if searchform.search.data == 'writer':
                user_id = models.User.query.filter(models.User.nickname == searchform.searchstr.data).first()
                if not user_id is None:
                    user_id = user_id.id
                else:
                    user_id = '-1'
                pagenation = models.PostPublic.query.filter(
                    and_(models.PostPublic.boardpublic_id == int(sNum), models.PostPublic.writer_id == user_id)) \
                    .order_by(models.PostPublic.timestamp.desc()).paginate(page, per_page=10)
            if searchform.search.data == 'content':
                pagenation = models.PostPublic.query.filter(
                    and_(models.PostPublic.boardpublic_id == int(sNum), models.PostPublic.body.contains(searchform.searchstr.data))) \
                    .order_by(models.PostPublic.timestamp.desc()).paginate(page, per_page=10)

        board = models.BoardPublic.query.get(int(sNum))
        limit = datetime.datetime.utcnow() - datetime.timedelta(days=5)

        if not board:
            abort(404)

        if request.MOBILE == False:
            return render_template('sub' + mNum + '.html',
                                   page=page, totalpage=pagenation.pages,
                                   posts=pagenation.items, board=board,
                                   mNum=int(mNum), sNum=int(sNum), limit=limit,
                                   form=LoginForm(), searchform=searchform, admin_users=admin_users)
        else:
            return render_template('/mobile/sub' + mNum + '.html',
                                   page=page, totalpage=pagenation.pages,
                                   posts=pagenation.items, board=board,
                                   mNum=int(mNum), sNum=int(sNum), limit=limit,
                                   form=LoginForm(), searchform=searchform, admin_users=admin_users)

    elif mNum == '2' and sNum == '5':
        return showHistory(sub, page)

    return showSub(sub)


def showHistory(sub, page):
    mNum = sub[0]
    sNum = sub[2]

    year = datetime.date.today().year
    yearRec = [n for n in range(2010, datetime.date.today().year + 1)]
    if not page in yearRec:
        page = year
    start = datetime.datetime(page, 1, 1, tzinfo=pytz.utc)
    end = datetime.datetime(page, 12, 31, tzinfo=pytz.utc)
    allRec = db.session.query(models.History) \
                       .filter(models.History.starttime.between(start, end)) \
                       .order_by(models.History.starttime).all()

    for post in allRec:
        post.period = post.starttime.strftime('%m.%d')
        if post.endtime and post.endtime != '':
            endDate = datetime.datetime.utcfromtimestamp(float(post.endtime))
            post.period = post.period + ' ~ ' + endDate.strftime('%m.%d')

    if request.MOBILE == False:
        return render_template('sub2_5.html',
                               mNum=int(mNum), sNum=int(sNum), form=LoginForm(),
                               years=yearRec, page=page, history=allRec, admin_users=admin_users)
    else:
        return render_template('mobile/sub2_5.html',
                               mNum=int(mNum), sNum=int(sNum), form=LoginForm(),
                               years=yearRec, page=page, history=allRec, admin_users=admin_users)


@app.route('/post/<int:id>')
@app.route('/post/<int:id>/view')
def viewPost(id):
    post = models.PostPublic.query.get(id)
    if not post or not post.boardpublic:
        return abort(404)
#    if post.boardpublic_id == 5 and not current_user.ismember:
#        return abort(403)
    if post.hidden == True:
        if current_user.is_anonymous():
            return abort(403)
        elif not ((current_user.id == post.writer_id) or (current_user.username in admin_users)):
            return abort(404)
    post.hitCount = post.hitCount + 1
    board = models.BoardPublic.query.get(post.boardpublic_id)
    db.session.commit()
    prev = models.PostPublic.query.filter(
        and_(models.PostPublic.id < id, models.PostPublic.boardpublic_id == post.boardpublic_id)). \
        order_by(models.PostPublic.timestamp.desc()).first()
    next = models.PostPublic.query.filter(
        and_(models.PostPublic.id > id, models.PostPublic.boardpublic_id == post.boardpublic_id)). \
        order_by(models.PostPublic.timestamp.asc()).first()

    if request.MOBILE == False:
        return render_template('sub5.html', mNum=5, sNum=post.boardpublic_id,
                               mode='view', post=post, board=board, prev=prev,
                               next=next, form=LoginForm(), admin_users=admin_users)
    else:
        return render_template('mobile/sub5.html', mNum=5, sNum=post.boardpublic_id,
                               mode='view', post=post, board=board, prev=prev,
                               next=next, form=LoginForm(), admin_users=admin_users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        login_user(form.user)
        if current_user.ismember:

            if not current_user.last_mod:
                flash('회원정보 수정내역이 없습니다. 정보를 업데이트해주세요.')
            elif datetime.datetime.utcnow() - current_user.last_mod > datetime.timedelta(days=90):
                flash('회원정보를 수정한 지 90일이 지났습니다. 정보를 업데이트해주세요.')

            if request.host in ['gongwoo.snu.ac.kr', 'eng-stem.snu.ac.kr', 'honor.snu.ac.kr']:
                if request.referrer.find('/stem/') > -1:
                    return redirect(request.referrer)
                else:
                    return redirect('/stem')
            else:
                return redirect('/stem')

        return redirect('/')

    return render_template('member/login.html', form=form)

@app.route('/member/register', methods=['GET', 'POST'])
def register():
    if not current_user.is_anonymous():
        return abort(403)

    registerform = RegisterForm()
    form = LoginForm()
    if registerform.validate_on_submit():
        login_user(registerform.user)
        if current_user.ismember:
            flash('가입을 축하드립니다. 회원님의 정보를 업데이트해주세요.')
        return redirect('/')
    else:
        if request.MOBILE == False:
            return render_template('member/register.html', registerform=form,
                form=form)
        else:
            return render_template('mobile/member/register.html', registerform=form,
                form=form)


@app.route('/member/modify', methods=['GET', 'POST'])
@mobile_template('/{mobile/}member/modify.html')
@login_required
def modify(template):
    if current_user.ismember:
        form = ModifyMemberForm()
        departments = models.DeptUniv.query.all()
        deptstems = models.DeptStem.query.all()
        if form.validate_on_submit():
            return render_template(
                template, form=form,
                departments=departments, deptstems=deptstems,
                message='수정이 완료되었습니다.')
        return render_template(
            template, form=form,
            departments=departments,
            deptstems=deptstems)
    else:
        form = ModifyForm()
        if form.validate_on_submit():
            return render_template(
                template, form=form,
                message='수정이 완료되었습니다.')
        return render_template(template, form=form)

@app.route('/logout')
def logout():
    form = LoginForm()
    logout_user()
    return redirect('/')

@app.errorhandler(401)
def unauthorized(e):
    if request.MOBILE == True :
        form = LoginForm()
        return render_template('/member/mlogin.html', form=form)
    else :
        form = LoginForm()
        return render_template('member/login.html', form=form)

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html', form=LoginForm()), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', form=LoginForm()), 404

@app.route('/notfound')
def not_found2():
    return render_template('404.html', form=LoginForm()), 404



class WritePost(Resource):
    @login_required
    def get(self):
        boardParser = reqparse.RequestParser()
        boardParser.add_argument('board', type=int, required=True)
        args = boardParser.parse_args()
        board = models.BoardPublic.query.get(args['board'])
        if not board:
            return abort(404)
        if board.id == 1 and not current_user.username in admin_users:
            return abort(403)
        if board.id == 2 and not current_user.username in admin_users:
            return abort(403)
        if board.id == 3:
            return abort(403)

        if request.MOBILE == False:
            return Response(
                render_template('sub5.html', mNum=5, sNum=args['board'],
                                mode='write', board=board, form=LoginForm()),
                mimetype='text/html')
        else:
            return Response(
                render_template('mobile/sub5.html', mNum=5, sNum=args['board'],
                                mode='write', board=board, form=LoginForm()),
                mimetype='text/html')

    @login_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('title', type=str)
        postParser.add_argument('body', type=str)
        postParser.add_argument('boardID', type=int)
        postParser.add_argument('hidden', type=int)

        args = postParser.parse_args()
        board = models.BoardPublic.query.get(args['boardID'])
        if not board:
            return abort(404)
#        if board.id == 5 and not current_user.ismember:
#            return abort(403)

#        print (args)

        post = models.PostPublic(
            args['hidden'], args['title'], args['body'], current_user,
            board)
        db.session.add(post)

        files = request.files.getlist("files")

        for file in files:
            process_file(file, post)

        db.session.commit()

        return redirect('/sub/5-%d' % args['boardID'])


class ModifyPost(Resource):
    @login_required
    def get(self, id):
        post = models.PostPublic.query.get(id)

        if not post:
            return abort(404)

        if current_user.id != post.writer_id:
            return Response(
                render_template('403.html', form=LoginForm()),
                mimetype='text/html', status=403)

        if request.MOBILE == False:
            return Response(
                render_template('sub5.html', mNum=5, sNum=post.boardpublic_id,
                                mode='modify', post=post,
                                board=models.BoardPublic.query.get(post.boardpublic_id),
                                form=LoginForm()),
                mimetype='text/html')
        else:
            return Response(
                render_template('mobile/sub5.html', mNum=5, sNum=post.boardpublic_id,
                                mode='modify', post=post,
                                board=models.BoardPublic.query.get(post.boardpublic_id),
                                form=LoginForm()),
                mimetype='text/html')


    @login_required
    def post(self, id):
        postParser = reqparse.RequestParser()
        postParser.add_argument('title', type=str)
        postParser.add_argument('body', type=str)

        args = postParser.parse_args()
        post = models.PostPublic.query.get(id)

        if not post:
            return abort(404)

#        if post.boardpublic_id == 5 and not current_user.ismember:
#            return abort(403)

        if current_user.id != post.writer_id:
            return Response(
                render_template('sub5_%d.html' % post.boardpublic_id, mNum=5,
                                sNum=post.boardpublic_id, mode='view', post=post,
                                board=models.BoardPublic.query.get(post.boardpublic_id),
                                form=LoginForm()),
                mimetype='text/html')

        post.title = args['title']
        post.body = args['body']

        files = request.files.getlist("files")

        for file in files:
            process_file(file, post)

        db.session.commit()

        return redirect(url_for('viewPost', id=id))



class DeletePost(Resource):
    @login_required
    def post(self, id):
        post = models.PostPublic.query.get(id)
        if current_user.id != post.writer_id:
            return "Not Allowed", 403

        db.session.delete(post)
        db.session.commit()
        return "Success", 200

class DeleteFile(Resource):
    @login_required
    def get(self, save_name):
        file = models.File.query.filter_by(link=save_name).first()
        if not file is None:
            if not file.postpublic_id is None:
                posted = file.postpublic_id
                uploader = models.PostPublic.query.filter_by(id=posted).first()
                if current_user != uploader.publicwriter:
                    return "Not Allowed", 403
                else:
                    delete_file(save_name)
                    return "Success", 200
            elif not file.postmember_id is None:
                posted = file.postmember_id
                uploader = models.PostMember.query.filter_by(id=posted).first()
                if current_user != uploader.memberwriter:
                    return "Not Allowed", 403
                else:
                    delete_file(save_name)
                    return "Success", 200
            elif not file.record_id is None:
                posted = file.record_id
                uploader = models.Record.query.filter_by(id=posted).first()
                if current_user != uploader.recordwriter:
                    return "Not Allowed", 403
                else:
                    delete_file(save_name)
                    return "Success", 200
        else:
            return "Not Allowed", 403

api.add_resource(DeleteFile, '/deletefile/<string:save_name>')

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


class Comment(Resource):
    @marshal_with(comment_fields)
    def get(self, commentID):
        comment = models.CommentPublic.query.get(commentID)
        if comment:
            return comment
        return None, 404

    @login_required
    @marshal_with(comment_fields)
    def post(self):
        commentParser = reqparse.RequestParser()
        commentParser.add_argument('body', type=str)
        commentParser.add_argument('userID', type=int)
        commentParser.add_argument('postID', type=int)

        args = commentParser.parse_args()
        writer = models.User.query.get(args['userID'])
        post = models.PostPublic.query.get(args['postID'])
        if not post:
            return None, 404
        comment = models.CommentPublic(
            args['body'], writer, post)

        db.session.add(comment)
        db.session.commit()

        return comment, 201

    @login_required
    def delete(self, id):
        comment = models.CommentPublic.query.get(id)
        if comment:
            if current_user == comment.publiccommenter:
                comment.remove()
                return True, 200
            else:
                return False, 401
        else:
            return None, 404


class IdCheck(Resource):
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


class Members(Resource):
    @marshal_with(member_fields)
    def full_get(self, people):
        return people

    @marshal_with(restricted_member_fields)
    def restricted_get(self, people):
        return people

    def get(self):
        people = models.User.query.filter_by(ismember=1) \
                           .filter(models.User.cycle != 0) \
                           .order_by(models.User.cycle.desc()) \
                           .order_by(models.User.nickname).all()

        if not current_user.is_anonymous() and current_user.ismember:
            return self.full_get(people)
        return self.restricted_get(people)

api.add_resource(Members, '/people')
api.add_resource(WritePost, '/post/write')
api.add_resource(ModifyPost, '/post/<int:id>/modify')
api.add_resource(DeletePost, '/post/<int:id>/delete')
api.add_resource(Comment, '/post/comment', '/post/comment/<int:id>')
api.add_resource(IdCheck, '/member/register/idcheck')
