from sqlalchemy import *
from database import Base
from datetime import datetime


class User(Base):

    __tablename__="users"

    id=Column(Integer,primary_key=True)

    username=Column(String(100),unique=True)

    password=Column(String(255))

    role=Column(String(50))


class Permission(Base):

    __tablename__="permissions"

    id=Column(Integer,primary_key=True)

    username=Column(String(100))

    column_name=Column(String(100))

    access=Column(String(50))


class LRData(Base):

    __tablename__="lr_data"

    id=Column(Integer,primary_key=True)

    lr_no=Column(String(100))

    customer=Column(String(255))

    origin=Column(String(255))

    destination=Column(String(255))

    version=Column(Integer,default=1)

    updated_by=Column(String(100))

    updated_at=Column(
        DateTime,
        default=datetime.utcnow
    )


class ReportRow(Base):

    __tablename__="report_rows"

    id=Column(Integer,primary_key=True)

    row_data=Column(Text)

    version=Column(Integer,default=1)

    updated_by=Column(String(100))

    updated_at=Column(
        DateTime,
        default=datetime.utcnow
    )


class AuditLog(Base):

    __tablename__="audit_logs"

    id=Column(Integer,primary_key=True)

    lr_no=Column(String(100))

    column_name=Column(String(100))

    old_value=Column(Text)

    new_value=Column(Text)

    updated_by=Column(String(100))

    timestamp=Column(
        DateTime,
        default=datetime.utcnow
    )
