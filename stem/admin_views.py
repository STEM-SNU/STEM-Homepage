import datetime
import logging
import os

import flask
import flask_admin
import flask_login
from flask_admin.contrib import sqla
from flask_admin import form as admin_form
import flask_wtf
import wtforms
from wtforms import widgets
from wtforms import validators

from stem import admin
from stem import app
from stem import db
from stem import models

ADMIN_USERS = ['wwee3631', 'stem_admin', 'jun9303']


class CKTextAreaWidget(widgets.TextArea):

    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckeditor'
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(wtforms.TextAreaField):
    widget = CKTextAreaWidget()


class HistoryForm(flask_wtf.Form):
    start = wtforms.DateField(
        'Start',
        validators=[validators.DataRequired()],
        widget=admin_form.DatePickerWidget())
    one_day = wtforms.BooleanField('One-day event')
    end = wtforms.DateField(
        'End',
        validators=[validators.Optional()],
        widget=admin_form.DatePickerWidget())
    content = wtforms.TextAreaField(
        'Content', validators=[validators.DataRequired()])

    @staticmethod
    def validate_end(form, field):
        if not form.one_day.data:
            try:
                if form.start.data > field.data:
                    raise validators.ValidationError('Start date should be '
                                                     'earlier than end date')
            except Exception:
                raise validators.ValidationError('Incorrect date format')


class AuthView(flask_admin.BaseView):

    @flask_login.login_required
    def is_accessible(self):
        return flask_login.current_user.username in ADMIN_USERS


class AuthModelView(sqla.ModelView):

    @flask_login.login_required
    def is_accessible(self):
        return flask_login.current_user.username in ADMIN_USERS


class UserView(AuthModelView):
    column_list = ['username', 'nickname', 'email', 'ismember']
    column_searchable_list = ['username', 'nickname', 'email', 'cycle', 'phone']
    column_editable_list = ['email']
    form_excluded_columns = [
        'last_mod', 'sent_notifications', 'received_notifications',
        'owned_boards', 'member_comments', 'public_comments', 'record_comments',
        'profile_comments_recv', 'profile_comments_writ', 'activities',
        'conferences', 'received_profile_comments', 'writing_profile_comments',
        'boardmember', 'preferred_boards', 'memoes', 'sent_notes',
        'received_notes', 'member_posts', 'public_posts', 'member_posts',
        'records', 'activity', 'conference', 'img', 'cover'
    ]

    form_overrides = {
        'cvpublic': wtforms.TextAreaField,
        'cvmember': wtforms.TextAreaField
    }

    def __init__(self, session, **kwargs):
        super(UserView, self).__init__(models.User, session, **kwargs)


admin.add_view(UserView(db.session, name='User'))


class BannerView(AuthModelView):
    column_list = ['src', 'href', 'description']
    column_searchable_list = ['src', 'description']
    column_editable_list = ['src', 'href', 'description']

    can_edit = False

    def __init__(self, session, **kwargs):
        super(BannerView, self).__init__(models.Banner, session, **kwargs)


admin.add_view(BannerView(db.session, name='Banner'))


class ConfigurationView(AuthModelView):
    column_list = ['option', 'value']
    column_editable_list = ['value']

    can_create = False
    can_edit = False
    can_delete = False

    def __init__(self, session, **kwargs):
        super(ConfigurationView, self).__init__(models.Configuration, session,
                                                **kwargs)


admin.add_view(ConfigurationView(db.session, name='Isactive'))


class DeptStemView(AuthModelView):
    column_list = ['id', 'name']
    column_editable_list = ['name']

    def __init__(self, session, **kwargs):
        super(DeptStemView, self).__init__(models.DeptStem, session, **kwargs)


admin.add_view(DeptStemView(db.session, name='StemDepartment'))


class DeptUnivView(AuthModelView):
    column_list = ['id', 'name']
    column_editable_list = ['name']

    def __init__(self, session, **kwargs):
        super(DeptUnivView, self).__init__(models.DeptUniv, session, **kwargs)


admin.add_view(DeptUnivView(db.session, name='UnivDepartment'))


class HistoryView(AuthModelView):
    form = HistoryForm
    column_list = ['content', 'starttime']

    can_view_details = False

    def __init__(self, session, **kwargs):
        super(HistoryView, self).__init__(models.History, session, **kwargs)

    def create_model(self, form):
        try:
            end = ''
            if not form.one_day.data:
                end = form.end.data
            model = models.History(form.content.data, form.start.data, end)
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
        except Exception as e:
            if not self.handle_view_exception(e):
                flask.flash(f'Failed to create record. {e}s', 'error')
                logging.exception('Failed to create record.',)

            self.session.rollback()

            return False
        else:
            self.after_model_change(form, model, True)

        return True

    def update_model(self, form, model):
        try:
            end = ''
            if not form.one_day.data:
                end = form.end.data
            model.content = form.content.data
            start_date = form.start.data
            end_date = end

            timezero = datetime.time(tzinfo=datetime.timezone.utc)
            model.starttime = datetime.datetime.combine(start_date, timezero)
            if end_date and end_date != start_date:
                endtime = datetime.datetime.combine(end_date, timezero)
                model.endtime = str(endtime.timestamp())
            self._on_model_change(form, model, False)
            self.session.commit()
        except Exception as e:
            if not self.handle_view_exception(e):
                flask.flash(f'Failed to update record. {e}s', 'error')
                logging.exception('Failed to update record.')

            self.session.rollback()

            return False
        else:
            self.after_model_change(form, model, False)

        return True

    def on_form_prefill(self, form, history_id):
        obj = models.History.query.get(history_id)
        if not obj:
            return
        form.start.data = obj.starttime
        if obj.endtime:
            form.end.data = datetime.datetime.utcfromtimestamp(
                float(obj.endtime))
        else:
            form.one_day.data = True
        form.content.data = obj.content


