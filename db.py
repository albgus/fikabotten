from sqlalchemy import create_engine, Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import time

Base = declarative_base()

server_users = Table('channel_users', Base.metadata,
    Column('user_id', ForeignKey('users.id'), primary_key=True),
    Column('sever_id', ForeignKey('servers.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    last_trigger = Column(Integer) # Check best storage format.
    trigger_count = Column(Integer)

    triggers = relationship('Trigger')

    servers = relationship('Server',
                            secondary=server_users,
                            back_populates='users')

class Server(Base):
    __tablename__ = 'servers'

    id = Column(Integer, primary_key=True)
    users = relationship('User',
                        secondary=server_users,
                        back_populates='servers')

class Trigger(Base):
    __tablename__ = 'triggers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='triggers')
    server_id = Column(Integer, ForeignKey('servers.id'))
    timestamp = Column(Integer)

