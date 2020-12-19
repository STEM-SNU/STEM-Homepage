#-*-coding: utf-8 -*-
import os


basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SESSION_TYPE = 'filesystem'

MAIL_PASSWORD = '6QpR%9=6-gMg7Nc4'