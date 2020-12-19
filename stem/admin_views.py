import os

from stem import app
from stem import db, models, admin, login_manager
from flask.ext.admin.contrib.sqla import ModelView
from sqlalchemy import func
from flask.ext.login import login_user, logout_user, current_user, \
    login_required
from flask.ext.admin import BaseView, expose
from flask_admin import form
from flask_wtf import Form
from wtforms import TextAreaField, DateField, BooleanField
from wtforms.widgets import TextArea
from wtforms.validators import Optional, DataRequired, ValidationError
import datetime
from flask_admin.helpers import get_form_data, validate_form_on_submit, \
    get_redirect_target, flash_errors

admin_users = ['wwee3631', 'stem_admin', 'jun9303']

class CKTextAreaWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckeditor'
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)

class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget()

class HistoryForm(Form):
    start = DateField('Start', validators=[DataRequired()],
                      widget=form.DatePickerWidget())
    one_day = BooleanField('One-day event')
    end = DateField('End', validators=[Optional()],
                    widget=form.DatePickerWidget())
    content = TextAreaField('Content', validators=[DataRequired()])

    def validate_end(form, field):
        if not form.one_day.data:
            try:
                if form.start.data > field.data:
                    raise ValidationError('Start date should be '
                                          'earlier than end date')
            except Exception:
                raise ValidationError('Incorrect date format')

class AuthView(BaseView):
    @login_required
    def is_accessible(self):
        return current_user.username in admin_users


class AuthModelView(ModelView):
    @login_required
    def is_accessible(self):
        return current_user.username in admin_users


class UserView(AuthModelView):
    column_list = ['username', 'nickname', 'email','ismember']
    column_searchable_list = ['username', 'nickname', 'email', 'cycle', 'phone']
    column_editable_list = ['email']
    form_excluded_columns = ['last_mod', 'sent_notifications', 'received_notifications', 'owned_boards',
                            'member_comments', 'public_comments', 'record_comments', 'profile_comments_recv',
                            'profile_comments_writ', 'activities', 'conferences', 'received_profile_comments',
                            'writing_profile_comments', 'boardmember',
                            'preferred_boards', 'memoes', 'sent_notes', 'received_notes', 'member_posts',
                            'public_posts', 'member_posts', 'records', 'activity', 'conference', 'img', 'cover']

    form_overrides = {
        'cvpublic': TextAreaField,
        'cvmember': TextAreaField
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
        super(ConfigurationView, self).__init__(models.Configuration, session, **kwargs)
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
        except Exception as ex:
            if not self.handle_view_exception(ex):
               flash(gettext('Failed to create record. %(error)s',
                             error=str(ex)), 'error')
               log.exception('Failed to create record.')

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
            startDate = form.start.data
            endDate = end

            timezero = datetime.time(tzinfo=datetime.timezone.utc)
            model.starttime = datetime.datetime.combine(startDate, timezero)
            if endDate and endDate != startDate:
                endtime = datetime.datetime.combine(endDate, timezero)
                model.endtime = str(endtime.timestamp())
            self._on_model_change(form, model, False)
            self.session.commit()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to update record. %(error)s',
                              error=str(ex)), 'error')
                log.exception('Failed to update record.')

            self.session.rollback()

            return False
        else:
            self.after_model_change(form, model, False)

        return True

    def on_form_prefill(self, form, id):
        obj = models.History.query.get(id)
        if not obj:
            return
        form.start.data = obj.starttime
        if obj.endtime and obj.endtime != '':
            form.end.data = datetime.datetime.utcfromtimestamp(float(obj.endtime))
        else:
            form.one_day.data = True
        form.content.data = obj.content
admin.add_view(HistoryView(db.session, name='History'))

class FileView(AuthModelView):
    column_list = ['name', 'link']
    column_searchable_list = ['name']
    column_editable_list = ['name']

    can_create = False

    def __init__(self, session, **kwargs):
        super(FileView, self).__init__(models.File, session, **kwargs)

    def on_model_delete(self, model):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], model.link))

admin.add_view(FileView(db.session, name='File'))

class BoardPublicView(AuthModelView):
    column_list = ['name', 'description']
    column_searchable_list = ['name', 'description']

    can_create = False
    can_delete = False

    def __init__(self, session, **kwargs):
        super(BoardPublicView, self).__init__(models.BoardPublic, session, **kwargs)
