import datetime
import functools
import logging
import math
import operator

import flask
import flask_login
import flask_restful
from flask_restful import fields
from flask_restful import reqparse
import jinja2
from sqlalchemy import and_, not_, or_
from sqlalchemy import orm

from stem import db
from stem import forms
from stem import helper
from stem import member_help
from stem import models
from stem import notification

member_app = flask.Blueprint(
    'member_app', __name__, template_folder='templates/memberapp')
api = flask_restful.Api(member_app)


def ShouldBeMember(func):

    @functools.wraps(func)
    @flask_login.login_required
    def DecoratedView(*args, **kwargs):
        if not flask_login.current_user.ismember:
            return flask.abort(403)
        return func(*args, **kwargs)

    return DecoratedView


def Note(note_type):
    if note_type == 0:
        sent_notes = models.Note.query.filter_by(
            sent_id=flask_login.current_user.id).filter_by(sent_del=0).order_by(
                models.Note.timestamp.desc()).all()
        return sent_notes
    else:
        received_notes = models.Note.query.filter_by(
            recv_id=flask_login.current_user.id).filter_by(recv_del=0).order_by(
                models.Note.timestamp.desc()).all()
        return received_notes

@member_app.route('-<string:cloud>')
def ToNas(cloud):
    if not flask.request.MOBILE:
        if cloud == 'nas':
            return flask.redirect(f'https://{flask.request.host}:8088')
        elif cloud == 'file':
            return flask.redirect(f'https://{flask.request.host}:8088/file')
        elif cloud == 'photo':
            return flask.redirect(f'https://{flask.request.host}:8089/photo')
        else:
            flask.abort(404)
    else:
        if cloud == 'nas':
            flask.flash('모바일 환경에서는 클라우드 데스크톱이 지원되지 않습니다.')
            return flask.redirect(flask.url_for('.tonas', cloud='file'))
        elif cloud in ['file', 'photo']:
            if flask_login.current_user.is_anonymous():
                flask.abort(401)
            else:
                if flask_login.current_user.ismember:
                    return flask.render_template(
                        'mobile_nas.html',
                        member=flask_login.current_user,
                        nav_id=4,
                        notifications=notification.Generate(flask_login.current_user),
                        prior_boards=models.BoardMember.query.filter(
                            or_(models.BoardMember.id == 1,
                                models.BoardMember.id == 2)).all(),
                        group_lists=models.Bgroup.query.filter(
                            models.Bgroup.id != 1).all(),
                        current=member_help.Current(),
                        snotes=Note(0),
                        rnotes=Note(1),
                        cloud=cloud)
                else:
                    flask.abort(403)
        else:
            flask.abort(404)

@member_app.route('/')
@ShouldBeMember
def main():
    memoes = models.Memo.query.order_by(models.Memo.id.desc()).limit(3).all()

    personal_board = models.BoardMember.query.filter(
        and_(models.BoardMember.group_id == 10,
             models.BoardMember.owner == flask_login.current_user)).first()

    preferred_boards = flask_login.current_user.preferred_boards

    recent_posts = models.PostMember.query.order_by(
        models.PostMember.id.desc()).limit(10).all()

    try:
        return flask.render_template(
            'dashboard.html',
            current_user=flask_login.current_user,
            nav_id=1,
            notifications=notification.Generate(flask_login.current_user),
            memoes=memoes,
            snotes=Note(0),
            rnotes=Note(1),
            personal_board=personal_board,
            preferred_boards=preferred_boards,
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            recent_posts=recent_posts,
            current=member_help.Current())
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/search')
@ShouldBeMember
def Search():
    search_string = flask.request.args.get('q')
    if search_string:
        matched_people = models.User.query.filter(
            and_(
                models.User.ismember,
                models.User.nickname.like('%' + search_string + '%'))).order_by(
                    models.User.cycle).order_by(models.User.nickname).all()
        matched_people_ids = []
        for person in matched_people:
            person_id = person.id
            matched_people_ids.append(person_id)
        matched_boards = models.BoardMember.query.filter(
            or_(
                models.BoardMember.title.like('%' + search_string + '%'),
                models.BoardMember.owner_id.in_(matched_people_ids))).order_by(
                    models.BoardMember.group_id).all()
    else:
        if flask.request.referrer:
            return flask.redirect(flask.request.referrer)
        else:
            return flask.redirect(flask.url_for('.main'))

    try:
        return flask.render_template(
            'search.html',
            matched_people=matched_people,
            matched_boards=matched_boards,
            notifications=notification.Generate(flask_login.current_user),
            snotes=Note(0),
            rnotes=Note(1),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            search_string=search_string)
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/mms/completion_state', methods=['GET', 'POST'])
@ShouldBeMember
def MoveToCompletionState():
    if flask.request.args:
        name = flask.request.args.get('name')
        cycle = flask.request.args.get('cycle')

        if not (name or cycle):
            flask.abort(404)

        members = models.User.query.filter_by(cycle=cycle).all()
        mem_id = []
        for member in members:
            if member.nickname == name:
                mem_id.append(member.id)
        if len(mem_id) > 1:
            flask.flash(
                str(len(mem_id)) +
                ' results are found. Search again for the next result.')
            for n in range(len(mem_id)):
                if mem_id[n] == int(flask.request.referrer.split('/')[::-1][0]):
                    n = (n + 1) % (len(mem_id))
                    moveid = mem_id[n]
                    break
                else:
                    moveid = mem_id[0]
        elif len(mem_id) == 1:
            moveid = mem_id[0]
        else:
            moveid = flask.request.referrer.split('/')[::-1][0]
    else:
        moveid = flask_login.current_user.id

    return flask.redirect(
        flask.url_for('.CompletionState', mem_id_shown=moveid))

