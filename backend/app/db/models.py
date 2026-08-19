from __future__ import annotations  # enables X | Y union syntax on Python 3.9

"""
app/db/models.py
────────────────
SQLAlchemy ORM models for Nerve's three core tables.

TABLES:
  ┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
  │    events    │────►│   pull_requests  │     │   agent_logs    │
  │              │  1:1│                  │ 1:N │                 │
  │ Every crash  │     │ The PR the agent │◄────│ Every step the  │
  │ we receive   │     │ opens to fix it  │     │ agent took      │
  └──────────────┘     └──────────────────┘     └─────────────────┘

WHY THIS SCHEMA?
  - `events` is the master record. Everything hangs off it.
  - `pull_requests` is 1:1 with event (one crash → one PR).
  - `agent_logs` is 1:N (one crash → many agent steps logged).
  - Using UUID PKs instead of serial ints so IDs are safe to expose in URLs
    and webhooks without leaking sequence info.

RELATIONSHIPS:
  - Event.pull_request  → the PR created for this event (optional, may not exist yet)
  - Event.agent_logs    → all agent steps for this event
  - PullRequest.event   → back-reference to the triggering event
  - AgentLog.event      → back-reference to the triggering event
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ── Enums ─────────────────────────────────────────────────────────────────────
# Using Python enums keeps the valid values in one place.
# SQLAlchemy maps these to Postgres ENUM types.

class EventStatus(str, enum.Enum):
    """Lifecycle of a crash event."""
    PENDING    = "PENDING"     # received, not yet picked up by worker
    PROCESSING = "PROCESSING"  # ARQ worker is running the agent
    COMPLETED  = "COMPLETED"   # agent finished, PR opened
    FAILED     = "FAILED"      # agent exhausted retries or hit a hard error
    ESCALATED  = "ESCALATED"   # exceeded retry limit, flagged for human review


class PRStatus(str, enum.Enum):
    """State of the pull request the agent created."""
    OPEN    = "OPEN"
    MERGED  = "MERGED"
    CLOSED  = "CLOSED"   # dismissed by the human reviewer


class AgentNode(str, enum.Enum):
    """Maps to a node in the LangGraph state machine (Phase 4)."""
    INVESTIGATE  = "investigate"
    HYPOTHESIZE  = "hypothesize"
    PATCH        = "patch"
    TEST         = "test"
    VALIDATE     = "validate"
    SUBMIT       = "submit"
    REFLECT      = "reflect"    # retry reflection loop


# ── Helper ─────────────────────────────────────────────────────────────────────
def _now() -> datetime:
    """UTC-aware datetime. Always store UTC, display in local time on the frontend."""
    return datetime.now(timezone.utc)


# ── Model: events ──────────────────────────────────────────────────────────────
class Event(Base):
    """
    One row = one production crash we received via webhook.

    The `metadata_` column stores arbitrary JSON from the source system
    (Sentry, Datadog, custom) so we don't need to alter the schema every
    time a new field comes in.
    """
    __tablename__ = "events"

    # Primary key — UUID so it's safe in URLs
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Where the error came from (e.g. "sentry", "datadog", "custom")
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    # Python exception type (e.g. "ZeroDivisionError", "KeyError")
    error_type: Mapped[str] = mapped_column(String(255), nullable=False)

    # The human-readable error message
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Full stack trace as raw text
    stack_trace: Mapped[str] = mapped_column(Text, nullable=False)

    # "org/repo" format — which GitHub repo to clone and fix
    repository: Mapped[str] = mapped_column(String(255), nullable=False)

    # "production", "staging", etc.
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="production")

    # Lifecycle status
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"),
        nullable=False,
        default=EventStatus.PENDING,
    )

    # Extra fields from the webhook source (arbitrary JSON)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    # uselist=False → one-to-one (an event has at most one PR)
    pull_request: Mapped["PullRequest | None"] = relationship(
        "PullRequest", back_populates="event", uselist=False
    )
    # one-to-many (an event has many agent log entries)
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        "AgentLog", back_populates="event", order_by="AgentLog.created_at"
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id} source={self.source} status={self.status}>"


# ── Model: pull_requests ───────────────────────────────────────────────────────
class PullRequest(Base):
    """
    The GitHub PR that the agent opens once it has a working fix.

    One-to-one with Event: one crash → one PR attempt.
    If the agent fails, this row may never be created.
    """
    __tablename__ = "pull_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign key back to the event that triggered this PR
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # enforces the 1:1 relationship at the DB level
    )

    # GitHub PR number (e.g. 847 in "org/repo/pull/847")
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Full GitHub PR URL
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Branch name the agent created (e.g. "nerve/fix-evt_abc123")
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # The patch the agent wrote (unified diff format)
    patch_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How many agent retry iterations it took
    iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # PR lifecycle
    status: Mapped[PRStatus] = mapped_column(
        Enum(PRStatus, name="pr_status"),
        nullable=False,
        default=PRStatus.OPEN,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # ── Relationship ───────────────────────────────────────────────────────────
    event: Mapped["Event"] = relationship("Event", back_populates="pull_request")

    def __repr__(self) -> str:
        return f"<PullRequest id={self.id} pr_number={self.pr_number} status={self.status}>"


# ── Model: agent_logs ─────────────────────────────────────────────────────────
class AgentLog(Base):
    """
    Append-only audit trail of every step the agent took.

    One row = one agent action (one LangGraph node execution).
    These rows are what power the live agent trace viewer in the dashboard.

    Never update or delete rows in this table — it's an audit log.
    """
    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Which event this log entry belongs to
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Which node in the LangGraph state machine ran
    node: Mapped[AgentNode] = mapped_column(
        Enum(AgentNode, name="agent_node"),
        nullable=False,
    )

    # Human-readable message the agent "thought" (shown in trace viewer)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Arbitrary JSON payload — node-specific data (e.g. the patch content,
    # test results, vector search results, LLM token usage)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Which retry iteration this log belongs to (0-indexed)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # When this step happened
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # ── Relationship ───────────────────────────────────────────────────────────
    event: Mapped["Event"] = relationship("Event", back_populates="agent_logs")

    def __repr__(self) -> str:
        return f"<AgentLog id={self.id} node={self.node} event_id={self.event_id}>"