admin.add_view(BoardPublicView(db.session, name='BoardPublic'))

class PostPublicView(AuthModelView):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']

    form_overrides = {
        'body': CKTextAreaField
    }

    column_list = ['id', 'hidden', 'title', 'publicwriter', 'boardpublic']
    column_searchable_list = ['id', 'title']

    form_excluded_columns = ['files', 'hitCount', 'commentCount']

    def __init__(self, session, **kwargs):
        super(PostPublicView, self).__init__(models.PostPublic, session, **kwargs)
admin.add_view(PostPublicView(db.session, name='PostPublic'))

class CommentPublicView(AuthModelView):
    column_list = ['publiccommenter', 'body', 'postpublic']

    form_overrides = {
        'body': TextAreaField
    }

    def __init__(self, session, **kwargs):
            super(CommentPublicView, self).__init__(models.CommentPublic, session, **kwargs)

admin.add_view(CommentPublicView(db.session, name='ComntPublic'))

class BoardMemberView(AuthModelView):
    column_list = ['title', 'owner', 'group']
    column_searchable_list = ['title']

    form_excluded_columns = ['preferred_members']

    def __init__(self, session, **kwargs):
        super(BoardMemberView, self).__init__(models.BoardMember, session, **kwargs)
admin.add_view(BoardMemberView(db.session, name='BoardMember'))

class PostMemberView(AuthModelView):
    extra_js = ['//cdn.ckeditor.com/4.6.0/standard/ckeditor.js']

    form_overrides = {
        'body': CKTextAreaField
    }

    column_list = ['id', 'title', 'memberwriter', 'boardmember']
    column_searchable_list = ['id', 'title']

    form_excluded_columns = ['files', 'hitCount', 'commentCount']

    def __init__(self, session, **kwargs):
        super(PostMemberView, self).__init__(models.PostMember, session, **kwargs)
admin.add_view(PostMemberView(db.session, name='PostMember'))

class CommentMemberView(AuthModelView):
    column_list = ['membercommenter', 'body', 'postmember']

    form_overrides = {
        'body': TextAreaField
    }

    def __init__(self, session, **kwargs):
            super(CommentMemberView, self).__init__(models.CommentMember, session, **kwargs)

admin.add_view(CommentMemberView(db.session, name='ComntMember'))

class MemoView(AuthModelView):
    column_list = ['title', 'timestamp', 'writer']

    form_overrides = {
        'body': TextAreaField
    }

    def __init__(self, session, **kwargs):
        super(MemoView, self).__init__(models.Memo, session, **kwargs)
admin.add_view(MemoView(db.session, name='STEMemo'))

class ConferenceView(AuthModelView):
   column_editable_list = ['name']

   form_excluded_columns = ['members', 'member']

   can_delete = False

   def __init__(self, session, **kwargs):
       super(ConferenceView, self).__init__(models.Conference, session, **kwargs)
admin.add_view(ConferenceView(db.session, name='Conference'))

class RecordView(AuthModelView):
    column_list = ['conftype', 'confday', 'confplace', 'title', 'recordwriter']
    form_excluded_columns = ['comments', 'files', 'hitCount', 'commentCount']

    column_editable_list = ['conftype', 'confday', 'confplace', 'title']

    column_searchable_list = ['title']

    form_overrides = {
        'body' : CKTextAreaField
    }

    def __init__(self, session, **kwargs):
        super(RecordView, self).__init__(models.Record, session, **kwargs)
admin.add_view(RecordView(db.session, name='Record'))

class CommentRecordView(AuthModelView):
    column_list = ['recordcommenter','body', 'record']

    def __init__(self, session, **kwargs):
        super(CommentRecordView, self).__init__(models.CommentRecord, session, **kwargs)
admin.add_view(CommentRecordView(db.session, name='ComntRecord'))

class ActivityView(AuthModelView):
   column_editable_list = ['type', 'name', 'totalscore']

   def __init__(self, session, **kwargs):
       super(ActivityView, self).__init__(models.Activity, session, **kwargs)
admin.add_view(ActivityView(db.session, name='Activity'))

class QuarterView(AuthModelView):
    column_editable_list = ['activity_score', 'conference_absence']

    def __init__(self, session, **kwargs):
        super(QuarterView, self).__init__(models.Quarter, session, **kwargs)
admin.add_view(QuarterView(db.session, name='Quarter'))

admin.init_app(app)