@member_app.route('/mms/completion_state/<int:mem_id_shown>')
@ShouldBeMember
def CompletionState(mem_id_shown):
    if (flask_login.current_user.id not in member_help.Current().page_manager_ids()
       ) and (flask_login.current_user.id != mem_id_shown):
        flask.abort(403)

    recentyear = member_help.Current().year
    recentsemester = member_help.Current().semester

    correspondmember = models.User.query.filter_by(id=mem_id_shown).first()

    activities = correspondmember.activities
    conferences = correspondmember.conferences
    quarters = models.Quarter
    scoretable = models.MemberActivity
    statetable = models.MemberConference

    scoresum = 0
    statesum = 0
    quarter_id_list = []
    completion = []

    for activity in activities:
        if activity.quarter_id not in quarter_id_list:
            quarter_id_list.append(activity.quarter_id)

    for conference in conferences:
        if conference.quarter_id not in quarter_id_list:
            quarter_id_list.append(conference.quarter_id)

    quarter_id_list.sort(reverse=True)

    for quarter_id in quarter_id_list:
        for activity in activities:
            if activity.quarter_id == quarter_id:
                score = scoretable.query.filter_by(
                    activity_id=activity.id).filter_by(
                        member_id=mem_id_shown).first().score
                scoresum = scoresum + score
        for conference in conferences:
            if conference.quarter_id == quarter_id:
                state = statetable.query.filter_by(
                    conference_id=conference.id).filter_by(
                        member_id=mem_id_shown).first().state
                if state == 1:
                    statesum = statesum + 1 / 3
                elif state in [0, 2]:
                    pass
                elif state == 3:
                    statesum = statesum + 1 / 3
                elif state == 4:
                    statesum = statesum + 1
                else:
                    statesum = statesum + 4 / 3
        quarter = models.Quarter.query.filter_by(id=quarter_id).first()
        completion.append([
            quarter_id, quarter.year, quarter.semester, scoresum,
            quarter.activity_score,
            round(statesum, 1), quarter.conference_absence
        ])
        scoresum = 0
        statesum = 0

    completion.sort(key=operator.itemgetter(1, 2), reverse=True)

    try:
        return flask.render_template(
            'memberapp/mms/completion_state.html',
            member=flask_login.current_user,
            notifications=notification.Generate(flask_login.current_user),
            nav_id=2,
            current=member_help.Current(),
            mem_id_shown=mem_id_shown,
            correspondmember=correspondmember,
            scoretable=scoretable,
            statetable=statetable,
            activities=activities,
            conferences=conferences,
            completion=completion,
            quarter_id_list=quarter_id_list,
            quarters=quarters,
            recentyear=recentyear,
            recentsemester=recentsemester,
            snotes=Note(0),
            rnotes=Note(1),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/mms/completion_criterion')
@ShouldBeMember
def MoveRecentCompletionCriterion():
    recentyear = member_help.Current().year
    recentsemester = member_help.Current().semester

    return flask.redirect(
        flask.url_for(
            '.MgmtCompletionCriterion',
            year=recentyear,
            semester=recentsemester))

@member_app.route(
    '/mms/completion_criterion/<int:year>/<int:semester>',
    methods=['GET', 'POST'])
@ShouldBeMember
def MgmtCompletionCriterion(year, semester):
    quarters = models.Quarter.query.order_by(
        models.Quarter.year.desc()).order_by(
            models.Quarter.semester.desc()).all()
    quarter = models.Quarter.query.filter_by(year=year).filter_by(
        semester=semester).first()

    if not quarter:
        return flask.abort(404)

    regularactscore = 0

    for activity in quarter.activities:
        if activity.type == 0:
            regularactscore = regularactscore + activity.totalscore

    try:
        return flask.render_template(
            'memberapp/mms/mgmt_completion_criterion.html',
            member=flask_login.current_user,
            notifications=notification.Generate(flask_login.current_user),
            nav_id=2,
            current=member_help.Current(),
            year=year,
            semester=semester,
            quarter=quarter,
            quarters=quarters,
            regularactscore=regularactscore,
            snotes=Note(0),
            rnotes=Note(1),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/mms/mgmt/completion_record', methods=['GET', 'POST'])
@ShouldBeMember
def MoveToMgmtCompletionRecordFirst():
    recentyear = member_help.Current().year
    recentsemester = member_help.Current().semester
    return flask.redirect(
        flask.url_for(
            '.MgmtCompletionRecord', year=recentyear, semester=recentsemester))

@member_app.route(
    '/mms/mgmt/completion_record/<int:year>/<int:semester>',
    methods=['GET', 'POST'])
@ShouldBeMember
def MgmtCompletionRecord(year, semester):
    if flask_login.current_user.id not in member_help.Current().page_manager_ids():
        flask.abort(404)

    recentyear = member_help.Current().year
    recentsemester = member_help.Current().semester
    quarters = models.Quarter.query.order_by(
        models.Quarter.year.desc()).order_by(
            models.Quarter.semester.desc()).all()

    quarter = models.Quarter.query.filter_by(year=year).filter_by(
        semester=semester).first_or_404()

    if not quarter:
        flask.abort(404)

    act_id_set = []
    for activity in quarter.activities:
        act_id_set.append(activity.id)
    conf_id_set = []
    for conference in quarter.conferences:
        conf_id_set.append(conference.id)

    scoretable = models.MemberActivity.query.filter(
        models.MemberActivity.activity_id.in_(act_id_set)).all()
    statetable = models.MemberConference.query.filter(
        models.MemberConference.conference_id.in_(conf_id_set)).all()

    try:
        return flask.render_template(
            'memberapp/mms/mgmt_completion_record.html',
            member=flask_login.current_user,
            notifications=notification.Generate(flask_login.current_user),
            nav_id=2,
            current=member_help.Current(),
            quarters=quarters,
            quarter=quarter,
            scoretable=scoretable,
            statetable=statetable,
            year=year,
            recentyear=recentyear,
            semester=semester,
            recentsemester=recentsemester,
            snotes=Note(0),
            rnotes=Note(1),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/mms/mgmt/completion_record/member_addlist')
@ShouldBeMember
def MemberAddList():
    if flask_login.current_user.id not in member_help.Current().page_manager_ids():
        flask.abort(404)

    members = models.User.query.filter_by(ismember=1).order_by(
        models.User.cycle).all()

    return flask.render_template(
        'memberapp/mms/mgmt_memberaddlist.html',
        members=members,
        snotes=Note(0),
        rnotes=Note(1))

@member_app.route(
    '/mms/mgmt/completion_record/member_recordtable/<int:year>/<int:semester>')
@ShouldBeMember
def MemberRecordTable(year, semester):
    if flask_login.current_user.id not in member_help.Current().page_manager_ids():
        flask.abort(404)

    scoresum = 0
    statesum = 0
    scoretable = models.MemberActivity
    statetable = models.MemberConference
    completion = []

    recentyear = member_help.Current().year
    recentsemester = member_help.Current().semester
    quarter = models.Quarter.query.filter_by(year=recentyear).filter_by(
        semester=recentsemester).first()
    qid = quarter.id

    if year == recentyear and semester == recentsemester:
        record_members = member_help.Current().active('actives')
    else:
        quarter = models.Quarter.query.filter_by(year=year).filter_by(
            semester=semester).first_or_404()
        qid = quarter.id
        id_set = []
        for qactivity in quarter.activities:
            memacts = models.MemberActivity.query.filter_by(
                activity_id=qactivity.id).all()
            for memact in memacts:
                id_set.append(memact.member_id)

        for qconference in quarter.conferences:
            memcons = models.MemberConference.query.filter_by(
                conference_id=qconference.id).all()
            for memcon in memcons:
                id_set.append(memcon.member_id)
        record_members = models.User.query.filter(
            models.User.id.in_(id_set)).order_by(models.User.cycle).order_by(
                models.User.nickname).all()

    for record_member in record_members:
        activities = record_member.activities
        conferences = record_member.conferences

        for activity in activities:
            if activity.quarter_id == qid:
                score = scoretable.query.filter_by(
                    activity_id=activity.id).filter_by(
                        member_id=record_member.id).first().score
                scoresum = scoresum + score
        for conference in conferences:
            if conference.quarter_id == qid:
                state = statetable.query.filter_by(
                    conference_id=conference.id).filter_by(
                        member_id=record_member.id).first().state
                if state == 1:  # 지각인 경우
                    statesum = statesum + 1 / 3
                elif state in [0, 2]:  # 출석이나 공결인 경우
                    pass
                elif state == 3:  # 공결하였으나 회의록 확인을 달지 않은 경우
                    statesum = statesum + 1 / 3
                elif state == 4:  # 결석한 경우
                    statesum = statesum + 1
                else:  # 나머지 state는 모두 결석하였고 회의록 확인을 달지 않은 경우
                    statesum = statesum + 4 / 3
        completion.append([
            record_member.deptstem.name, record_member.nickname,
            record_member.cycle, scoresum, quarter.activity_score,
            round(statesum, 1), quarter.conference_absence
        ])
        scoresum = 0
        statesum = 0

    return flask.render_template(
        'memberapp/mms/mgmt_memberrecordtable.html', completion=completion)

@member_app.route('/mms/active', methods=['GET', 'POST'])
@ShouldBeMember
def ActiveApply():
    form = forms.ModifyMemberForm()

    departments = models.DeptUniv.query.all()
    stem_departments = models.DeptStem.query.filter(
        or_(models.DeptStem.id == 1, models.DeptStem.id == 3,
            models.DeptStem.id == 4)).all()

    flask.request = models.Configuration.query.filter_by(
        option='active_apply').first().value

    actives = member_help.Current().active('actives')

    try:
        if form.validate_on_submit():
            return flask.render_template(
                'memberapp/mms/active_apply.html',
                current_user=flask_login.current_user,
                notifications=notification.Generate(flask_login.current_user),
                nav_id=2,
                current=member_help.Current(),
                form=form,
                deptunivs=departments,
                deptstems=stem_departments,
                is_active=flask.request,
                message='신청이 완료되었습니다.',
                snotes=Note(0),
                rnotes=Note(1))
        return flask.render_template(
            'memberapp/mms/active_apply.html',
            current_user=flask_login.current_user,
            notifications=notification.Generate(flask_login.current_user),
            nav_id=2,
            current=member_help.Current(),
            form=form,
            deptunivs=departments,
            deptstems=stem_departments,
            is_active=flask.request,
            snotes=Note(0),
            rnotes=Note(1),
            actives=actives)
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/mms/active/activation', methods=['GET', 'POST'])
@ShouldBeMember
def ActiveActivation():
    if flask_login.current_user.id in member_help.Current().page_manager_ids():
        if 'is_active' in flask.request.form:
            isactive = models.Configuration.query.filter_by(
                option='active_apply').all()
            newval = models.Configuration('active_apply', True)
            for i in isactive:
                db.session.delete(i)
            db.session.add(newval)
            db.session.commit()
        else:
            isactive = models.Configuration.query.filter_by(
                option='active_apply').all()
            newval = models.Configuration('active_apply', False)
            for i in isactive:
                db.session.delete(i)
            db.session.add(newval)
            db.session.commit()
        return flask.redirect(flask.url_for('.ActiveApply'))
    return flask.abort(403)

@member_app.route('/mms/mgmt/active_registration', methods=['GET', 'POST'])
@ShouldBeMember
def MgmtActiveRegistration():

    form = forms.ModifyStemDeptOnly()

    if flask_login.current_user.id not in member_help.Current().page_manager_ids():
        flask.abort(403)

    try:
        if form.is_submitted():
            if form.memberid.data == -1:
                users = models.User.query.filter(
                    or_(models.User.deptstem_id == 1,
                        models.User.deptstem_id == 3,
                        models.User.deptstem_id == 4)).all()
                for user in users:
                    user.deptstem_id = form.stem_department.data
                    db.session.add(user)
                db.session.commit()
            else:
                user = models.User.query.filter(
                    models.User.id == form.memberid.data).first_or_404()
                user.deptstem_id = form.stem_department.data
                db.session.add(user)
                db.session.commit()
            return flask.render_template(
                'memberapp/mms/mgmt_registration.html',
                member=flask_login.current_user,
                notifications=notification.Generate(flask_login.current_user),
                nav_id=2,
                form=form,
                current=member_help.Current(),
                snotes=Note(0),
                rnotes=Note(1),
                prior_boards=models.BoardMember.query.filter(
                    or_(models.BoardMember.id == 1,
                        models.BoardMember.id == 2)).all(),
                group_lists=models.Bgroup.query.filter(
                    models.Bgroup.id != 1).all())
        return flask.render_template(
            'memberapp/mms/mgmt_registration.html',
            member=flask_login.current_user,
            notifications=notification.Generate(flask_login.current_user),
            nav_id=2,
            form=form,
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/people/_<int:cycle>')
@ShouldBeMember
def ShowPeople(cycle):
    try:
        return flask.render_template(
            'memberapp/people.html',
            member=flask_login.current_user,
            nav_id=3,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            cycle=cycle,
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/people/<int:member_id>')
@ShouldBeMember
def ShowMember(member_id):
    try:
        mem = models.User.query.get(member_id)
        if not mem:
            flask.abort(403)

        comments = models.MemberComment.query.filter(
            models.MemberComment.member_id == mem.id).order_by(
                models.MemberComment.timestamp.desc()).all()

        return flask.render_template(
            'memberapp/profile.html',
            member=flask_login.current_user,
            profile_member=mem,
            nav_id=3,
            cycle=mem.cycle,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            comments=comments,
            snotes=Note(0),
            rnotes=Note(1))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/calendar')
@ShouldBeMember
def ShowCalendar():
    try:
        return flask.render_template(
            'calendar.html',
            member=flask_login.current_user,
            nav_id=5,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/stememo')
@ShouldBeMember
def ShowSTEMemoFirstPage():
    return flask.redirect(flask.url_for('.ShowSTEMemo', page=1))

@member_app.route('/stememo/<int:page>')
@ShouldBeMember
def ShowSTEMemo(page):

    if page == 0:
        flask.abort(404)

    total_num = len(models.Memo.query.all())
    end = total_num - 10 * (page - 1)
    start = total_num - 10 * page
    maxpage = math.ceil(total_num / 10)

    if start < 1:
        start = 0
    if end < 1:
        flask.abort(404)

    memoes = models.Memo.query.all()[start:end:][::-1]

    try:
        return flask.render_template(
            'memo.html',
            current_user=flask_login.current_user,
            nav_id=6,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            memoes=memoes,
            maxpage=maxpage,
            page=page,
            total_num=total_num,
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/board')
@ShouldBeMember
def ShowBoardList():
    try:
        if flask.request.args.get('gid'):
            gid = flask.request.args.get('gid')
            bgroups = models.Bgroup.query.filter_by(id=gid).first()
        else:
            bgroups = models.Bgroup.query.all()
        return flask.render_template(
            'post_group.html',
            current_user=flask_login.current_user,
            nav_id=7,
            bgroups=bgroups,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/board/personal/<int:member_id>')
@ShouldBeMember
def ShowPersonalBoard(member_id):
    board = models.BoardMember.query.filter_by(group_id=10).filter_by(
        owner_id=member_id).first()
    if board:
        return flask.redirect(
            flask.url_for('.ShowBoardFirstPage', boardmember_id=board.id))
    else:
        flask.abort(404)

@member_app.route('/board/recent/<int:postmember_id>')
@ShouldBeMember
def RecentPost(postmember_id):
    rboard_recent = models.PostMember.query.order_by(
        models.PostMember.timestamp.desc()).limit(10).all()
    current_post = models.PostMember.query.filter_by(
        id=postmember_id).first_or_404()

    if current_post in rboard_recent:
        return flask.redirect(
            flask.url_for(
                '.ShowPost',
                boardmember_id=current_post.boardmember_id,
                postmember_id=postmember_id))
    else:
        flask.abort(404)

@member_app.route('/board/<int:boardmember_id>')
@ShouldBeMember
def ShowBoardFirstPage(boardmember_id):
    return flask.redirect(
        flask.url_for('.ShowPage', boardmember_id=boardmember_id, page=1))

@member_app.route(
    '/board/<int:boardmember_id>/_<int:page>', methods=['GET', 'POST'])
@ShouldBeMember
def ShowPage(boardmember_id, page):
    if page == 0:
        flask.abort(404)

    try:

        preference = flask_login.current_user.preferred_boards
        preferred_boards = []
        for b in preference:
            preferred_boards.append(b.id)

        board = models.BoardMember.query.get(boardmember_id)

        if not board:
            flask.abort(404)

        if flask.request.args.get('search'):
            post_search = []
            if flask.request.args.get('searchtype') == '0':
                for post in board.posts:
                    if flask.request.args.get('search') in post.title:
                        post_search.append(post)
            if flask.request.args.get('searchtype') == '1':
                for post in board.posts:
                    if flask.request.args.get(
                            'search') in post.memberwriter.nickname:
                        post_search.append(post)
            if flask.request.args.get('searchtype') == '2':
                for post in board.posts:
                    if flask.request.args.get('search') in post.body:
                        post_search.append(post)
            postlist = post_search
        else:
            postlist = board.posts.all()

        totalpost = len(postlist)
        if totalpost == 0:
            if page != 1:
                flask.abort(404)
            end = 0
            start = 0
        else:
            end = totalpost - 10 * (page - 1)
            start = totalpost - 10 * page
            if start < 1:
                start = 0
            if end < 1:
                flask.abort(404)

        maxpage = math.ceil(totalpost / 10)

        posts = postlist[start:end:]

        post_parser = reqparse.RequestParser()
        post_parser.add_argument('board_title', type=str, default='')
        post_parser.add_argument('owner_id', type=str, default='')
        post_parser.add_argument('owner_name', type=str, default='')
        args = post_parser.parse_args()

        if args['board_title']:
            board.title = args['board_title']
            db.session.add(board)
            db.session.commit()
        elif args['owner_id'] and args['owner_name']:
            new_owner = models.User.query.filter_by(
                username=args['owner_id']).first()
            if new_owner is None:
                flask.flash('주어진 정보에 일치하는 회원이 없습니다.')

            elif board.group_id == 10:  # boardgroup 10 = '개인게시판'
                flask.flash('개인게시판은 게시판 주를 변경할 수 없습니다.')

            elif new_owner.nickname != args['owner_name']:
                flask.flash('주어진 정보에 일치하는 회원이 없습니다.')

            elif not new_owner.ismember:
                flask.flash('해당 회원은 게시판 주가 될 수 없습니다.')

            else:
                board.owner = new_owner
                db.session.add(board)
                db.session.commit()

        return flask.render_template(
            'post_list.html',
            member=flask_login.current_user,
            nav_id=7,
            board=board,
            posts=posts,
            maxpage=maxpage,
            page=page,
            totalpost=totalpost,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1),
            preferred_boards=preferred_boards)

    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/board/<int:boardmember_id>/<int:postmember_id>')
@ShouldBeMember
def ShowPost(boardmember_id, postmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        post = models.PostMember.query.get(postmember_id)
        comments = models.CommentMember.query.filter_by(
            postmember_id=postmember_id).order_by(
                models.CommentMember.timestamp).all()

        post_up = None
        post_down = None

        if post not in board.posts:
            flask.abort(404)

        if not board or not post:
            flask.abort(404)

        totalpost = len(board.posts[::-1])
        page = 1
        for s in range(totalpost):
            if post == board.posts[s]:
                if totalpost == 1:
                    pass
                elif s == totalpost - 1:
                    post_down = board.posts[s - 1]
                elif s == 0:
                    post_up = board.posts[s + 1]
                else:
                    post_up = board.posts[s + 1]
                    post_down = board.posts[s - 1]

        while True:
            end = totalpost - 10 * (page - 1)
            start = totalpost - 10 * page

            if start < 1:
                start = 0
            if end < 1:
                end = 0

            posts = board.posts[start:end:]

            if post in posts:
                break
            else:
                page = page + 1

        post.hitCount = post.hitCount + 1

        # if models.Conference.query.filter_by(record_id=post.id).first():
        #         conf = models.Conference.query.filter_by(record_id=post.id).first()

        #         statetable = models.MemberConference.query.filter_by(
        #                                     conference_id=conf.id)

        #         chulsuks = statetable.filter_by(state=0).all()
        #         bubunchams = statetable.filter_by(state=1).all()
        #         gonggyuls = statetable.filter(or_(models.MemberConference.state==2,
        #                            models.MemberConference.state==3)).all()
        #         gyulsuks = statetable.filter(or_(models.MemberConference.state==4,
        #                            models.MemberConference.state==5)).all()
        # else :
        #         chulsuks = None
        #         bubunchams = None
        #         gonggyuls = None
        #         gyulsuks = None

        db.session.commit()

        return flask.render_template(
            'post_view.html',
            member=flask_login.current_user,
            nav_id=7,
            board=board,
            post=post,
            page=page,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            post_up=post_up,
            post_down=post_down,
            comments=comments,
            snotes=Note(0),
            rnotes=Note(1))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/board/<int:boardmember_id>/<int:postmember_id>/modify')
@ShouldBeMember
def ModifyPost(boardmember_id, postmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        post = models.PostMember.query.get(postmember_id)

        if not board or not post or post not in board.posts:
            flask.abort(404)
        elif post.memberwriter != flask_login.current_user:
            flask.abort(403)

        return flask.render_template(
            'post_modify.html',
            member=flask_login.current_user,
            nav_id=7,
            board=board,
            post=post,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/board/<int:boardmember_id>/<int:postmember_id>/delete')
@ShouldBeMember
def DeletePost(boardmember_id, postmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        post = models.PostMember.query.get(postmember_id)

        if not board or not post or post not in board.posts:
            flask.abort(404)
        elif (post.memberwriter != flask_login.current_user) and (board.owner !=
                                                            flask_login.current_user):
            flask.abort(403)

        db.session.delete(post)
        db.session.commit()

        return flask.redirect(
            flask.url_for('.ShowBoardFirstPage', boardmember_id=boardmember_id))
    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/board/<int:boardmember_id>/write')
@ShouldBeMember
def WritePost(boardmember_id):
    try:
        board = models.BoardMember.query.get(boardmember_id)
        if not board:
            flask.abort(404)

        # if boardmember_id >= 3 and boardmember_id <=7 :
        #         recentyear = db.session.query(func.max(models.Quarter.year)
        #                    .label("recentyear")).first().recentyear
        #         recentsemester = db.session.query(func.max(models.Quarter.semester)
        #                        .label("recentsemester")).filter_by(year=recentyear)
        #                        .first().recentsemester
        #         current_quarter = models.Quarter.query.filter_by(year=recentyear)
        #                        .filter_by(semester=recentsemester).first()
        #         current_date = datetime.datetime.now().strftime('%Y-%m-%d')

        #         attendants = []

        #         for man in manager:
        #                 if man.cycle == recruitcycle:
        #                         attendants.append(man)

        #         if len(attendants) == 0:
        #                 for man in manager:
        #                         if man.cycle == recruitcycle-1:
        #                                 attendants.append(man)

        #         actives = models.User.query.filter(or_(
        #                models.User.deptstem_id==1,models.User.deptstem_id==3,
        #             models.User.deptstem_id==4)).order_by(models.User.deptstem_id).all()

        #         for active in actives:
        #                 attendants.append(active)

        #         buseos = []
        #         if boardmember_id == 4: # 대외교류부 부서회의
        #                 actives = models.User.query.filter_by(deptstem_id=3).all()
        #                 for active in actives:
        #                         buseos.append(active)
        #         elif boardmember_id == 5: # 봉사부 부서회의
        #                 actives = models.User.query.filter_by(deptstem_id=1).all()
        #                 for active in actives:
        #                         buseos.append(active)
        #         elif boardmember_id == 6: # 학술부 부서회의
        #                 actives = models.User.query.filter_by(deptstem_id=4).all()
        #                 for active in actives:
        #                         buseos.append(active)
        #         else:
        #                 buseos = attendants

        #         return flask.render_template('post_write.html',
        #         member=flask_login.current_user, nav_id=6, board=board,
        #         notifications=notification.Generate(flask_login.current_user),
        #         current=member_help.Current(), snotes=Note(0), rnotes=Note(1),
        #         quarter=current_quarter, date=current_date, attendants = attendants,
        #                    buseos=buseos)

        return flask.render_template(
            'post_write.html',
            member=flask_login.current_user,
            nav_id=7,
            board=board,
            notifications=notification.Generate(flask_login.current_user),
            prior_boards=models.BoardMember.query.filter(
                or_(models.BoardMember.id == 1,
                    models.BoardMember.id == 2)).all(),
            group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
            current=member_help.Current(),
            snotes=Note(0),
            rnotes=Note(1))

    except jinja2.TemplateNotFound:
        flask.abort(404)

@member_app.route('/record/write')
@ShouldBeMember
def WriteRecordList():
    current = member_help.Current()

    if flask_login.current_user not in current.active('actives'):
        flask.abort(403)

    limit = datetime.datetime.now() - datetime.timedelta(days=7)
    writable_records = models.Record.query.filter_by(
        writer_id=flask_login.current_user.id).filter(
            models.Record.confday >= limit).all()

    return flask.render_template(
        'record/record_writable.html',
        member=flask_login.current_user,
        nav_id=8,
        current=current,
        notifications=notification.Generate(flask_login.current_user),
        snotes=Note(0),
        rnotes=Note(1),
        prior_boards=models.BoardMember.query.filter(
            or_(models.BoardMember.id == 1, models.BoardMember.id == 2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
        records=writable_records)

@member_app.route('/record/write/<int:record_id>')
@ShouldBeMember
def WriteRecord(record_id):
    record = models.Record.query.get(record_id)

    if not record:
        flask.abort(404)

    current = member_help.Current()
    actives = current.active('actives')

    conf_id = 0
    if record.conftype == 0:
        conf_id = models.Conference.query.filter_by(
            record_id=record.id).first().id

    if record.conftype == 2:
        buseo = models.User.query.filter_by(ismember=1).filter_by(
            deptstem_id=3).all()
    elif record.conftype == 3:
        buseo = models.User.query.filter_by(ismember=1).filter_by(
            deptstem_id=1).all()
    elif record.conftype == 4:
        buseo = models.User.query.filter_by(ismember=1).filter_by(
            deptstem_id=4).all()
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
            attendance = body[0].split(
                '</p><p style="display:none;" class="forid">')
            att_0 = attendance[1].strip().split(' ')
            att_1 = attendance[2].strip().split(' ')
            att_2 = attendance[3].strip().split(' ')
            att_4 = attendance[4].strip().rstrip('</p> ').split(' ')

            body.pop(0)
            body = ''.join(body)
    else:
        body = ''
        att_0 = ['']
        att_1 = ['']
        att_2 = ['']
        att_4 = ['']

    if (flask_login.current_user not in current.active('actives')) or (
            flask_login.current_user.id != record.writer_id):
        flask.abort(403)

    limit = datetime.datetime.now() - datetime.timedelta(days=7)
    if not record.confday >= limit:
        flask.abort(403)

    return flask.render_template(
        'record/record_write.html',
        member=flask_login.current_user,
        nav_id=8,
        conf_id=conf_id,
        record=record,
        actives=actives,
        buseo=buseo,
        body=body,
        att_0=att_0,
        att_1=att_1,
        att_2=att_2,
        att_4=att_4,
        notifications=notification.Generate(flask_login.current_user),
        prior_boards=models.BoardMember.query.filter(
            or_(models.BoardMember.id == 1, models.BoardMember.id == 2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
        current=current,
        snotes=Note(0),
        rnotes=Note(1))

@member_app.route('/record', methods=['GET', 'POST'])
@ShouldBeMember
def ListRecord():
    record_parser = reqparse.RequestParser()
    record_parser.add_argument('conftypes', type=str)
    record_parser.add_argument('confstart', type=str)
    record_parser.add_argument('confplace', type=str)
    record_parser.add_argument('confend', type=str)
    record_parser.add_argument('conftitle', type=str)
    record_parser.add_argument('page', type=int)

    args = record_parser.parse_args()

    conftypes = args['conftypes']
    if not conftypes:
        conftypes = [0, 1, 2, 3, 4, 5]
    else:
        conftypes = [int(conftype) for conftype in conftypes.strip().split(' ')]

    confstart = args['confstart']
    if not confstart:
        confstart = datetime.datetime.strptime('2010-07-14', '%Y-%m-%d')
    else:
        confstart = datetime.datetime.strptime(confstart, '%Y-%m-%d')

    confend = args['confend']
    if not confend:
        confend = datetime.datetime.now()
    else:
        confend = datetime.datetime.strptime(confend, '%Y-%m-%d')

    if confstart > confend:
        confstart, confend = confend, confstart

    confplace = args['confplace']
    if not confplace:
        confplace = '%'
    else:
        confplace = '%' + confplace + '%'

    conftitle = args['conftitle']
    if not conftitle:
        conftitle = '%'
    else:
        conftitle = '%' + conftitle + '%'

    page = args['page']
    if page is None:
        page = 1

    records = models.Record.query.filter(
        models.Record.conftype.in_(conftypes)).filter(
            models.Record.confday >= confstart).filter(
                models.Record.confday <= confend).filter(
                    models.Record.confplace.like(confplace)).filter(
                        models.Record.title.like(conftitle)).order_by(
                            models.Record.confday).all()

    if page == 0:
        flask.abort(404)

    total_num = len(records)
    end = total_num - 10 * (page - 1)
    start = total_num - 10 * page
    maxpage = math.ceil(total_num / 10)

    if start < 1:
        start = 0
    if end < 1:
        end = 0

    records = records[start:end:][::-1]

    confstart = confstart.strftime('%Y-%m-%d')
    confend = confend.strftime('%Y-%m-%d')
    conftitle = conftitle.strip('%')
    confplace = confplace.strip('%')

    return flask.render_template(
        'record/record_list.html',
        member=flask_login.current_user,
        nav_id=8,
        current=member_help.Current(),
        records=records,
        page=page,
        maxpage=maxpage,
        notifications=notification.Generate(flask_login.current_user),
        prior_boards=models.BoardMember.query.filter(
            or_(models.BoardMember.id == 1, models.BoardMember.id == 2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
        snotes=Note(0),
        rnotes=Note(1),
        conftypes=conftypes,
        confstart=confstart,
        confend=confend,
        confplace=confplace,
        conftitle=conftitle)

@member_app.route('/record/view/<int:record_id>')
@ShouldBeMember
def ViewRecord(record_id):
    record = models.Record.query.get(record_id)
    comments = models.CommentRecord.query.filter_by(
        record_id=record_id).order_by(models.CommentRecord.timestamp).all()

    if not record:
        flask.abort(404)

    record.hitCount += 1

    db.session.commit()

    return flask.render_template(
        'record/record_view.html',
        member=flask_login.current_user,
        nav_id=8,
        record=record,
        comments=comments,
        notifications=notification.Generate(flask_login.current_user),
        snotes=Note(0),
        rnotes=Note(1),
        prior_boards=models.BoardMember.query.filter(
            or_(models.BoardMember.id == 1, models.BoardMember.id == 2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all(),
        current=member_help.Current())

@member_app.route('/record/make', methods=['GET', 'POST'])
@ShouldBeMember
def MakeRecord():
    current = member_help.Current()

    if flask_login.current_user not in current.active('actives'):
        flask.abort(403)

    quarter = current.quarter.id
    day = datetime.datetime.now().strftime('%Y-%m-%d')

    return flask.render_template(
        'record/record_make.html',
        member=flask_login.current_user,
        nav_id=8,
        current=current,
        quarter=quarter,
        confday=day,
        notifications=notification.Generate(flask_login.current_user),
        snotes=Note(0),
        rnotes=Note(1),
        prior_boards=models.BoardMember.query.filter(
            or_(models.BoardMember.id == 1, models.BoardMember.id == 2)).all(),
        group_lists=models.Bgroup.query.filter(models.Bgroup.id != 1).all())


class AutoRecordTitleResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        current = member_help.Current()
        year = current.year
        semester = current.semester

        if semester == 1:
            start = str(year) + '-03-01'
            start = datetime.datetime.strptime(start, '%Y-%m-%d')

        elif semester == 2:
            start = str(year) + '-07-01'
            start = datetime.datetime.strptime(start, '%Y-%m-%d')

        elif semester == 3:
            start = str(year) + '-09-01'
            start = datetime.datetime.strptime(start, '%Y-%m-%d')

        elif semester == 4:
            year += 1
            start = str(year) + '-01-01'
            start = datetime.datetime.strptime(start, '%Y-%m-%d')

        post_parser = reqparse.RequestParser()
        post_parser.add_argument('conftype', type=int)

        args = post_parser.parse_args()
        conftype = args['conftype']

        num = models.Record.query.filter(
            and_(models.Record.conftype == conftype,
                 models.Record.confday >= start,
                 models.Record.confday <= datetime.datetime.now())).options(
                     orm.load_only('id')).count()

        if conftype == 0:
            ret = '제 ' + str(num + 1) + '차 정기회의'
            return ret, 200
        elif conftype == 1:
            ret = '제 ' + str(num + 1) + '차 임원회의'
            return ret, 200
        elif conftype == 2:
            ret = '제 ' + str(num + 1) + '차 대외교류부 부서회의'
            return ret, 200
        elif conftype == 3:
            ret = '제 ' + str(num + 1) + '차 봉사부 부서회의'
            return ret, 200
        elif conftype == 4:
            ret = '제 ' + str(num + 1) + '차 학술부 부서회의'
            return ret, 200
        else:
            ret = '기타 회의'
            return ret, 200


class NewRecordResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('conftype', type=int)
        post_parser.add_argument('confday', type=str)
        post_parser.add_argument('confplace', type=str)
        post_parser.add_argument('conftitle', type=str)

        args = post_parser.parse_args()
        conftype = args['conftype']
        confday = args['confday']
        confplace = args['confplace']
        conftitle = args['conftitle']

        if not ((conftype in range(6)) and confday and confplace and conftitle):
            return 'Fail', 404

        if conftype == 0:
            title = '(정기회의) ' + confday + ' ' + conftitle
        elif conftype == 1:
            title = '(임원회의) ' + confday + ' ' + conftitle
        elif conftype == 2:
            title = '(대외교류부 부서회의) ' + confday + ' ' + conftitle
        elif conftype == 3:
            title = '(봉사부 부서회의) ' + confday + ' ' + conftitle
        elif conftype == 4:
            title = '(학술부 부서회의) ' + confday + ' ' + conftitle
        else:
            title = '(기타) ' + confday + ' ' + conftitle

        if conftype == 0:
            newrec = models.Record(
                conftype, datetime.datetime.strptime(confday, '%Y-%m-%d'),
                confplace, title, None, flask_login.current_user)
            newconf = models.Conference(conftitle,
                                        member_help.Current().quarter, newrec)
            db.session.add(newconf)
            db.session.add(newrec)
            db.session.commit()
            return newrec.id, 200
        else:
            newrec = models.Record(
                conftype, datetime.datetime.strptime(confday, '%Y-%m-%d'),
                confplace, title, None, flask_login.current_user)
            db.session.add(newrec)
            db.session.commit()
            return newrec.id, 200


class NewQuarterResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)
        recentyear = member_help.Current().year
        recentsemester = member_help.Current().semester

        newyear = recentyear
        newsemester = (recentsemester + 1) % 4

        if recentsemester == 4:
            newyear = newyear + 1

        if newsemester == 1:
            description = str(newyear) + '년 봄분기(' + str(newyear) + '.3월 ~ 6월)'
        elif newsemester == 2:
            description = str(newyear) + '년 여름분기(' + str(newyear) + '.7월 ~ 8월)'
        elif newsemester == 3:
            description = str(newyear) + '년 가을분기(' + str(newyear) + '.9월 ~ 12월)'
        elif newsemester == 4:
            description = str(newyear) + '년 겨울분기(' + str(newyear +
                                                         1) + '.1월 ~ 2월)'

        quarter = models.Quarter(newyear, newsemester)
        quarter.description = description
        db.session.add(quarter)
        db.session.commit()
        return 'Success', 200


class ModifyQuarterResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self, quarter_id):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('activity_score', type=int)
        post_parser.add_argument('conference_absence', type=int)

        args = post_parser.parse_args()

        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)

        quarter = models.Quarter.query.get(quarter_id)
        quarter.activity_score = args['activity_score']
        quarter.conference_absence = args['conference_absence']
        db.session.add(quarter)
        db.session.commit()
        return 'Success', 200


class BoardMemberResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('board_title', type=str)
        post_parser.add_argument('gid', type=int)
        post_parser.add_argument('special', type=int)
        args = post_parser.parse_args()

        board = models.BoardMember()
        board.title = args['board_title']
        board.special = args['special']
        board.owner_id = flask_login.current_user.id
        board.group_id = args['gid']

        db.session.add(board)
        db.session.commit()
        return 'Success', 200

    @ShouldBeMember
    def delete(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('boardmember_id', type=int)
        post_parser.add_argument('postmember_id', type=int)
        args = post_parser.parse_args()

        board = models.BoardMember.query.filter_by(
            id=args['boardmember_id']).first()
        post = models.Post.query.filter_by(id=args['postmember_id']).first()
        if not board or not post:
            flask.abort(404)
        if board.special == 0:
            post.boards.remove(board)
        db.session.add(post)
        db.session.commit()
        return 'Success', 200


class WriteRecordResource(flask_restful.Resource):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('body', type=str)

    @ShouldBeMember
    def put(self, record_id):
        current = member_help.Current()
        args = self.post_parser.parse_args()
        record = models.Record.query.get(record_id)
        if not record:
            flask.abort(404)

        if (flask_login.current_user not in current.active('actives')) or (
                flask_login.current_user.id != record.writer_id):
            flask.abort(403)

        record.body = args['body']

        files = flask.request.files.getlist('files')

        for file in files:
            if not helper.process_file(file, record):
                logging.error('Failed to process file %s', file.filename)

        db.session.commit()

        return 'Success', 200


class PostResource(flask_restful.Resource):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument(
        'title', type=str, required=True, help='Title is required')
    post_parser.add_argument('body', type=str, default='')
    post_parser.add_argument('boardmember_id', type=int, default=0)
    post_parser.add_argument('flask.redirect', type=str, default='')

    @ShouldBeMember
    def post(self):
        args = self.post_parser.parse_args()
        board = models.BoardMember.query.get(args['boardmember_id'])
        if not board:
            return None, 404
        post = models.PostMember(args['title'], args['body'],
                                 flask_login.current_user, board)
        db.session.add(post)

        files = flask.request.files.getlist('files')

        for file in files:
            if helper.process_file(file, post):
                logging.error('Failed to process file %s', file.filename)

        db.session.commit()
        return str(post)

    @ShouldBeMember
    def put(self, post_id):
        args = self.post_parser.parse_args()
        board = models.BoardMember.query.get(args['boardmember_id'])
        post = models.PostMember.query.get(post_id)
        if not board or not post:
            flask.abort(404)

        post.title = args['title']
        post.body = args['body']

        files = flask.request.files.getlist('files')

        for file in files:
            if not helper.process_file(file, post):
                logging.error('Failed to process file %s', file.filename)

        db.session.commit()
        return str(post)

    @ShouldBeMember
    def get(self, post_id):
        post = models.PostMember.query.get(post_id)
        if post:
            return str(post)
        return {}


class AddMemoResource(flask_restful.Resource):

    task_parser = reqparse.RequestParser()
    task_parser.add_argument('title', type=str)
    task_parser.add_argument('body', type=str)

    @ShouldBeMember
    def post(self):
        args = self.task_parser.parse_args()
        memo = models.Memo(args['title'], args['body'], flask_login.current_user)
        db.session.add(memo)
        db.session.commit()
        return 'Success', 200


class DeleteMemoResource(flask_restful.Resource):

    task_parser = reqparse.RequestParser()
    task_parser.add_argument('id', type=int, default=0)

    @ShouldBeMember
    def post(self):
        args = self.task_parser.parse_args()
        memo = models.Memo.query.filter_by(id=args['id']).first_or_404()
        if flask_login.current_user.id != memo.writer_id:
            return 'Not Allowed', 403

        db.session.delete(memo)
        db.session.commit()
        return 'Success', 200


class MakeActivityResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('type', type=int)
        post_parser.add_argument('name', type=str)
        post_parser.add_argument('totalscore', type=int)
        post_parser.add_argument('quarter_id', type=int)

        args = post_parser.parse_args()

        if args['quarter_id'] != member_help.Current().quarter.id:
            return flask.abort(403)
        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)

        activity = models.Activity(args['type'], args['name'],
                                   args['totalscore'])
        activity.quarter_id = args['quarter_id']

        if activity.type == 0:
            members = member_help.Current().active('actives')
            for member in members:
                activity.members.append(member)
        db.session.add(activity)
        db.session.commit()
        return 'Success', 200


class ModifyActivityResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('id', type=int)
        post_parser.add_argument('name', type=str)
        post_parser.add_argument('totalscore', type=int)

        args = post_parser.parse_args()

        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)

        activity = models.Activity.query.get(args['id'])
        activity.name = args['name']
        activity.totalscore = args['totalscore']
        db.session.add(activity)
        db.session.commit()
        return 'Success', 200


class DeleteActivityResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self, activity_id):
        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)
        activity = models.Activity.query.get(activity_id)
        db.session.delete(activity)
        db.session.commit()
        return 'Success', 200


class UpdateActivityScoreResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('activity_id', type=int)
        post_parser.add_argument('member_id', type=int)
        post_parser.add_argument('score', type=int)

        args = post_parser.parse_args()

        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)
        scoreforupdate = models.MemberActivity.query.filter(
            and_(
                models.MemberActivity.activity_id == args['activity_id'],
                models.MemberActivity.member_id == args['member_id'])).first()
        scoreforupdate.score = args['score']

        db.session.add(scoreforupdate)
        db.session.commit()
        return 'Success', 200


class AddActivityMemberResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('activity_id', type=int)
        post_parser.add_argument('member_ids', type=str)

        args = post_parser.parse_args()
        member_ids = args['member_ids'].strip().split(' ')
        member_ids = list(map(int, member_ids))

        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)

        activity = models.Activity.query.filter_by(
            id=args['activity_id']).first()

        for member_id in member_ids:
            member = models.User.query.filter_by(id=member_id).first()
            if member in activity.members:
                pass
            else:
                activity.members.append(member)

        db.session.add(activity)
        db.session.commit()

        return 'Success', 200


class DeleteActivityMemberResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('activity_id', type=int)
        post_parser.add_argument('member_id', type=int)
        args = post_parser.parse_args()

        if flask_login.current_user.id not in member_help.Current().page_manager_ids(
        ):
            return flask.abort(403)

        activity = models.Activity.query.filter_by(
            id=args['activity_id']).first()
        member = models.User.query.filter_by(id=args['member_id']).first()
        activity.members.remove(member)

        db.session.add(activity)
        db.session.commit()

        return 'Success', 200


class UpdateConferenceStateResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('conference_id', type=int)
        post_parser.add_argument('member_id', type=int)
        post_parser.add_argument('state', type=int)

        args = post_parser.parse_args()

        if flask.request.referrer.find('/stem/record/write/') > -1:
            if flask_login.current_user not in member_help.Current().active(
                    'actives'):
                return flask.abort(403)
        else:
            if flask_login.current_user.id not in member_help.Current(
            ).page_manager_ids():
                return flask.abort(403)

        stateforupdate = models.MemberConference.query.filter(
            and_(
                models.MemberConference.conference_id == args['conference_id'],
                models.MemberConference.member_id ==
                args['member_id'])).first()
        stateforupdate.state = args['state']

        db.session.add(stateforupdate)
        db.session.commit()
        return 'Success', 200


class AddConferenceMemberResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('conference_id', type=int)
        post_parser.add_argument('member_ids', type=str)

        args = post_parser.parse_args()
        member_ids = args['member_ids'].strip().split(' ')
        member_ids = list(map(int, member_ids))

        if flask.request.referrer.find('/stem/record/write/') > -1:
            if flask_login.current_user not in member_help.Current().active(
                    'actives'):
                return flask.abort(403)
        else:
            if flask_login.current_user.id not in member_help.Current(
            ).page_manager_ids():
                return flask.abort(403)

        conference = models.Conference.query.filter_by(
            id=args['conference_id']).first()

        for member_id in member_ids:
            member = models.User.query.filter_by(id=member_id).first()
            if member in conference.members:
                pass
            else:
                conference.members.append(member)

        db.session.add(conference)
        db.session.commit()

        return 'Success', 200


class DeleteConferenceMemberResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('conference_id', type=int)
        post_parser.add_argument('member_ids', type=str)
        args = post_parser.parse_args()

        member_ids = args['member_ids'].strip().split(' ')
        member_ids = list(map(int, member_ids))

        if flask.request.referrer.find('/stem/record/write/') > -1:
            if flask_login.current_user not in member_help.Current().active(
                    'actives'):
                return flask.abort(403)
        else:
            if flask_login.current_user.id not in member_help.Current(
            ).page_manager_ids():
                return flask.abort(403)

        conference = models.Conference.query.filter_by(
            id=args['conference_id']).first()

        for member_id in member_ids:
            member = models.User.query.filter_by(id=member_id).first()
            if member in conference.members:
                conference.members.remove(member)
            else:
                pass

        db.session.add(conference)
        db.session.commit()

        return 'Success', 200

comment_fields = {
    'id': fields.Integer,
    'body': fields.String,
    'timestamp': fields.DateTime,
    'member_id': fields.Integer,
    'writer_id': fields.Integer
}


class MemberCommentResource(flask_restful.Resource):

    @ShouldBeMember
    @flask_restful.marshal_with(comment_fields)
    def post(self):
        comment_parser = reqparse.RequestParser()
        comment_parser.add_argument('member_id', type=int)
        comment_parser.add_argument('writer_id', type=int)
        comment_parser.add_argument('body', type=str)

        args = comment_parser.parse_args()
        member = models.User.query.get(args['member_id'])
        writer = models.User.query.get(args['writer_id'])
        if not member:
            return None, 404
        comment = models.MemberComment(args['body'], member, writer)

        db.session.add(comment)
        db.session.commit()

        return comment, 201

    @ShouldBeMember
    def delete(self, comment_id):
        comment = models.MemberComment.query.filter_by(id=comment_id).first()
        if comment:
            if flask_login.current_user == comment.writer:
                db.session.delete(comment)
                db.session.commit()
                return True, 200
            else:
                return False, 401
        else:
            return None, 404


class DeleteNoteResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        note_parser = reqparse.RequestParser()
        note_parser.add_argument('id', type=int)
        note_parser.add_argument('sent_del', type=int)
        note_parser.add_argument('recv_del', type=int)
        args = note_parser.parse_args()

        note = models.Note.query.filter_by(id=args['id']).first()

        if not note:
            return None, 404
        if flask_login.current_user not in [note.sender, note.receiver]:
            return None, 403

        if args['sent_del']:
            note.sent_del = args['sent_del']
        elif args['recv_del']:
            note.recv_del = args['recv_del']
        else:
            return False, 401

        db.session.add(note)
        db.session.commit()

        note = models.Note.query.get(args['id'])
        if note.sent_del != 0 and note.recv_del != 0:
            db.session.delete(note)
            db.session.commit()


class MakeNoteResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        note_parser = reqparse.RequestParser()
        note_parser.add_argument('receiver', type=str)
        note_parser.add_argument('sent_id', type=int)
        note_parser.add_argument('body', type=str)
        note_parser.add_argument('sendmail', type=int)
        args = note_parser.parse_args()

        note = models.Note()
        recv = models.User.query.filter_by(username=args['receiver']).first()
        if recv is None:
            return '해당 계정이 존재하지 않습니다.', 404
        if not recv.ismember:
            return ('공우 회원이 아닌 계정으로 쪽지를 보낼 수 ' '없습니다.'), 404
        if recv == flask_login.current_user:
            return '자기 자신에게 쪽지를 보낼 수 없습니다.', 404
        note.recv_id = recv.id
        note.sent_id = args['sent_id']
        note.timestamp = datetime.datetime.now()
        note.body = args['body']

        db.session.add(note)
        db.session.commit()

        receiver_img = note.receiver.img or 'profile/default.png'
        print(args['sendmail'])
        if args['sendmail'] == 1:
            html = flask.render_template(
                'memberapp/note_content.html',
                recv=recv,
                current_user=flask_login.current_user,
                body=args['body'])
            subject = (f'[공우(STEM)] {recv.nickname} 회원님, STEM 쪽지함에 '
                       '쪽지가 도착했습니다.')

            helper.send_email(recv.email, subject, html)

        msg = [
            f'{note.receiver.cycle}기 {note.receiver.nickname} 회원에게 '
            '쪽지가 전달되었습니다.', note.id, receiver_img, note.receiver.nickname,
            note.receiver.username,
            note.timestamp.strftime('%Y-%m-%d %H:%M'), note.body
        ]

        return msg, 200


class ReadNoteResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self):
        note_parser = reqparse.RequestParser()
        note_parser.add_argument('id', type=int)
        note_parser.add_argument('recv_read', type=int)
        args = note_parser.parse_args()

        note = models.Note.query.filter_by(id=args['id']).first()
        if not note:
            return None, 404

        if flask_login.current_user != note.receiver:
            return None, 403

        if note.recv_read == 0 and args['recv_read'] != 0:
            note.recv_read = 1
            db.session.add(note)
            db.session.commit()
            return 'Success', 200

        return 'Success', 200


class FavoriteResource(flask_restful.Resource):

    @ShouldBeMember
    def post(self, boardmember_id):
        board = models.BoardMember.query.filter_by(
            id=boardmember_id).first_or_404()
        if board in flask_login.current_user.preferred_boards:
            return 'Error', 404
        else:
            flask_login.current_user.preferred_boards.append(board)
            db.session.add(flask_login.current_user)
            db.session.commit()
            return 'Successdd', 200

    @ShouldBeMember
    def delete(self, boardmember_id):
        board = models.BoardMember.query.filter_by(
            id=boardmember_id).first_or_404()
        for b in flask_login.current_user.preferred_boards:
            if board.id == b.id:
                pref = models.MemberPreference.query.filter(
                    and_(
                        models.MemberPreference.member_id ==
                        flask_login.current_user.id,
                        models.MemberPreference.boardmember_id ==
                        board.id)).first()
                db.session.delete(pref)
                db.session.commit()
                return 'Success', 200
        return 'Error', 404

comment_fields = {
    'id': fields.Integer,
    'body': fields.String,
    'timestamp': fields.DateTime
}


class CommentResource(flask_restful.Resource):

    @flask_restful.marshal_with(comment_fields)
    def get(self, comment_id, m_or_r):
        if m_or_r == 'M':  # False for BoardMember
            comment = models.CommentMember.query.get(comment_id)
        elif m_or_r == 'R':  # True for Record
            comment = models.CommentRecord.query.get(comment_id)
        else:
            return None, 404

        if comment:
            return comment
        return None, 404

    @ShouldBeMember
    @flask_restful.marshal_with(comment_fields)
    def post(self, m_or_r):
        comment_parser = reqparse.RequestParser()
        comment_parser.add_argument('body', type=str)
        comment_parser.add_argument('userID', type=int)
        comment_parser.add_argument('postID', type=int)

        args = comment_parser.parse_args()
        writer = models.User.query.get(args['userID'])
        if m_or_r == 'M':
            post = models.PostMember.query.get(args['postID'])
            if not post:
                return None, 404
            comment = models.CommentMember(args['body'], writer, post)
        elif m_or_r == 'R':
            post = models.Record.query.get(args['postID'])
            if not post:
                return None, 404
            comment = models.CommentRecord(args['body'], writer, post)
        else:
            return None, 404

        db.session.add(comment)
        db.session.commit()

        return comment, 201

    @ShouldBeMember
    def delete(self, comment_id, m_or_r):
        if m_or_r == 'M':  # False for BoardMember
            comment = models.CommentMember.query.get(comment_id)
            if comment:
                if (flask_login.current_user == comment.membercommenter) or (
                        flask_login.current_user ==
                        comment.postmember.boardmember.owner):
                    comment.remove()
                    return True, 200
                else:
                    return None, 404
            else:
                return None, 404
        elif m_or_r == 'R':  # True for Record
            comment = models.CommentRecord.query.get(comment_id)
            if comment:
                if flask_login.current_user == comment.recordcommenter:
                    comment.remove()
                    return True, 200
                else:
                    return None, 404
            else:
                return None, 404
        else:
            return None, 404

api.add_resource(AutoRecordTitleResource, '/api/record/autotitle')
api.add_resource(NewRecordResource, '/api/record/new')
api.add_resource(NewQuarterResource, '/api/quarter/new')
api.add_resource(ModifyQuarterResource, '/api/quarter/<int:quarter_id>/modify')
api.add_resource(BoardMemberResource, '/api/board')
api.add_resource(WriteRecordResource, '/api/record/write/<int:record_id>')
api.add_resource(PostResource, '/api/post', '/api/post/<int:post_id>')
api.add_resource(AddMemoResource, '/api/memo/add')
api.add_resource(DeleteMemoResource, '/api/memo/delete')
api.add_resource(MakeActivityResource, '/api/activity/make')
api.add_resource(ModifyActivityResource, '/api/activity/modify')
api.add_resource(DeleteActivityResource, '/api/activity/<int:activity_id>/delete')
api.add_resource(UpdateActivityScoreResource,
                 '/api/quarter/memberactivity/update')
api.add_resource(AddActivityMemberResource, '/api/quarter/memberactivity/add')
api.add_resource(DeleteActivityMemberResource,
                 '/api/quarter/memberactivity/delete')
api.add_resource(UpdateConferenceStateResource,
                 '/api/quarter/memberconference/update')
api.add_resource(AddConferenceMemberResource,
                 '/api/quarter/memberconference/add')
api.add_resource(DeleteConferenceMemberResource,
                 '/api/quarter/memberconference/delete')
api.add_resource(MemberCommentResource, '/api/people/comment',
                 '/api/people/comment/<int:comment_id>')
api.add_resource(DeleteNoteResource, '/api/note/delete')
api.add_resource(MakeNoteResource, '/api/note/make')
api.add_resource(ReadNoteResource, '/api/note/read')
api.add_resource(FavoriteResource, '/api/favorite/add/<int:boardmember_id>',
                 '/api/favorite/del/<int:boardmember_id>')
api.add_resource(CommentResource, '/api/post/comment/<string:m_or_r>',
                 '/api/post/comment/<string:m_or_r>/<int:comment_id>')
