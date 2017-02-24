from app import app
from app import db, models, admin, lm
from flask.ext.admin.contrib.sqla import ModelView
from sqlalchemy import func
from flask.ext.login import login_user, logout_user, current_user, \
    login_required
from flask.ext.admin import BaseView, expose
from flask_admin import form
from flask_wtf import Form
from wtforms import TextAreaField, DateField, BooleanField
from wtforms.validators import Optional, DataRequired, ValidationError
import datetime
from flask_admin.helpers import get_form_data, validate_form_on_submit, \
    get_redirect_target, flash_errors

admin_users = ['wwee3631', 'stem_admin']


class AuthView(BaseView):
    @login_required
    def is_accessible(self):
        return current_user.username in admin_users


class AuthModelView(ModelView):
    @login_required
    def is_accessible(self):
        return current_user.username in admin_users


class UserView(AuthModelView):
    column_list = ('username', 'nickname', 'email', 'member')

    def __init__(self, session, **kwargs):
        super(UserView, self).__init__(models.User, session, **kwargs)


class MemberView(AuthModelView):
    column_list = ('user', 'cycle', 'phone', 'stem_department')
    column_exclude_list = ('task_comments','sent_notifications',
                        'received_notifications','profile_comments',
                        'member_comments')
    form_excluded_columns = ('task_comments','sent_notifications',
                        'received_notifications','profile_comments',
                        'member_comments')

    def __init__(self, session, **kwargs):
        super(MemberView, self).__init__(models.Member, session, **kwargs)

    def after_model_change(self, form, model, is_created):
        try:
            if not model.cycle:
                model.cycle = 0
                self.session.commit()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to update record. %(error)s',
                              error=str(ex)), 'error')
                log.exception('Failed to update record.')

            self.session.rollback()


class PostView(AuthModelView):
    column_list = ('board','tags','author','title','timestamp')
    form_excluded_columns = ('posts')
    def __init__(self, session, **kwargs):
        super(PostView, self).__init__(models.Post, session, **kwargs)

    def get_query(self):
        return (super(PostView, self).get_query()
                .filter(models.Post.board_id != 3))

    def get_count_query(self):
        return (super(PostView, self).get_count_query()
                .filter(models.Post.board_id != 3))


class HistoryForm(Form):
    start = DateField('Start', validators=[DataRequired()],
                      widget=form.DatePickerWidget())
    one_day = BooleanField('One-day event')
    end = DateField('End', validators=[Optional()],
                    widget=form.DatePickerWidget())
    description = TextAreaField('description', validators=[DataRequired()])

    def validate_end(form, field):
        if not form.one_day.data:
            try:
                if form.start.data > field.data:
                    raise ValidationError('Start date should be '
                                          'earlier than end date')
            except Exception:
                raise ValidationError('Incorrect date format')


class HistoryView(AuthModelView):
    form = HistoryForm
    column_list = ('title','timestamp')
    def __init__(self, session, **kwargs):
        super(HistoryView, self).__init__(models.Post, session, **kwargs)

    def get_query(self):
        return (super(HistoryView, self).get_query()
                .filter(models.Post.board_id == 3))

    def get_count_query(self):
        return (super(HistoryView, self).get_count_query()
                .filter(models.Post.board_id == 3))

    def create_model(self, form):
        """
            Create model from form.
            :param form:
                Form instance
        """
        try:
            end = None
            if not form.one_day.data:
                end = form.end.data
            model = models.Post.historyPost(form.description.data,
                                            form.start.data, end)
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
        """
            Update model from form.
            :param form:
                Form instance
            :param model:
                Model instance
        """
        try:
            end = None
            if not form.one_day.data:
                end = form.end.data
            #model.title = form.description.data.replace('<br>','').replace('\r','').replace('\n','<br>')
            model.title = form.description.data
            startDate = form.start.data
            endDate = end

            timezero = datetime.time(tzinfo=datetime.timezone.utc)
            model.timestamp = datetime.datetime.combine(startDate, timezero)
            if endDate and endDate != startDate:
                endtime = datetime.datetime.combine(endDate, timezero)
                model.body = str(endtime.timestamp())
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
        obj = models.Post.query.get(id)
        if not obj:
            return
        form.start.data = obj.timestamp
        if obj.body and obj.body != '':
            form.end.data = datetime.datetime.utcfromtimestamp(float(obj.body))
        else:
            form.one_day.data = True
        form.description.data = obj.title


class HistoryListView(AuthView):
    @expose('/')
    def index(self):
        items = (db.session.query(models.Post)
                 .filter(models.Post.board_id == 3)
                 .order_by(models.Post.timestamp.desc()).all())
        for post in items:
            post.period = post.timestamp.strftime('%y.%m.%d')
            if post.body and post.body != '':
                endDate = datetime.datetime.utcfromtimestamp(float(post.body))
                post.period = (post.period + ' ~ ' +
                               endDate.strftime('%y.%m.%d'))
        return self.render('admin_views/history.html', items=items)


admin.add_view(UserView(db.session))
admin.add_view(MemberView(db.session))
admin.add_view(AuthModelView(models.Board, db.session))
admin.add_view(AuthModelView(models.Department, db.session))
admin.add_view(AuthModelView(models.StemDepartment, db.session))
admin.add_view(AuthModelView(models.File, db.session))
admin.add_view(PostView(db.session, name='Post'))
admin.add_view(HistoryView(db.session, name='History', endpoint='History'))
admin.add_view(HistoryListView(name='HistoryList', endpoint='history-list'))
admin.add_view(AuthModelView(models.Banner, db.session))
admin.add_view(AuthModelView(models.Tag, db.session))
admin.init_app(app)
