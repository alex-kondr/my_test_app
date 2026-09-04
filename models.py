import os
from typing import Any, Generator, Optional
from datetime import datetime, date
from decimal import Decimal
import enum

from sqlalchemy import String, Text, Boolean, DateTime, func, create_engine, Enum, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, sessionmaker, Session
from dotenv import load_dotenv
from sqlalchemy.orm.session import Session


load_dotenv()

engine = create_engine(
    os.getenv("SQLALCHEMY_URI"),
    echo=True,
    pool_pre_ping=True,  # Перевіряє життєздатність з'єднання перед використанням
)

# Фабрика для створення сесій
DBSession = sessionmaker(bind=engine, expire_on_commit=False)


class Status(enum.Enum):
    in_progress = "In progress"
    done = "Done"
    qc = "QC"
    accepted = "Accepted"
    running = "Running"


class AgentType(str, enum.Enum):
    BIG = "Big"
    MEDIUM = "Medium"
    SMALL = "Small"

    @property
    def price(self) -> Decimal:
        prices = {
            AgentType.BIG: Decimal("7.00"),
            AgentType.MEDIUM: Decimal("5.00"),
            AgentType.SMALL: Decimal("3.00"),
        }
        return prices[self]


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)


class AgentModel(Base):
    __tablename__ = "agent"

    agent_id: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(100))
    source_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(1000), nullable=True, default=None)
    priority: Mapped[str] = mapped_column(String(10), nullable=True, default=None)
    group: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.in_progress)
    done: Mapped[bool] = mapped_column(Boolean(), default=False)
    bb: Mapped[bool] = mapped_column(Boolean(), default=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date(), default=None)
    count_emit: Mapped[Optional[int]] = mapped_column(default=0)
    max_emit: Mapped[Optional[int]] = mapped_column(default=0)
    old_code: Mapped[str] = mapped_column(Text, default=None, nullable=True)
    new_code: Mapped[str] = mapped_column(Text, default=None, nullable=True)
    agent_type: Mapped[str] = mapped_column(String(50), default=AgentType.MEDIUM.value)
    agent_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    extra_time: Mapped[bool] = mapped_column(Boolean(), default=False)
    create_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    update_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, agent_type: AgentType = AgentType.MEDIUM, **kwargs):
        super().__init__(
            agent_type=agent_type.value,
            agent_price=agent_type.price,
            **kwargs
        )


def get_db() -> Generator[Session, Any, None]:
    with DBSession() as session:
        yield session


# if __name__ == "__main__":
#     Base.metadata.drop_all(bind=engine)
#     Base.metadata.create_all(bind=engine)