class FileView(AuthModelView):
    column_list = ['name', 'link']
    column_searchable_list = ['name']
    column_editable_list = ['name']

    can_create = False

    def __init__(self, session, **kwargs):
        super(FileView, self).__init__(models.File, session, **kwargs)

    def on_model_delete(self, model):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], model.link))


class BoardPublicView(AuthModelView):
    column_list = ['name', 'description']
    column_searchable_list = ['name', 'description']

    can_create = False
    can_delete = False

    def __init__(self, session, **kwargs):
        super(BoardPublicView, self).__init__(models.BoardPublic, session,
                                              **kwargs)


class PostPublicView(AuthModelView):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']

    form_overrides = {'body': CKTextAreaField}

    column_list = ['id', 'hidden', 'title', 'publicwriter', 'boardpublic']
    column_searchable_list = ['id', 'title']

    form_excluded_columns = ['files', 'hitCount', 'commentCount']

    def __init__(self, session, **kwargs):
        super(PostPublicView, self).__init__(models.PostPublic, session,
                                             **kwargs)


class CommentPublicView(AuthModelView):
    column_list = ['publiccommenter', 'body', 'postpublic']

    form_overrides = {'body': wtforms.TextAreaField}

    def __init__(self, session, **kwargs):
        super(CommentPublicView, self).__init__(models.CommentPublic, session,
                                                **kwargs)


class BoardMemberView(AuthModelView):
    column_list = ['title', 'owner', 'group']
    column_searchable_list = ['title']

    form_excluded_columns = ['preferred_members']

    def __init__(self, session, **kwargs):
        super(BoardMemberView, self).__init__(models.BoardMember, session,
                                              **kwargs)


class PostMemberView(AuthModelView):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']

    form_overrides = {'body': CKTextAreaField}

    column_list = ['id', 'title', 'memberwriter', 'boardmember']
    column_searchable_list = ['id', 'title']

    form_excluded_columns = ['files', 'hitCount', 'commentCount']

    def __init__(self, session, **kwargs):
        super(PostMemberView, self).__init__(models.PostMember, session,
                                             **kwargs)


class CommentMemberView(AuthModelView):
    column_list = ['membercommenter', 'body', 'postmember']

    form_overrides = {'body': wtforms.TextAreaField}

    def __init__(self, session, **kwargs):
        super(CommentMemberView, self).__init__(models.CommentMember, session,
                                                **kwargs)


class MemoView(AuthModelView):
    column_list = ['title', 'timestamp', 'writer']

    form_overrides = {'body': wtforms.TextAreaField}

    def __init__(self, session, **kwargs):
        super(MemoView, self).__init__(models.Memo, session, **kwargs)


class ConferenceView(AuthModelView):
    column_editable_list = ['name']

    form_excluded_columns = ['members', 'member']

    can_delete = False

    def __init__(self, session, **kwargs):
        super(ConferenceView, self).__init__(models.Conference, session,
                                             **kwargs)


class RecordView(AuthModelView):
    column_list = ['conftype', 'confday', 'confplace', 'title', 'recordwriter']
    form_excluded_columns = ['comments', 'files', 'hitCount', 'commentCount']

    column_editable_list = ['conftype', 'confday', 'confplace', 'title']

    column_searchable_list = ['title']

    form_overrides = {'body': CKTextAreaField}

    def __init__(self, session, **kwargs):
        super(RecordView, self).__init__(models.Record, session, **kwargs)


class CommentRecordView(AuthModelView):
    column_list = ['recordcommenter', 'body', 'record']

    def __init__(self, session, **kwargs):
        super(CommentRecordView, self).__init__(models.CommentRecord, session,
                                                **kwargs)


class ActivityView(AuthModelView):
    column_editable_list = ['type', 'name', 'totalscore']

    def __init__(self, session, **kwargs):
        super(ActivityView, self).__init__(models.Activity, session, **kwargs)


class QuarterView(AuthModelView):
    column_editable_list = ['activity_score', 'conference_absence']

    def __init__(self, session, **kwargs):
        super(QuarterView, self).__init__(models.Quarter, session, **kwargs)


admin.add_view(HistoryView(db.session, name='History'))
admin.add_view(FileView(db.session, name='File'))
admin.add_view(BoardPublicView(db.session, name='BoardPublic'))
admin.add_view(PostPublicView(db.session, name='PostPublic'))
admin.add_view(CommentPublicView(db.session, name='CommentPublic'))
admin.add_view(BoardMemberView(db.session, name='BoardMember'))
admin.add_view(PostMemberView(db.session, name='PostMember'))
admin.add_view(CommentMemberView(db.session, name='CommentMember'))
admin.add_view(MemoView(db.session, name='STEMemo'))
admin.add_view(ConferenceView(db.session, name='Conference'))
admin.add_view(RecordView(db.session, name='Record'))
admin.add_view(CommentRecordView(db.session, name='CommentRecord'))
admin.add_view(ActivityView(db.session, name='Activity'))
admin.add_view(QuarterView(db.session, name='Quarter'))

admin.init_app(app)
