from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, Float,
    ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DatasetFormat(str, enum.Enum):
    JSONL = "jsonl"
    CSV = "csv"
    JSON = "json"
    TXT = "txt"
    ZIP = "zip"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    model_configs: Mapped[list["ModelConfig"]] = relationship(back_populates="user")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="user")
    evaluation_tasks: Mapped[list["EvaluationTask"]] = relationship(back_populates="user")
    reports: Mapped[list["Report"]] = relationship(back_populates="user")


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai, anthropic, custom
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    base_url: Mapped[Optional[str]] = mapped_column(String(500))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="model_configs")
    elo_score: Mapped[Optional["ModelEloScore"]] = relationship(
        back_populates="model_config",
        foreign_keys="ModelEloScore.model_config_id"
    )


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # qa, code, chat, rag, etc.
    format: Mapped[str] = mapped_column(String(20), default="jsonl")
    size: Mapped[int] = mapped_column(Integer, default=0)  # number of records
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    schema_meta: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="datasets")


class TaskModelAssociation(Base):
    """Many-to-many association between evaluation tasks and model configs."""
    __tablename__ = "task_model_association"

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_configs.id", ondelete="RESTRICT"),
        primary_key=True,
    )


class EvaluationTask(Base):
    __tablename__ = "evaluation_tasks"
    __table_args__ = (
        Index("ix_eval_tasks_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDING, index=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100))
    model_ids: Mapped[list] = mapped_column(JSON, default=list)
    dataset_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("datasets.id"))
    evaluator_config: Mapped[dict] = mapped_column(JSON, default=dict)
    results_summary: Mapped[Optional[dict]] = mapped_column(JSON)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total_samples: Mapped[int] = mapped_column(Integer, default=0)
    processed_samples: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    checkpoint_data: Mapped[Optional[dict]] = mapped_column(JSON)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="evaluation_tasks")
    results: Mapped[list["EvaluationResult"]] = relationship(back_populates="task")
    reports: Mapped[list["Report"]] = relationship(back_populates="task")
    models: Mapped[list["ModelConfig"]] = relationship(
        secondary="task_model_association", viewonly=True
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        Index("ix_eval_results_task_model", "task_id", "model_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_tasks.id"), nullable=False, index=True)
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_configs.id"), nullable=False, index=True)
    input_text: Mapped[Optional[str]] = mapped_column(Text)
    output_text: Mapped[Optional[str]] = mapped_column(Text)
    reference_text: Mapped[Optional[str]] = mapped_column(Text)
    scores: Mapped[dict] = mapped_column(JSON, default=dict)
    result_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped["EvaluationTask"] = relationship(back_populates="results")


class ModelEloScore(Base):
    __tablename__ = "model_elo_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_configs.id"), unique=True, nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    elo_score: Mapped[float] = mapped_column(Float, default=1000.0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    total_matches: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    model_config: Mapped["ModelConfig"] = relationship(back_populates="elo_score")


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship()
    messages: Mapped[list["AgentMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="AgentMessage.created_at"
    )


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, tool
    content: Mapped[Optional[str]] = mapped_column(Text)
    tool_calls: Mapped[Optional[list]] = mapped_column(JSON)  # [{id, name, arguments}]
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(100))
    tool_name: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped["AgentConversation"] = relationship(back_populates="messages")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # ["var1", "var2"]
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("prompt_templates.id"))
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    prompt_type: Mapped[str] = mapped_column(String(20), default="generation")  # generation | evaluation
    domain: Mapped[Optional[str]] = mapped_column(String(50))  # medical, finance, industrial, legal, education, general
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class GeneratedTrainingData(Base):
    __tablename__ = "generated_training_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_tasks.id"), nullable=False, index=True)
    result_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_results.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_input: Mapped[Optional[str]] = mapped_column(Text)
    original_output: Mapped[Optional[str]] = mapped_column(Text)
    corrected_output: Mapped[Optional[str]] = mapped_column(Text)
    diagnosis: Mapped[Optional[dict]] = mapped_column(JSON)
    improvement_notes: Mapped[Optional[str]] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PromptExperiment(Base):
    __tablename__ = "prompt_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    template_ids: Mapped[list] = mapped_column(JSON, default=list)  # [1, 2, 3]
    model_ids: Mapped[list] = mapped_column(JSON, default=list)
    test_inputs: Mapped[list] = mapped_column(JSON, default=list)  # [{"var1": "val1"}, ...]
    results: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ArenaMatch(Base):
    __tablename__ = "arena_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_configs.id"), nullable=False)
    model_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("model_configs.id"), nullable=False)
    output_a: Mapped[Optional[str]] = mapped_column(Text)
    output_b: Mapped[Optional[str]] = mapped_column(Text)
    winner: Mapped[Optional[str]] = mapped_column(String(10))  # "a", "b", "tie", None
    latency_a_ms: Mapped[Optional[float]] = mapped_column(Float)
    latency_b_ms: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    data: Mapped[Optional[dict]] = mapped_column(JSON)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AgentMemory(Base):
    __tablename__ = "agent_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)  # preference, context, insight
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_tasks.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(10), default="pdf")
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped["EvaluationTask"] = relationship(back_populates="reports")
    user: Mapped["User"] = relationship(back_populates="reports")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["User"] = relationship()
    members: Mapped[list["OrganizationMember"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    shared_resources: Mapped[list["ResourceShare"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")  # admin, member, viewer
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class ResourceShare(Base):
    __tablename__ = "resource_shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # evaluation, dataset, model
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    shared_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="shared_resources")
    user: Mapped["User"] = relationship()


class JudgeModelConfig(Base):
    """Dedicated judge model configuration, independent from user's general models."""
    __tablename__ = "judge_model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    base_url: Mapped[Optional[str]] = mapped_column(String(500))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship()


class AgentModelConfig(Base):
    """Configuration for the AI assistant's LLM backend."""
    __tablename__ = "agent_model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    base_url: Mapped[Optional[str]] = mapped_column(String(500))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    params: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship()


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # first 8 chars for display
    key_hash: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)  # ["read", "write", "evaluate"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvaluationTemplate(Base):
    __tablename__ = "evaluation_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    model_ids: Mapped[list] = mapped_column(JSON, default=list)
    dataset_id: Mapped[Optional[int]] = mapped_column(Integer)
    evaluator_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
