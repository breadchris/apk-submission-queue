import os
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

db_path = 'sqlite:///pwn.db'
engine = create_engine(db_path, convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class Task(Base):
    __tablename__ = "task"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer(), unique=True)

    def __init__(self, task_id):
        self.task_id = task_id

    def __repr__(self):
        return '<Task %r>' % (self.task_id)

class TaskStatus(Base):
    __tablename__ = "task_status"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('task.id'),
        nullable=False)
    status_time = Column(DateTime)
    desc = Column(Text, nullable=False)

    def __init__(self, task_id, status_time, desc):
        self.task_id = task_id
        self.status_time = status_time
        self.desc = desc

    def __repr__(self):
        return '<TaskStatus %r %r %s>' % (self.task_id, self.status_time, self.desc)

class Emulator(Base):
    __tablename__ = "emulator"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    busy = Column(Integer)

    def __init__(self, name):
        self.name = name
        self.busy = 0

    def __repr__(self):
        return '<Emulator %r>' % (self.name)

def init_db():
	if not os.path.exists(db_path):
	    Base.metadata.create_all(engine)
