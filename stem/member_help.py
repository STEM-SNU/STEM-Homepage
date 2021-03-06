import flask_restful
from sqlalchemy import or_
from sqlalchemy.sql.expression import func

from stem import db
from stem import models


class Current(flask_restful.Resource):

    def __init__(self):
        self.cycle = db.session.query(
            func.max(models.User.cycle).label("cycle")).first().cycle
        self.membernum = db.session.query(
            models.User).filter_by(ismember=True).count()
        self.year = db.session.query(
            func.max(
                models.Quarter.year).label("recentyear")).first().recentyear
        self.semester = db.session.query(
            func.max(
                models.Quarter.semester).label("recentsemester")).filter_by(
                    year=self.year).first().recentsemester
        self.quarter = models.Quarter.query.filter_by(year=self.year).filter_by(
            semester=self.semester).first()

    @staticmethod
    def page_manager_ids():
        cycle = db.session.query(func.max(
            models.User.cycle).label("cycle")).first().cycle
        page_manager = models.User.query.filter(
            or_(models.User.cycle == cycle,
                models.User.cycle == cycle - 1)).filter(
                    or_(models.User.deptstem_id == 5,
                        models.User.deptstem_id == 6)).all()
        page_manager_ids = []
        for page_man in page_manager:
            page_manager_ids.append(page_man.id)
        return page_manager_ids

    @staticmethod
    def active(text):
        cycle = db.session.query(func.max(
            models.User.cycle).label("cycle")).first().cycle
        page_manager = models.User.query.filter(
            or_(models.User.cycle == cycle,
                models.User.cycle == cycle - 1)).filter(
                    or_(models.User.deptstem_id == 5,
                        models.User.deptstem_id == 6)).order_by(
                            models.User.deptstem_id).all()
        if text == "executives":
            manager_rec = []
            for man in page_manager:
                if man.cycle == cycle:
                    manager_rec.append(man)

            if not manager_rec:
                for man in page_manager:
                    if man.cycle == cycle - 1:
                        manager_rec.append(man)
            return manager_rec

        elif text == "actives":
            active_members = []
            for man in page_manager:
                if man.cycle == cycle:
                    active_members.append(man)

            if not active_members:
                for man in page_manager:
                    if man.cycle == cycle - 1:
                        active_members.append(man)

            actives = models.User.query.filter(
                or_(models.User.deptstem_id == 1, models.User.deptstem_id == 3,
                    models.User.deptstem_id == 4)).order_by(
                        models.User.deptstem_id).all()

            for active in actives:
                active_members.append(active)
            return active_members

        else:
            return None

    @staticmethod
    def isapply():
        val = models.Configuration.query.filter_by(
            option="active_apply").first().value
        if val:
            return True
        else:
            return False
