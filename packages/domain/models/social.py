from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, Index, SQLModel

from packages.domain.models.base import TimestampMixin


class ConnectionStatus(StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    blocked = "blocked"


class UserConnection(TimestampMixin, SQLModel, table=True):
    __tablename__ = "user_connections"

    requester_user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_user_connections_requester_user_id_users"),
            primary_key=True,
            nullable=False,
        ),
    )
    addressee_user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_user_connections_addressee_user_id_users"),
            primary_key=True,
            nullable=False,
        ),
    )
    status: ConnectionStatus = Field(
        default=ConnectionStatus.pending,
        sa_column=Column(
            postgresql.ENUM(ConnectionStatus, name="connection_status", create_type=False),
            nullable=False,
            server_default=ConnectionStatus.pending.value,
        ),
    )

    __table_args__ = (
        CheckConstraint(
            "requester_user_id <> addressee_user_id",
            name="ck_user_connections_no_self_connection",
        ),
        Index("ix_user_connections_requester_user_id", "requester_user_id"),
        Index("ix_user_connections_addressee_user_id", "addressee_user_id"),
        Index("ix_user_connections_status", "status"),
        Index("ix_user_connections_requester_user_id_status", "requester_user_id", "status"),
        Index("ix_user_connections_addressee_user_id_status", "addressee_user_id", "status"),
    )


class OrganizerFollower(TimestampMixin, SQLModel, table=True):
    __tablename__ = "organizer_followers"

    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", name="fk_organizer_followers_user_id_users"),
            primary_key=True,
            nullable=False,
        ),
    )
    organizer_id: UUID = Field(
        sa_column=Column(
            ForeignKey("organizers.id", name="fk_organizer_followers_organizer_id_organizers"),
            primary_key=True,
            nullable=False,
        ),
    )

    __table_args__ = (
        Index("ix_organizer_followers_user_id", "user_id"),
        Index("ix_organizer_followers_organizer_id", "organizer_id"),
    )
