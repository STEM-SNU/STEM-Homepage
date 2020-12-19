import os
import pytz
import uuid
import math

from flask import Blueprint, render_template, abort, current_app, redirect, \
    request, url_for, flash
from jinja2 import TemplateNotFound
from flask.ext.login import login_user, logout_user, current_user, \
    login_required
from flask.ext.restful import Api, Resource, reqparse, fields, marshal_with
from flask.ext.mail import Mail, Message
from functools import wraps

from .forms import ModifyMemberForm, ModifyStemDeptOnly
from .helper import send_email
from .member_help import Current

from werkzeug import secure_filename

from sqlalchemy import or_, and_, not_
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import load_only
from datetime import datetime, timedelta

from stem import db, models, app, helper, notification, mail

from operator import itemgetter

member_app = Blueprint('member_app', __name__,
                       template_folder='templates/memberapp')
api = Api(member_app)

def member_required(func):
    @wraps(func)
    @login_required
    def decorated_view(*args, **kwargs):
        if not current_user.ismember:
            return abort(403)
        return func(*args, **kwargs)
    return decorated_view

def note(type):
    if type == 0:
        sent_notes = models.Note.query.filter_by(sent_id=current_user.id) \
            .filter_by(sent_del=0).order_by(models.Note.timestamp.desc()) \
            .all()
        return sent_notes
    else:
        received_notes = models.Note.query.filter_by(recv_id=current_user.id) \
            .filter_by(recv_del=0).order_by(models.Note.timestamp.desc()) \
            .all()
        return received_notes


@member_app.route('-<string:cloud>')
def tonas(cloud):
    if request.MOBILE == False:
        if cloud == 'nas':
            return redirect('https://'+request.host+':8088')
        elif cloud == 'file':
            return redirect('https://'+request.host+':8088/file')
        elif cloud == 'photo':
            return redirect('https://'+request.host+':8089/photo')
        else:
            abort(404)
    else:
        if cloud == 'nas':
            flash('모바일 환경에서는 클라우드 데스크톱이 지원되지 않습니다.')
            return redirect(url_for('.tonas', cloud='file'))
        elif cloud in ['file', 'photo']:
            if current_user.is_anonymous():
                abort(401)
            else:
                if current_user.ismember:
                    return render_template('mobile_nas.html', member=current_user, nav_id=4,
                    notifications=notification.Generate(current_user),
                    prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
                    group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
                    current=Current(), snotes=note(0), rnotes=note(1), cloud=cloud)
                else:
                    abort(403)
        else:
            abort(404)

@member_app.route('/')
@member_required
def main():
    memoes = models.Memo.query.order_by(models.Memo.id.desc()).limit(3).all()
    
    personal_board = models.BoardMember.query.filter(and_(models.BoardMember.group_id==10, models.BoardMember.owner==current_user)).first()
    
    preferred_boards = current_user.preferred_boards

    recent_posts = models.PostMember.query.order_by(models.PostMember.id.desc()).limit(10).all()

    try:
        return render_template(
            'dashboard.html', current_user=current_user,
            nav_id=1, notifications=notification.Generate(current_user), memoes=memoes, snotes=note(0), rnotes=note(1),
            personal_board = personal_board, preferred_boards = preferred_boards,
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(), 
            recent_posts=recent_posts, current=Current())
    except TemplateNotFound:
        abort(404)

@member_app.route('/search')
@member_required
def search():
    search_string = request.args.get('q')
    if search_string:
        matched_people = models.User.query.filter(and_(models.User.ismember==True,
                            models.User.nickname.like("%"+search_string+"%"))). \
                         order_by(models.User.cycle).order_by(models.User.nickname).all()
        matched_people_ids = []
        for person in matched_people:
            id = person.id
            matched_people_ids.append(id)
        matched_boards = models.BoardMember.query. \
                         filter(or_(models.BoardMember.title.like("%"+search_string+"%"),
                            models.BoardMember.owner_id.in_(matched_people_ids))). \
                         order_by(models.BoardMember.group_id).all()
    else:
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(url_for('.main'))


    try:
        return render_template('search.html', matched_people=matched_people, matched_boards=matched_boards,
            notifications=notification.Generate(current_user),snotes=note(0), rnotes=note(1),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(), current=Current(),
            search_string = search_string)
    except TemplateNotFound:
        abort(404) 

@member_app.route('/mms/completion_state', methods=['GET','POST'])
@member_required
def MoveToCompletionState():
    if request.args:
        name = request.args.get('name')
        cycle = request.args.get('cycle')
        
        if not (name or cycle):
            abort(404)

        members = models.User.query.filter_by(cycle=cycle).all()
        mem_id=[]
        for member in members:
            if member.nickname == name:
                mem_id.append(member.id)
        if len(mem_id) > 1:
            flash(str(len(mem_id)) + ' results are found. Search again for the next result.')
            for n in range(len(mem_id)):
                if mem_id[n] == int(request.referrer.split("/")[::-1][0]):
                    n = (n+1)%(len(mem_id))
                    moveid = mem_id[n]
                    break
                else:
                    moveid = mem_id[0]
        elif len(mem_id) == 1:
            moveid = mem_id[0]
        else:
            moveid = request.referrer.split("/")[::-1][0]
    else:
        moveid = current_user.id

    return redirect(url_for('.CompletionState', mem_id_shown=moveid))

