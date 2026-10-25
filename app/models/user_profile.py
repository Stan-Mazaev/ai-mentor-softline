from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class UserProfile(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    # Анонимный идентификатор (например, UUID, сгенерированный на клиенте).
    # Никаких имён, телефонов, email — принцип минимизации ПДн.
    anonymous_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)