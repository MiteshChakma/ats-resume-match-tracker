import os
BASE_Dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_Dir, 'instance', 'ats_tracker.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False