@member_app.route('/mms/completion_state/<int:mem_id_shown>')
@member_required
def CompletionState(mem_id_shown):
    if (not current_user.id in Current().page_manager_ids()) and (current_user.id != mem_id_shown):
        abort(403)

    recentyear = Current().year
    recentsemester = Current().semester

    correspondmember = models.User.query.filter_by(id=mem_id_shown).first()

    activities = correspondmember.activities
    conferences = correspondmember.conferences
    quarters = models.Quarter
    scoretable = models.Member_Activity
    statetable = models.Member_Conference

    scoresum = 0
    statesum = 0
    quarter_id_list = []
    completion = []

    for activity in activities:
         if (not activity.quarter_id in quarter_id_list):
             quarter_id_list.append(activity.quarter_id)


    for conference in conferences:
        if (not conference.quarter_id in quarter_id_list):
            quarter_id_list.append(conference.quarter_id)

    quarter_id_list.sort(reverse=True)

    for id in quarter_id_list:
        for activity in activities:
            if activity.quarter_id == id:
                score = scoretable.query.filter_by(activity_id=activity.id).filter_by(member_id=mem_id_shown).first().score
                scoresum = scoresum + score
        for conference in conferences:
            if conference.quarter_id == id:
                state = statetable.query.filter_by(conference_id=conference.id).filter_by(member_id=mem_id_shown).first().state
                if state == 1:
                    statesum = statesum + 1/3
                elif state in [0,2]:
                    pass
                elif state == 3:
                    statesum = statesum + 1/3
                elif state == 4:
                    statesum = statesum + 1
                else:
                    statesum = statesum + 4/3
        quarter = models.Quarter.query.filter_by(id=id).first()
        completion.append([id, quarter.year, quarter.semester, scoresum, quarter.activity_score, round(statesum,1), quarter.conference_absence])
        scoresum = 0
        statesum = 0

    completion.sort(key=itemgetter(1,2), reverse=True)

    try:
        return render_template('memberapp/mms/completion_state.html', member=current_user,
                notifications=notification.Generate(current_user), nav_id=2, current=Current(), 
                mem_id_shown=mem_id_shown, correspondmember=correspondmember, scoretable=scoretable, 
                statetable=statetable, activities=activities, conferences=conferences,
                completion=completion, quarter_id_list=quarter_id_list, quarters=quarters, 
                recentyear=recentyear, recentsemester=recentsemester, snotes=note(0), rnotes=note(1),
                prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
                group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except TemplateNotFound:
        abort(404)

@member_app.route('/mms/completion_criterion')
@member_required
def MoveRecentCompletionCriterion():
    recentyear = Current().year
    recentsemester = Current().semester

    return redirect(url_for('.MgmtCompletionCriterion', year=recentyear, semester=recentsemester))

@member_app.route('/mms/completion_criterion/<int:year>/<int:semester>', methods=['GET', 'POST'])
@member_required
def MgmtCompletionCriterion(year, semester):
    quarters = models.Quarter.query.order_by(models.Quarter.year.desc()).order_by(models.Quarter.semester.desc()).all()
    quarter = models.Quarter.query.filter_by(year=year).filter_by(semester=semester).first()

    if not quarter:
        return abort(404)

    regularactscore = 0

    for activity in quarter.activities:
        if activity.type==0:
            regularactscore = regularactscore + activity.totalscore

    try:
        return render_template('memberapp/mms/mgmt_completion_criterion.html', member=current_user,
         notifications=notification.Generate(current_user), nav_id=2, current=Current(),
         year=year, semester=semester, quarter=quarter, quarters=quarters,
         regularactscore=regularactscore, snotes=note(0), rnotes=note(1),
         prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
         group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except TemplateNotFound:
        abort(404)

@member_app.route('/mms/mgmt/completion_record', methods=['GET', 'POST'])
@member_required
def MoveToMgmtCompletionRecordFirst():
    recentyear = Current().year
    recentsemester = Current().semester
    return redirect(url_for('.MgmtCompletionRecord', year = recentyear, semester=recentsemester))

@member_app.route('/mms/mgmt/completion_record/<int:year>/<int:semester>', methods=['GET', 'POST'])
@member_required
def MgmtCompletionRecord(year, semester):
    if not current_user.id in Current().page_manager_ids():
        abort(404)

    recentyear = Current().year
    recentsemester = Current().semester
    quarters = models.Quarter.query.order_by(models.Quarter.year.desc()).order_by(models.Quarter.semester.desc()).all()

    quarter = models.Quarter.query.filter_by(year=year).filter_by(semester=semester).first_or_404()

    if not quarter:
        abort(404)

    actIDset =[]
    for activity in quarter.activities:
        actIDset.append(activity.id)
    confIDset = []
    for conference in quarter.conferences:
        confIDset.append(conference.id)

    scoretable = models.Member_Activity.query.filter(models.Member_Activity.activity_id.in_(actIDset)).all()
    statetable = models.Member_Conference.query.filter(models.Member_Conference.conference_id.in_(confIDset)).all()

    try:
        return render_template('memberapp/mms/mgmt_completion_record.html', member=current_user, notifications=notification.Generate(current_user), 
            nav_id=2, current=Current(), quarters=quarters, quarter=quarter, scoretable=scoretable, statetable=statetable, year=year, 
            recentyear=recentyear, semester=semester, recentsemester=recentsemester, snotes=note(0), rnotes=note(1),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except TemplateNotFound:
        abort(404)

@member_app.route('/mms/mgmt/completion_record/member_addlist')
@member_required
def MemberAddList():
    if not current_user.id in Current().page_manager_ids():
        abort(404)

    members = models.User.query.filter_by(ismember=1).order_by(models.User.cycle).all()

    return render_template('memberapp/mms/mgmt_memberaddlist.html', members=members, snotes=note(0), rnotes=note(1))

@member_app.route('/mms/mgmt/completion_record/member_recordtable/<int:year>/<int:semester>')
@member_required
def MemberRecordTable(year, semester):
    if not current_user.id in Current().page_manager_ids():
        abort(404)

    scoresum = 0
    statesum = 0
    scoretable = models.Member_Activity
    statetable = models.Member_Conference
    completion = []

    recentyear = Current().year
    recentsemester = Current().semester
    quarter = models.Quarter.query.filter_by(year=recentyear).filter_by(semester=recentsemester).first()
    qid = quarter.id

    if year == recentyear and semester == recentsemester:
        record_members = Current().active("actives")
    else:
        quarter = models.Quarter.query.filter_by(year=year).filter_by(semester=semester).first_or_404()
        qid = quarter.id
        IDset =[]
        for qactivity in quarter.activities:
            memacts = models.Member_Activity.query.filter_by(activity_id=qactivity.id).all()
            for memact in memacts:
                IDset.append(memact.member_id)

        for qconference in quarter.conferences:
            memcons = models.Member_Conference.query.filter_by(conference_id=qconference.id).all()
            for memcon in memcons:
                IDset.append(memcon.member_id)
        record_members = models.User.query.filter(models.User.id.in_(IDset)).order_by(models.User.cycle).order_by(models.User.nickname).all()

    for record_member in record_members:
        activities = record_member.activities
        conferences = record_member.conferences

        for activity in activities:
            if activity.quarter_id == qid:
                score = scoretable.query.filter_by(activity_id=activity.id).filter_by(member_id=record_member.id).first().score
                scoresum = scoresum + score
        for conference in conferences:
            if conference.quarter_id == qid:
                state = statetable.query.filter_by(conference_id=conference.id).filter_by(member_id=record_member.id).first().state
                if state == 1: # 지각인 경우
                    statesum = statesum + 1/3
                elif state in [0,2]: # 출석이나 공결인 경우
                    pass
                elif state == 3: # 공결하였으나 회의록 확인을 달지 않은 경우
                    statesum = statesum + 1/3
                elif state == 4: # 결석한 경우
                    statesum = statesum + 1
                else: # 나머지 state는 모두 결석하였고 회의록 확인을 달지 않은 경우
                    statesum = statesum + 4/3
        completion.append([record_member.deptstem.name, record_member.nickname, record_member.cycle, scoresum, quarter.activity_score, round(statesum,1), quarter.conference_absence])
        scoresum = 0
        statesum = 0

    return render_template('memberapp/mms/mgmt_memberrecordtable.html', completion=completion)

@member_app.route('/mms/active', methods=['GET', 'POST'])
@member_required
def ActiveApply():
    form = ModifyMemberForm()
    
    departments = models.DeptUniv.query.all()
    stem_departments = models.DeptStem.query.filter(or_(models.DeptStem.id==1, models.DeptStem.id==3, models.DeptStem.id==4)).all()

    request = models.Configuration.query.filter_by(option='active_apply').first().value

    actives = Current().active("actives")

    try:
        if form.validate_on_submit():
            return render_template('memberapp/mms/active_apply.html', current_user=current_user,
             notifications=notification.Generate(current_user), nav_id=2, current=Current(),
             form=form, deptunivs=departments, deptstems=stem_departments,
             is_active=request, message='신청이 완료되었습니다.',
             snotes=note(0), rnotes=note(1))
        return render_template('memberapp/mms/active_apply.html', current_user=current_user,
             notifications=notification.Generate(current_user), nav_id=2, current=Current(),
             form=form, deptunivs=departments, deptstems=stem_departments,
             is_active=request, snotes=note(0), rnotes=note(1), actives=actives)
    except TemplateNotFound:
        abort(404)

@member_app.route('/mms/active/activation', methods=['GET', 'POST'])
@member_required
def ActiveActivation():
    if current_user.id in Current().page_manager_ids():
        if 'is_active' in request.form:
            isactive = models.Configuration.query.filter_by(option='active_apply').all()
            newval = models.Configuration('active_apply', True)
            for i in isactive:
                db.session.delete(i)
            db.session.add(newval)
            db.session.commit()
        else:
            isactive = models.Configuration.query.filter_by(option='active_apply').all()
            newval = models.Configuration('active_apply', False)
            for i in isactive:
                db.session.delete(i)
            db.session.add(newval)
            db.session.commit()
        return redirect(url_for('.ActiveApply'))
    return abort(403)

@member_app.route('/mms/mgmt/active_registration', methods=['GET', 'POST'])
@member_required
def MgmtActiveRegistration():

    form = ModifyStemDeptOnly()

    if not current_user.id in Current().page_manager_ids():
        abort(403)

    try:
        if form.is_submitted():
            if form.memberid.data == -1:
                users = models.User.query.filter(or_(models.User.deptstem_id==1,models.User.deptstem_id==3,models.User.deptstem_id==4)).all()
                for user in users :
                    user.deptstem_id = form.stem_department.data
                    db.session.add(user)
                db.session.commit()
            else:
                user = models.User.query.filter(models.User.id == form.memberid.data).first_or_404()
                user.deptstem_id = form.stem_department.data
                db.session.add(user)
                db.session.commit()
            return render_template('memberapp/mms/mgmt_registration.html', member=current_user, notifications=notification.Generate(current_user), nav_id=2, form=form, current=Current(), 
                snotes=note(0), rnotes=note(1),
                prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
                group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
        return render_template('memberapp/mms/mgmt_registration.html', member=current_user, notifications=notification.Generate(current_user), nav_id=2, form=form, current=Current(), 
                snotes=note(0), rnotes=note(1),
                prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
                group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except TemplateNotFound:
        abort(404)

@member_app.route('/people/_<int:cycle>')
@member_required
def showPeople(cycle):
    try:
        return render_template(
            'memberapp/people.html', member=current_user, nav_id=3,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            cycle=cycle, current=Current(), snotes=note(0), rnotes=note(1))
    except TemplateNotFound:
        abort(404)

@member_app.route('/people/<int:id>')
@member_required
def showMember(id):
    try:
        mem = models.User.query.get(id)
        if not mem:
            abort(403)

        comments = models.Member_Comment.query.filter(models.Member_Comment.member_id==mem.id).order_by(models.Member_Comment.timestamp.desc()).all()

        return render_template(
            'memberapp/profile.html', member=current_user,
            profile_member=mem, nav_id=3, cycle=mem.cycle,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=Current(), comments=comments, snotes=note(0), rnotes=note(1))
    except TemplateNotFound:
        abort(404)

@member_app.route('/calendar')
@member_required
def showCalendar():
    try:
        return render_template(
            'calendar.html', member=current_user, nav_id=5,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=Current(), snotes=note(0), rnotes=note(1))
    except TemplateNotFound:
        abort(404)

@member_app.route('/stememo')
@member_required
def gotoSTEMemoPage1():
    return redirect(url_for('.showSTEMemo', page = 1))

@member_app.route('/stememo/<int:page>')
@member_required
def showSTEMemo(page):

    if page == 0 :
        abort(404)

    totalNum = len(models.Memo.query.all())
    end = totalNum - 10 * (page - 1)
    start = totalNum - 10 * page
    maxpage = math.ceil(totalNum / 10)

    if start < 1 :
        start = 0
    if end < 1 :
        abort(404)

    memoes = models.Memo.query.all()[start:end:][::-1]

    try:
        mem = models.User
        return render_template(
            'memo.html',
            current_user=current_user, nav_id=6,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(), 
            memoes=memoes, maxpage = maxpage, page=page, totalNum=totalNum, current=Current(),
            snotes=note(0), rnotes=note(1))
    except TemplateNotFound:
        abort(404)

@member_app.route('/board')
@member_required
def showBoardList():
    try:
        if request.args.get('gid'):
            gid = request.args.get('gid')
            bgroups = models.Bgroup.query.filter_by(id=gid).first()
        else:
            bgroups = models.Bgroup.query.all()
        return render_template(
            'post_group.html',
            current_user=current_user, nav_id=7, bgroups=bgroups,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=Current(), snotes=note(0), rnotes=note(1))
    except TemplateNotFound:
        abort(404)

@member_app.route('/board/personal/<int:member_id>')
@member_required
def showPersonalBoard(member_id):
    board = models.BoardMember.query.filter_by(group_id=10).filter_by(owner_id=member_id).first()
    if board:
        return redirect(url_for('.gotoBoardPage1', boardmember_id=board.id))
    else:
        abort(404)

@member_app.route('/board/recent/<int:postmember_id>')
@member_required
def RecentPost(postmember_id):
    rboardRec=models.PostMember.query.order_by(models.PostMember.timestamp.desc()).limit(10).all()
    currentPost=models.PostMember.query.filter_by(id=postmember_id).first_or_404()

    if currentPost in rboardRec:
        return redirect(url_for('.showPost', boardmember_id=currentPost.boardmember_id, postmember_id=postmember_id))
    else:
        abort(404)

@member_app.route('/board/<int:boardmember_id>')
@member_required
def gotoBoardPage1(boardmember_id):
    return redirect(url_for('.showPage', boardmember_id=boardmember_id, page = 1))

@member_app.route('/board/<int:boardmember_id>/_<int:page>', methods=['GET', 'POST'])
@member_required
def showPage(boardmember_id,page):
    if page == 0 :
        abort(404)

    try:

        preference = current_user.preferred_boards
        preferred_boards = []
        for b in preference:
            preferred_boards.append(b.id)

        board = models.BoardMember.query.get(boardmember_id)

        if not board:
            abort(404)

        if request.args.get('search'):
            post_search = []
            if request.args.get('searchtype')=='0':
                for post in board.posts:
                    if request.args.get('search') in post.title:
                        post_search.append(post)
            if request.args.get('searchtype')=='1':
                for post in board.posts:
                    if request.args.get('search') in post.memberwriter.nickname:
                        post_search.append(post)
            if request.args.get('searchtype')=='2':
                for post in board.posts:
                    if request.args.get('search') in post.body:
                        post_search.append(post)
            postlist = post_search
        else:
            postlist = board.posts.all()

        totalpost = len(postlist)
        if totalpost == 0 :
            if page != 1:
                abort(404)
            end = 0
            start = 0
        else :
            end = totalpost - 10 * (page - 1)
            start = totalpost - 10 * page
            if start < 1 :
                start = 0
            if end < 1 :
                abort(404)

        maxpage = math.ceil(totalpost / 10)

        posts = postlist[start:end:]

        postParser = reqparse.RequestParser()
        postParser.add_argument('board_title', type=str, default='')
        postParser.add_argument('owner_id', type=str, default='')
        postParser.add_argument('owner_name', type=str, default='')
        args= postParser.parse_args()

        if args['board_title'] is not '':
            board.title = args['board_title']
            db.session.add(board)
            db.session.commit()
        elif args['owner_id'] is not '' and args['owner_name'] is not '':
            new_owner = models.User.query.filter_by(username=args['owner_id']).first()
            if new_owner is None:
                flash('주어진 정보에 일치하는 회원이 없습니다.')

            elif board.group_id == 10: #boardgroup 10 = '개인게시판'
                flash('개인게시판은 게시판 주를 변경할 수 없습니다.')

            elif new_owner.nickname != args['owner_name']:
                flash('주어진 정보에 일치하는 회원이 없습니다.')

            elif not new_owner.ismember:
                flash('해당 회원은 게시판 주가 될 수 없습니다.')

            else:
                board.owner = new_owner
                db.session.add(board)
                db.session.commit()

        return render_template(
            'post_list.html', member=current_user, nav_id=7,
            board=board, posts=posts, maxpage = maxpage, page=page,
            totalpost=totalpost,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=Current(), snotes=note(0), rnotes=note(1), preferred_boards=preferred_boards)

    except TemplateNotFound:
        abort(404)


@member_app.route('/board/<int:boardmember_id>/<int:postmember_id>')
@member_required
def showPost(boardmember_id, postmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        post = models.PostMember.query.get(postmember_id)
        comments = models.CommentMember.query.filter_by(postmember_id=postmember_id).order_by(models.CommentMember.timestamp).all()

        post_up = None
        post_down = None

        if not post in board.posts:
            abort(404)

        if not (board and post):
            abort(404)

        totalpost = len(board.posts[::-1])
        page = 1
        for s in range(totalpost):
            if post == board.posts[s]:
                if totalpost == 1:
                    pass
                elif s == totalpost - 1:
                    post_down = board.posts[s-1]
                elif s == 0:
                    post_up = board.posts[s+1]
                else:
                    post_up = board.posts[s+1]
                    post_down = board.posts[s-1]

        while True:
            end = totalpost - 10 * (page - 1)
            start = totalpost - 10 * page

            if start < 1 :
                start = 0
            if end < 1 :
                end = 0

            posts=board.posts[start:end:]

            if post in posts :
                break
            else :
                page = page + 1

        post.hitCount = post.hitCount + 1

        # if models.Conference.query.filter_by(record_id=post.id).first():
        #     conf = models.Conference.query.filter_by(record_id=post.id).first()
            
        #     statetable = models.Member_Conference.query.filter_by(conference_id=conf.id)

        #     chulsuks = statetable.filter_by(state=0).all()
        #     bubunchams = statetable.filter_by(state=1).all() 
        #     gonggyuls = statetable.filter(or_(models.Member_Conference.state==2, models.Member_Conference.state==3)).all()
        #     gyulsuks = statetable.filter(or_(models.Member_Conference.state==4, models.Member_Conference.state==5)).all()
        # else :
        #     chulsuks = None
        #     bubunchams = None
        #     gonggyuls = None
        #     gyulsuks = None

        db.session.commit()

        return render_template(
            'post_view.html', member=current_user, nav_id=7,
            board=board, post=post, page = page,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=Current(), post_up=post_up, post_down=post_down, comments=comments, snotes=note(0), rnotes=note(1))
    except TemplateNotFound:
        abort(404)

@member_app.route('/board/<int:boardmember_id>/<int:postmember_id>/modify')
@member_required
def modifyPost(boardmember_id, postmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        post = models.PostMember.query.get(postmember_id)

        if not post in board.posts:
            abort(404)
        if not (board and post):
            abort(404)
        if post.memberwriter != current_user:
            abort(403)

        return render_template(
            'post_modify.html', member=current_user, nav_id=7,
            board=board, post=post,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=Current(), snotes=note(0), rnotes=note(1))
    except TemplateNotFound:
        abort(404)

@member_app.route('/board/<int:boardmember_id>/<int:postmember_id>/delete')
@member_required
def deletePost(boardmember_id, postmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        post = models.PostMember.query.get(postmember_id)

        if not post in board.posts:
            abort(404)
        if not (board and post):
            abort(404)
        if (post.memberwriter != current_user) and (board.owner != current_user):
            abort(403)

        db.session.delete(post)

        db.session.commit()

        return redirect(url_for('.gotoBoardPage1', boardmember_id=boardmember_id))
    except TemplateNotFound:
        abort(404)

@member_app.route('/board/<int:boardmember_id>/write')
@member_required
def writePost(boardmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        if not board:
            abort(404)

        # if boardmember_id >= 3 and boardmember_id <=7 :
        #     recentyear = db.session.query(func.max(models.Quarter.year).label("recentyear")).first().recentyear
        #     recentsemester = db.session.query(func.max(models.Quarter.semester).label("recentsemester")).filter_by(year=recentyear).first().recentsemester
        #     current_quarter = models.Quarter.query.filter_by(year=recentyear).filter_by(semester=recentsemester).first()
        #     current_date = datetime.now().strftime('%Y-%m-%d')

        #     attendants = []

        #     for man in manager:
        #         if man.cycle == recruitcycle:
        #             attendants.append(man)

        #     if len(attendants) == 0:
        #         for man in manager:
        #             if man.cycle == recruitcycle-1:
        #                 attendants.append(man)

        #     actives = models.User.query.filter(or_(models.User.deptstem_id==1,models.User.deptstem_id==3,models.User.deptstem_id==4)).order_by(models.User.deptstem_id).all()

        #     for active in actives:
        #         attendants.append(active)

        #     buseos = []
        #     if boardmember_id == 4: # 대외교류부 부서회의
        #         actives = models.User.query.filter_by(deptstem_id=3).all()
        #         for active in actives:
        #             buseos.append(active)
        #     elif boardmember_id == 5: # 봉사부 부서회의
        #         actives = models.User.query.filter_by(deptstem_id=1).all()
        #         for active in actives:
        #             buseos.append(active)
        #     elif boardmember_id == 6: # 학술부 부서회의
        #         actives = models.User.query.filter_by(deptstem_id=4).all()
        #         for active in actives:
        #             buseos.append(active)
        #     else:
        #         buseos = attendants

        #     return render_template('post_write.html',
        #     member=current_user, nav_id=6, board=board,
        #     notifications=notification.Generate(current_user),
        #     current=Current(), snotes=note(0), rnotes=note(1), quarter=current_quarter, date=current_date, attendants = attendants, buseos=buseos)

        return render_template(
            'post_write.html',
            member=current_user, nav_id=7, board=board,
            notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=Current(), snotes=note(0), rnotes=note(1))

    except TemplateNotFound:
        abort(404)

@member_app.route('/record/write')
@member_required
def writeRecordList():
    current=Current()

    if not current_user in current.active("actives"):
        abort(403)

    limit = datetime.now() - timedelta(days=7)
    writableRecords = models.Record.query.filter_by(writer_id=current_user.id). \
                       filter(models.Record.confday >= limit).all()

    return render_template('record/record_writable.html',
        member=current_user, nav_id=8, current=current, notifications=notification.Generate(current_user), snotes=note(0), rnotes=note(1),
        prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(), records=writableRecords)

@member_app.route('/record/write/<int:record_id>')
@member_required
def writeRecord(record_id):
    record = models.Record.query.get(record_id)

    if not record:
        abort(404)

    current=Current()

    actives=current.active('actives')

    conf_id = 0
    if record.conftype == 0:
        conf_id = models.Conference.query.filter_by(record_id=record.id).first().id

    if record.conftype == 2:
        buseo = models.User.query.filter_by(ismember=1).filter_by(deptstem_id=3).all()
    elif record.conftype == 3:
        buseo = models.User.query.filter_by(ismember=1).filter_by(deptstem_id=1).all()
    elif record.conftype == 4:
        buseo = models.User.query.filter_by(ismember=1).filter_by(deptstem_id=4).all()
    else:
        buseo = []

    if record.body is not None:
        body = record.body.split('<!-- EndOfAttend -->')
        if len(body) <= 1:
            body = ''
            att_0 = ['']
            att_1 = ['']
            att_2 = ['']
            att_4 = ['']
        else:
            attendance = body[0].split('</p><p style="display:none;" class="forid">')
            att_0 = attendance[1].strip().split(' ')
            att_1 = attendance[2].strip().split(' ')
            att_2 = attendance[3].strip().split(' ')
            att_4 = attendance[4].strip().rstrip('</p> ').split(' ')

            body.pop(0)
            body="".join(body)
    else:
        body = ''
        att_0 = ['']
        att_1 = ['']
        att_2 = ['']
        att_4 = ['']

    if (not current_user in current.active("actives")) or (current_user.id != record.writer_id):
        abort(403)

    limit = datetime.now() - timedelta(days=7)
    if not record.confday >= limit:
        abort(403)

    return render_template(
            'record/record_write.html', member=current_user, nav_id=8, conf_id=conf_id,
            record=record, actives=actives, buseo=buseo, body=body, att_0 = att_0, att_1=att_1,
            att_2=att_2, att_4=att_4, notifications=notification.Generate(current_user),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=current, snotes=note(0), rnotes=note(1))

@member_app.route('/record', methods=['GET','POST'])
@member_required
def listRecord():
    recordParser = reqparse.RequestParser()
    recordParser.add_argument('conftypes', type=str)
    recordParser.add_argument('confstart', type=str)
    recordParser.add_argument('confplace', type=str)
    recordParser.add_argument('confend', type=str)
    recordParser.add_argument('conftitle', type=str)
    recordParser.add_argument('page', type=int)

    args = recordParser.parse_args()

    conftypes = args['conftypes']
    if (conftypes == '') or (conftypes is None):
        conftypes = [0, 1, 2, 3, 4, 5]
    else:
        conftypes = conftypes.strip().split(" ")
        conftypes = list(map(int, conftypes))

    confstart = args['confstart']
    if (confstart == '') or (confstart is None):
        confstart = datetime.strptime('2010-07-14', '%Y-%m-%d')
    else:
        confstart = datetime.strptime(confstart, '%Y-%m-%d')

    confend = args['confend']
    if (confend == '') or (confend is None):
        confend = datetime.now()
    else:
        confend = datetime.strptime(confend, '%Y-%m-%d')

    if confstart > confend:
        confstart, confend = confend, confstart

    confplace = args['confplace']
    if (confplace == '') or (confplace is None):
        confplace = "%"
    else:
        confplace = "%" + confplace + "%"

    conftitle = args['conftitle']
    if (conftitle == '') or (conftitle is None):
        conftitle = "%"
    else:
        conftitle = "%" + conftitle + "%"

    page = args['page']
    if page is None:
        page = 1

    records = models.Record.query.filter(models.Record.conftype.in_(conftypes)). \
               filter(models.Record.confday >= confstart). \
               filter(models.Record.confday <= confend). \
               filter(models.Record.confplace.like(confplace)). \
               filter(models.Record.title.like(conftitle)).order_by(models.Record.confday).all()

    if page == 0 :
        abort(404)

    totalNum = len(records)
    end = totalNum - 10 * (page - 1)
    start = totalNum - 10 * page
    maxpage = math.ceil(totalNum / 10)

    if start < 1 :
        start = 0
    if end < 1 :
        end = 0

    records = records[start:end:][::-1]

    confstart = confstart.strftime('%Y-%m-%d')
    confend = confend.strftime('%Y-%m-%d')
    conftitle = conftitle.strip("%")
    confplace = confplace.strip("%")

    return render_template('record/record_list.html',
        member=current_user, nav_id=8, current=Current(), records=records, page=page, maxpage=maxpage,
        notifications=notification.Generate(current_user), 
        prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(), snotes=note(0), rnotes=note(1),
        conftypes=conftypes, confstart=confstart, confend=confend, confplace=confplace, conftitle=conftitle)

@member_app.route('/record/view/<int:record_id>')
@member_required
def viewRecord(record_id):
    record = models.Record.query.get(record_id)
    comments = models.CommentRecord.query.filter_by(record_id=record_id).order_by(models.CommentRecord.timestamp).all()

    if not record:
        abort(404)

    record.hitCount += 1

    db.session.commit()

    return render_template(
        'record/record_view.html', member=current_user, nav_id=8, record=record, comments=comments,
            notifications=notification.Generate(current_user), snotes=note(0), rnotes=note(1),
            prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(), current=Current())

@member_app.route('/record/make', methods=['GET', 'POST'])
@member_required
def makeRecord():
    current=Current()

    if not current_user in current.active("actives"):
        abort(403)

    quarter=current.quarter.id
    day=datetime.now().strftime('%Y-%m-%d')

    return render_template('record/record_make.html',
        member=current_user, nav_id=8, current=current, quarter=quarter, confday=day,
        notifications=notification.Generate(current_user), snotes=note(0), rnotes=note(1),
        prior_boards = models.BoardMember.query.filter(or_(models.BoardMember.id==1, models.BoardMember.id==2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())

class AutoRecordTitle(Resource):
    @member_required
    def post(self):
        current=Current()
        year=current.year
        semester=current.semester

        if semester == 1:
            start = str(year)+'-03-01'
            start = datetime.strptime(start,'%Y-%m-%d')

        elif semester == 2:
            start = str(year)+'-07-01'
            start = datetime.strptime(start,'%Y-%m-%d')

        elif semester == 3:
            start = str(year)+'-09-01'
            start = datetime.strptime(start,'%Y-%m-%d')

        elif semester == 4:
            year += 1
            start = str(year)+'-01-01'
            start = datetime.strptime(start,'%Y-%m-%d')

        postParser = reqparse.RequestParser()
        postParser.add_argument('conftype', type=int)

        args = postParser.parse_args()
        conftype = args['conftype']

        num = models.Record.query.filter(and_(models.Record.conftype==conftype,
               models.Record.confday >= start, models.Record.confday <= datetime.now())).options(load_only('id')).count()


        if conftype == 0 :
            ret = "제 " + str(num+1) + "차 정기회의"
            return ret, 200
        elif conftype == 1 :
            ret = "제 " + str(num+1) + "차 임원회의"
            return ret, 200
        elif conftype == 2 :
            ret = "제 " + str(num+1) + "차 대외교류부 부서회의"
            return ret, 200
        elif conftype == 3 :
            ret = "제 " + str(num+1) + "차 봉사부 부서회의"
            return ret, 200
        elif conftype == 4 :
            ret = "제 " + str(num+1) + "차 학술부 부서회의"
            return ret, 200
        else :
            ret = "기타 회의"
            return ret, 200
api.add_resource(AutoRecordTitle, '/api/record/autotitle')

class NewRecord(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('conftype', type=int)
        postParser.add_argument('confday', type=str)
        postParser.add_argument('confplace', type=str)
        postParser.add_argument('conftitle', type=str)

        args = postParser.parse_args()
        conftype = args['conftype']
        confday = args['confday']
        confplace = args['confplace']
        conftitle = args['conftitle']

        if not ((conftype in range(6)) and confday and confplace and conftitle):
            return "Fail", 404

        if conftype == 0:
            title = '(정기회의) ' + confday +' '+ conftitle
        elif conftype == 1:
            title = '(임원회의) ' + confday +' '+ conftitle
        elif conftype == 2:
            title = '(대외교류부 부서회의) ' + confday +' '+ conftitle
        elif conftype == 3:
            title = '(봉사부 부서회의) ' + confday +' '+ conftitle
        elif conftype == 4:
            title = '(학술부 부서회의) ' + confday +' '+ conftitle
        else:
            title = '(기타) ' + confday + ' ' + conftitle

        if conftype == 0:
            newrec = models.Record(conftype, datetime.strptime(confday,'%Y-%m-%d'), confplace, title, None, current_user)
            newconf = models.Conference(conftitle, Current().quarter, newrec)
            db.session.add(newconf)
            db.session.add(newrec)
            db.session.commit()
            return newrec.id, 200
        else:
            newrec = models.Record(conftype, datetime.strptime(confday,'%Y-%m-%d'), confplace, title, None, current_user)
            db.session.add(newrec)
            db.session.commit()
            return newrec.id, 200
api.add_resource(NewRecord, '/api/record/new')


class NewQuarter(Resource):
    @member_required
    def post(self):
        if not current_user.id in Current().page_manager_ids():
            return abort(403)
        recentyear = Current().year
        recentsemester = Current().semester

        newyear = recentyear
        newsemester = recentsemester

        if recentsemester == 4 :
            newyear = newyear + 1
            newsemester = 1
        else :
            newyear = newyear
            newsemester = recentsemester + 1

        if newsemester == 1 :
            description = str(newyear) + '년 봄분기('+str(newyear)+'.3월 ~ 6월)'
        elif newsemester == 2 :
            description = str(newyear) + '년 여름분기('+str(newyear)+'.7월 ~ 8월)'
        elif newsemester == 3 :
            description = str(newyear) + '년 가을분기('+str(newyear)+'.9월 ~ 12월)'
        elif newsemester == 4 :
            description = str(newyear) + '년 겨울분기('+str(newyear+1)+'.1월 ~ 2월)'

        quarter = models.Quarter(newyear, newsemester)
        quarter.description = description
        db.session.add(quarter)
        db.session.commit()
        return "Success", 200
api.add_resource(NewQuarter, '/api/quarter/new')

class ModifyQuarter(Resource):
    @member_required
    def post(self,id):
        postParser = reqparse.RequestParser()
        postParser.add_argument('activity_score', type=int)
        postParser.add_argument('conference_absence', type=int)

        args = postParser.parse_args()

        if not current_user.id in Current().page_manager_ids():
            return abort(403)

        quarter = models.Quarter.query.get(id)
        quarter.activity_score = args['activity_score']
        quarter.conference_absence= args['conference_absence']
        db.session.add(quarter)
        db.session.commit()
        return "Success", 200
api.add_resource(ModifyQuarter, '/api/quarter/<int:id>/modify')

class BoardMember(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('board_title', type=str)
        postParser.add_argument('gid', type=int)
        postParser.add_argument('special', type=int)
        args= postParser.parse_args()

        board = models.BoardMember()
        board.title = args['board_title']
        board.special = args['special']
        board.owner_id = current_user.id
        board.group_id = args['gid']

        db.session.add(board)
        db.session.commit()
        return "Success", 200

    @member_required
    def delete(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('boardmember_id', type=int)
        postParser.add_argument('postmember_id', type=int)
        args = postParser.parse_args()

        board = models.BoardMember.query.filter_by(id=args['boardmember_id']).first()
        post = models.Post.query.filter_by(id=args['postmember_id']).first()
        if not board or not post:
            abort(404)
        if board.special == 0:
            post.boards.remove(board)
        db.session.add(post)
        db.session.commit()
        return "Success", 200
api.add_resource(BoardMember, '/api/board')

class WriteRecord(Resource):
    postParser = reqparse.RequestParser()
    postParser.add_argument('body', type=str)

    @member_required
    def put(self, record_id):
        current=Current()
        args = self.postParser.parse_args()
        record = models.Record.query.get(record_id)
        if not record:
            abort(404)

        if (not current_user in current.active("actives")) or (current_user.id != record.writer_id):
            abort(403)

        record.body = args['body']

        files = request.files.getlist("files")

        file_uploaded = False

        for file in files:
            if helper.process_file(file, record):
                file_uploaded = True

        db.session.commit()

        return "Success", 200
api.add_resource(WriteRecord, '/api/record/write/<int:record_id>')

class Post(Resource):
    postParser = reqparse.RequestParser()
    postParser.add_argument('title', type=str, required=True,
                               help='Title is required')
    postParser.add_argument('body', type=str, default='')
    postParser.add_argument('boardmember_id', type=int, default=0)
    postParser.add_argument('redirect', type=str, default='')

    @member_required
    def post(self):
        args = self.postParser.parse_args()
        board = models.BoardMember.query.get(args['boardmember_id'])
        if not board:
            return None, 404
        post = models.PostMember(args['title'], args['body'],
                        current_user, board)
        db.session.add(post)

        files = request.files.getlist("files")

        file_uploaded = False

        for file in files:
            if helper.process_file(file, post):
                file_uploaded = True

        db.session.commit()
        return str(post)

    @member_required
    def put(self, id):
        args = self.postParser.parse_args()
        board = models.BoardMember.query.get(args['boardmember_id'])
        post = models.PostMember.query.get(id)
        if not (board and post):
            abort(404)

        post.title = args['title']
        post.body = args['body']

        files = request.files.getlist("files")

        file_uploaded = False

        for file in files:
            if helper.process_file(file, post):
                file_uploaded = True

        db.session.commit()

        return str(post)

    @member_required
    def get(self, id):
        post = models.PostMember.query.get(id)
        if post:
            return str(post)
        return {}
api.add_resource(Post,'/api/post', '/api/post/<int:id>')

class AddMemo(Resource):

    taskParser = reqparse.RequestParser()
    taskParser.add_argument('title', type=str)
    taskParser.add_argument('body', type=str)

    @member_required
    def post(self):
        args = self.taskParser.parse_args()
        memo = models.Memo(args['title'],args['body'],current_user)
        db.session.add(memo)
        db.session.commit()
        return "Success", 200
api.add_resource(AddMemo, '/api/memo/add')

class DeleteMemo(Resource):

    taskParser = reqparse.RequestParser()
    taskParser.add_argument('id', type=int, default=0)

    @member_required
    def post(self):
        args = self.taskParser.parse_args()
        memo = models.Memo.query.filter_by(id=args['id']).first_or_404()
        if current_user.id != memo.writer_id:
            return "Not Allowed", 403

        db.session.delete(memo)
        db.session.commit()
        return "Success", 200
api.add_resource(DeleteMemo, '/api/memo/delete')

class MakeActivity(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('type', type=int)
        postParser.add_argument('name', type=str)
        postParser.add_argument('totalscore', type=int)
        postParser.add_argument('quarter_id', type=int)
        
        args = postParser.parse_args()

        if args['quarter_id'] != Current().quarter.id:
            return abort(403)
        if not current_user.id in Current().page_manager_ids():
            return abort(403)

        activity = models.Activity(
            args['type'], args['name'], args['totalscore'])
        activity.quarter_id=args['quarter_id']

        if activity.type == 0:
            members = Current().active("actives")
            for member in members:
                activity.members.append(member)
        db.session.add(activity)
        db.session.commit()
        return "Success", 200
api.add_resource(MakeActivity, '/api/activity/make')

class ModifyActivity(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('id', type=int)
        postParser.add_argument('name', type=str)
        postParser.add_argument('totalscore', type=int)

        args = postParser.parse_args()

        if not current_user.id in Current().page_manager_ids():
            return abort(403)

        activity = models.Activity.query.get(args['id'])
        activity.name = args['name']
        activity.totalscore = args['totalscore']
        db.session.add(activity)
        db.session.commit()
        return "Success", 200
api.add_resource(ModifyActivity, '/api/activity/modify')

class DeleteActivity(Resource):
    @member_required
    def post(self,id):
        if not current_user.id in Current().page_manager_ids():
            return abort(403)
        activity = models.Activity.query.get(id)
        db.session.delete(activity)
        db.session.commit()
        return "Success", 200
api.add_resource(DeleteActivity, '/api/activity/<int:id>/delete')

class UpdateActivityScore(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('activity_id', type=int)
        postParser.add_argument('member_id', type=int)
        postParser.add_argument('score', type=int)

        args = postParser.parse_args()

        if not current_user.id in Current().page_manager_ids():
            return abort(403)
        scoreforupdate = models.Member_Activity.query.filter(and_(models.Member_Activity.activity_id==args['activity_id'],models.Member_Activity.member_id==args['member_id'])).first()
        scoreforupdate.score = args['score']

        db.session.add(scoreforupdate)
        db.session.commit()
        return "Success", 200
api.add_resource(UpdateActivityScore, '/api/quarter/memberactivity/update')

class AddActivityMember(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('activity_id', type=int)
        postParser.add_argument('member_ids', type=str)

        args = postParser.parse_args()
        member_ids = args['member_ids'].strip().split(" ")
        member_ids = list(map(int, member_ids))

        if not current_user.id in Current().page_manager_ids():
            return abort(403)

        activity = models.Activity.query.filter_by(id=args['activity_id']).first()

        for member_id in member_ids:
            member = models.User.query.filter_by(id=member_id).first()
            if member in activity.members:
                pass
            else:
                activity.members.append(member)

        db.session.add(activity)
        db.session.commit()

        return "Success",200
api.add_resource(AddActivityMember, '/api/quarter/memberactivity/add')

class DeleteActivityMember(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('activity_id', type=int)
        postParser.add_argument('member_id', type=int)
        args=postParser.parse_args()

        if not current_user.id in Current().page_manager_ids():
            return abort(403)

        activity = models.Activity.query.filter_by(id=args['activity_id']).first()
        member = models.User.query.filter_by(id=args['member_id']).first()
        activity.members.remove(member)

        db.session.add(activity)
        db.session.commit()

        return "Success",200
api.add_resource(DeleteActivityMember, '/api/quarter/memberactivity/delete')

class UpdateConferenceState(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('conference_id', type=int)
        postParser.add_argument('member_id', type=int)
        postParser.add_argument('state', type=int)

        args = postParser.parse_args()

        if request.referrer.find('/stem/record/write/') > -1:
            if not current_user in Current().active('actives'):
                return abort(403)
        else:
            if not current_user.id in Current().page_manager_ids():
                return abort(403)

        stateforupdate = models.Member_Conference.query.filter(and_(models.Member_Conference.conference_id==args['conference_id'],models.Member_Conference.member_id==args['member_id'])).first()
        stateforupdate.state = args['state']

        db.session.add(stateforupdate)
        db.session.commit()
        return "Success", 200
api.add_resource(UpdateConferenceState, '/api/quarter/memberconference/update')

class AddConferenceMember(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('conference_id', type=int)
        postParser.add_argument('member_ids', type=str)

        args = postParser.parse_args()
        member_ids = args['member_ids'].strip().split(" ")
        member_ids = list(map(int, member_ids))

        if request.referrer.find('/stem/record/write/') > -1:
            if not current_user in Current().active('actives'):
                return abort(403)
        else:
            if not current_user.id in Current().page_manager_ids():
                return abort(403)

        conference = models.Conference.query.filter_by(id=args['conference_id']).first()

        for member_id in member_ids:
            member = models.User.query.filter_by(id=member_id).first()
            if member in conference.members:
                pass
            else:
                conference.members.append(member)

        db.session.add(conference)
        db.session.commit()

        return "Success",200
api.add_resource(AddConferenceMember, '/api/quarter/memberconference/add')

class DeleteConferenceMember(Resource):
    @member_required
    def post(self):
        postParser = reqparse.RequestParser()
        postParser.add_argument('conference_id', type=int)
        postParser.add_argument('member_ids', type=str)
        args=postParser.parse_args()

        member_ids = args['member_ids'].strip().split(" ")
        member_ids = list(map(int, member_ids))

        if request.referrer.find('/stem/record/write/') > -1:
            if not current_user in Current().active('actives'):
                return abort(403)
        else:
            if not current_user.id in Current().page_manager_ids():
                return abort(403)

        conference = models.Conference.query.filter_by(id=args['conference_id']).first()

        for member_id in member_ids:
            member = models.User.query.filter_by(id=member_id).first()
            if member in conference.members:
                conference.members.remove(member)
            else:
                pass

        db.session.add(conference)
        db.session.commit()

        return "Success",200
api.add_resource(DeleteConferenceMember, '/api/quarter/memberconference/delete')

comment_fields = {
    'id' : fields.Integer,
    'body' : fields.String,
    'timestamp' : fields.DateTime,
    'member_id' : fields.Integer,
    'writer_id' : fields.Integer
}

class MemberComment(Resource):
    @member_required
    @marshal_with(comment_fields)
    def post(self):
        commentParser = reqparse.RequestParser()
        commentParser.add_argument('member_id', type=int)
        commentParser.add_argument('writer_id', type=int)
        commentParser.add_argument('body', type=str)

        args = commentParser.parse_args()
        member = models.User.query.get(args['member_id'])
        writer = models.User.query.get(args['writer_id'])
        if not member:
            return None, 404
        comment = models.Member_Comment(
            args['body'],member, writer)

        db.session.add(comment)
        db.session.commit()

        return comment, 201

    @member_required
    def delete(self, id):
        comment = models.Member_Comment.query.filter_by(id=id).first()
        if comment:
            if current_user == comment.writer:
                db.session.delete(comment)
                db.session.commit()
                return True, 200
            else:
                return False, 401
        else:
            return None, 404
api.add_resource(MemberComment, '/api/people/comment', '/api/people/comment/<int:id>')

class DeleteNote(Resource):
    @member_required
    def post(self):
        noteParser = reqparse.RequestParser()
        noteParser.add_argument('id', type=int)
        noteParser.add_argument('sent_del', type=int)
        noteParser.add_argument('recv_del', type=int)
        args=noteParser.parse_args()

        note = models.Note.query.filter_by(id=args['id']).first()

        if not note:
            return None, 404
        if not current_user in [note.sender,note.receiver]:
            return None, 403

        if args['sent_del']:
            note.sent_del=args['sent_del']
        elif args['recv_del']:
            note.recv_del=args['recv_del']
        else:
            return False, 401

        db.session.add(note)
        db.session.commit()

        note = models.Note.query.get(args['id'])
        if note.sent_del != 0 and note.recv_del != 0:
            db.session.delete(note)
            db.session.commit()
api.add_resource(DeleteNote, '/api/note/delete')

class MakeNote(Resource):
    @member_required
    def post(self):
        noteParser = reqparse.RequestParser()
        noteParser.add_argument('receiver', type=str)
        noteParser.add_argument('sent_id', type=int)
        noteParser.add_argument('body', type=str)
        noteParser.add_argument('sendmail', type=int)
        args=noteParser.parse_args()

        note = models.Note()
        recv = models.User.query.filter_by(username=args['receiver']).first()
        if recv is None:
            return "해당 계정이 존재하지 않습니다.", 404
        if not recv.ismember:
            return "공우 회원이 아닌 계정으로 쪽지를 보낼 수 없습니다.", 404
        if recv == current_user:
            return "자기 자신에게 쪽지를 보낼 수 없습니다.", 404
        note.recv_id = recv.id
        note.sent_id = args['sent_id']
        note.timestamp = datetime.now()
        note.body = args['body']

        db.session.add(note)
        db.session.commit()

        receiver_img = note.receiver.img or 'profile/default.png'
        print(args['sendmail'])
        if args['sendmail'] == 1:
            html = render_template(
                'memberapp/note_content.html',
                recv=recv, current_user=current_user, body=args['body'])
            subject = "[공우(STEM)] " + recv.nickname + " 회원님, STEM 쪽지함에 쪽지가 도착했습니다."

            send_email(recv.email, subject, html)

        msg = [str(note.receiver.cycle)+"기 "+note.receiver.nickname+" 회원에게 쪽지가 전달되었습니다.", \
        note.id, receiver_img, note.receiver.nickname, note.receiver.username, note.timestamp.strftime('%Y-%m-%d %H:%M'), note.body]

        return msg, 200
api.add_resource(MakeNote, '/api/note/make')

class ReadNote(Resource):
    @member_required
    def post(self):
        noteParser = reqparse.RequestParser()
        noteParser.add_argument('id', type=int)
        noteParser.add_argument('recv_read', type=int)
        args=noteParser.parse_args()

        note = models.Note.query.filter_by(id=args['id']).first()
        if not note:
            return None, 404

        if not current_user is note.receiver:
            return None, 403

        if note.recv_read == 0 and args['recv_read'] != 0:
            note.recv_read = 1
            db.session.add(note)
            db.session.commit()
            return "Success", 200

        return "Success", 200
api.add_resource(ReadNote, '/api/note/read')

class Favorite(Resource):
    @member_required
    def post(self, boardmember_id):
        board = models.BoardMember.query.filter_by(id=boardmember_id).first_or_404()
        if board in current_user.preferred_boards:
            return "Error", 404
        else:
            current_user.preferred_boards.append(board)
            db.session.add(current_user)
            db.session.commit()
            return "Successdd", 200
        

    @member_required
    def delete(self, boardmember_id):
        board = models.BoardMember.query.filter_by(id=boardmember_id).first_or_404()
        for b in current_user.preferred_boards:
            if board.id == b.id:
                pref = models.Member_Preference.query. \
                    filter(and_(models.Member_Preference.member_id==current_user.id,
                        models.Member_Preference.boardmember_id==board.id)).first()
                db.session.delete(pref)
                db.session.commit()
                return "Success", 200
        return "Error", 404
api.add_resource(Favorite, '/api/favorite/add/<int:boardmember_id>', '/api/favorite/del/<int:boardmember_id>')

comment_fields = {
    'id': fields.Integer,
    'body': fields.String,
    'timestamp': fields.DateTime
}

class Comment(Resource):
    @marshal_with(comment_fields)
    def get(self, commentID, MorR):
        if MorR == "M": # False for BoardMember
            comment = models.CommentMember.query.get(commentID)
        elif MorR == "R": # True for Record
            comment = models.CommentRecord.query.get(commentID)
        else:
            return None, 404

        if comment:
            return comment
        return None, 404

    @member_required
    @marshal_with(comment_fields)
    def post(self, MorR):
        commentParser = reqparse.RequestParser()
        commentParser.add_argument('body', type=str)
        commentParser.add_argument('userID', type=int)
        commentParser.add_argument('postID', type=int)

        args = commentParser.parse_args()
        writer = models.User.query.get(args['userID'])
        if MorR == "M":
            post = models.PostMember.query.get(args['postID'])
            if not post:
                return None, 404
            comment = models.CommentMember(args['body'], writer, post)
        elif MorR == "R":
            post = models.Record.query.get(args['postID'])
            if not post:
                return None, 404
            comment = models.CommentRecord(args['body'], writer, post)
        else:
            return None, 404

        db.session.add(comment)
        db.session.commit()

        return comment, 201

    @member_required
    def delete(self, commentID, MorR):
        if MorR == "M": # False for BoardMember
            comment = models.CommentMember.query.get(commentID)
            if comment:
                if (current_user == comment.membercommenter) or (current_user == comment.postmember.boardmember.owner):
                    comment.remove()
                    return True, 200
                else:
                    return None, 404
            else:
                return None, 404
        elif MorR == "R": # True for Record
            comment = models.CommentRecord.query.get(commentID)
            if comment:
                if current_user == comment.recordcommenter:
                    comment.remove()
                    return True, 200
                else:
                    return None, 404
            else:
                return None, 404
        else:
            return None, 404
api.add_resource(Comment, '/api/post/comment/<string:MorR>', '/api/post/comment/<string:MorR>/<int:commentID>')
