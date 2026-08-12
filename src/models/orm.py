import uuid
from datetime import datetime as dt

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class BaseTable(DeclarativeBase):
    """Insert-only audit base."""

    serial_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id: Mapped[uuid.UUID] = mapped_column(
        unique=True,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(nullable=False)


class UpdatableBaseTable:
    """Mixin for mutable tables; updated_* stamped by DB trigger on UPDATE."""

    updated_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))
    updated_by_id: Mapped[uuid.UUID | None]


class AgentPlatformBase(BaseTable):
    __abstract__ = True
    __table_args__: tuple[object, ...] = ({"schema": "agent_platform"},)

    # id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    # key          text NOT NULL UNIQUE,
    # display_name text NOT NULL,
    # entra_app_role text,
    # gateway_path text,
    # created_at   timestamptz NOT NULL DEFAULT now()


class User(AgentPlatformBase, UpdatableBaseTable):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False)
    workos_id: Mapped[uuid.UUID | None]
    last_login_at: Mapped[dt | None] = mapped_column(DateTime(timezone=True))


class Domain(AgentPlatformBase, UpdatableBaseTable):
    __tablename__ = "domains"

    name: Mapped[str | None]
    code: Mapped[str] = mapped_column(nullable=False)


class DomainUser(AgentPlatformBase, UpdatableBaseTable):
    __tablename__ = "domain_users"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("domains.id"), nullable=False)

    user: Mapped["User"] = relationship()
    domain: Mapped["Domain"] = relationship()

    __table_args__: tuple[object, ...] = (
        UniqueConstraint("user_id", "domain_id"),
        *AgentPlatformBase.__table_args__,
    )
