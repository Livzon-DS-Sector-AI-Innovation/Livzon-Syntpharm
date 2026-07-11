"""Deviation Automation ORM models.

Extracted from deviation_automation_api.py.
"""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SOPRule(Base):
    __tablename__ = "sop_rule"
    __table_args__ = {"schema": "quality"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    sop_code = Column(String(64), nullable=False, unique=True)
    sop_full_name = Column(String(256), nullable=False)
    sop_version = Column(String(32), nullable=False)
    business_tag = Column(String(256))
    standard_limit = Column(Text)
    standard_sentence = Column(Text)
    sop_file_path = Column(String(512))
    status = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, nullable=False, default=datetime.now)
    update_time = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )


class DevTask(Base):
    __tablename__ = "dev_task"
    __table_args__ = {"schema": "quality"}

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    deviation_no = Column(String(64), nullable=False, unique=True)
    creator = Column(String(64), nullable=False)
    auditor = Column(String(64))
    report_date = Column(Date, nullable=False)
    original_file_path = Column(String(512))
    standard_file_path = Column(String(512))
    task_status = Column(SmallInteger, nullable=False, default=1)
    ai_result = Column(Text)
    create_time = Column(DateTime, nullable=False, default=datetime.now)
    update_time = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )


class ReportTemplate(Base):
    __tablename__ = "report_template"
    __table_args__ = {"schema": "quality"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    file_path = Column(String(512))
    is_active = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, nullable=False, default=datetime.now)
    update_time = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )