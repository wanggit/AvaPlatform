"""SQLAlchemy 声明式模型基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 实体统一继承的基础类。"""

    pass
