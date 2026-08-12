from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from src.models.orm import User, Domain, DomainUser


def getUserByID(session: Session, email: str) -> UUID | None:
    return session.scalar(select(User.id).where(User.email == email, User.is_active.is_(True)))
