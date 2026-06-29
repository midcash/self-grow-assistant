import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Quality(Base):
    __tablename__ = "qualities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(200), default="")
    icon = Column(String(20), default="star")
    target_level = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    levels = relationship("QualityLevel", back_populates="quality", cascade="all, delete-orphan")
    mappings = relationship("CategoryMapping", back_populates="quality", cascade="all, delete-orphan")
    progress_records = relationship("QualityProgress", back_populates="quality", cascade="all, delete-orphan")


class QualityLevel(Base):
    __tablename__ = "quality_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quality_id = Column(Integer, ForeignKey("qualities.id", ondelete="CASCADE"), nullable=False)
    level = Column(Integer, nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(200), default="")
    threshold_score = Column(Integer, nullable=False, default=0)

    quality = relationship("Quality", back_populates="levels")


class TodoItem(Base):
    __tablename__ = "todo_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    content = Column(String(200), nullable=False)
    category = Column(String(30), nullable=False, default="其他")
    duration_minutes = Column(Integer, default=0)
    actual_duration = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class QualityProgress(Base):
    __tablename__ = "quality_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quality_id = Column(Integer, ForeignKey("qualities.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    score = Column(Integer, default=0)
    total_score = Column(Integer, default=0)

    quality = relationship("Quality", back_populates="progress_records")


class CategoryMapping(Base):
    __tablename__ = "category_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quality_id = Column(Integer, ForeignKey("qualities.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False)
    score_per_duration = Column(Float, default=0.05)
    score_per_completion = Column(Integer, default=5)

    quality = relationship("Quality", back_populates="mappings")


class RoleModel(Base):
    __tablename__ = "role_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    field = Column(String(50), default="")
    avatar = Column(String(20), default="user")
    image_url = Column(String(500), default="")
    description = Column(String(300), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    qualities = relationship("RoleModelQuality", back_populates="role_model", cascade="all, delete-orphan")


class RoleModelQuality(Base):
    __tablename__ = "role_model_qualities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_model_id = Column(Integer, ForeignKey("role_models.id", ondelete="CASCADE"), nullable=False)
    quality_name = Column(String(50), nullable=False)
    description = Column(String(300), default="")
    suggested_activities = Column(Text, default="[]")

    role_model = relationship("RoleModel", back_populates="qualities")


class AgentTaskPriority(Base):
    """智能体任务优先级快照 — 每次评估后保存"""
    __tablename__ = "agent_task_priorities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    todo_id = Column(Integer, ForeignKey("todo_items.id", ondelete="CASCADE"), nullable=False)
    urgency_score = Column(Float, default=0.0)
    importance_score = Column(Float, default=0.0)
    algorithm_score = Column(Float, default=0.0)
    llm_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    llm_reasoning = Column(String(500), default="")
    suggested_action = Column(String(200), default="")
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow)


class AgentConversation(Base):
    """智能体对话历史"""
    __tablename__ = "agent_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)  # user / agent
    content = Column(Text, nullable=False)
    emotion_tag = Column(String(20), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AgentMemoryDigest(Base):
    """每日摘要 — 冷记忆层"""
    __tablename__ = "agent_memory_digests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    summary = Column(Text, default="")
    completed_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    top_priority_task = Column(String(200), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Goal(Base):
    """长期目标 — 秘书级自主智能体的核心"""
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    deadline = Column(Date, nullable=True)
    status = Column(String(20), default="active")
    target_metric = Column(String(200), default="")
    current_progress = Column(Float, default=0.0)
    importance = Column(Integer, default=5)
    pressure = Column(Float, default=0.0)
    reminder_count = Column(Integer, default=0)
    last_reminded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tasks = relationship("GoalTask", back_populates="goal", cascade="all, delete-orphan")


class GoalTask(Base):
    """目标分解出的子任务"""
    __tablename__ = "goal_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    content = Column(String(200), nullable=False)
    category = Column(String(30), default="其他")
    status = Column(String(20), default="pending")
    daily_quota = Column(Integer, default=0)
    today_progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    goal = relationship("Goal", back_populates="tasks")


class AgentTrace(Base):
    """Agent 编排 Trace — 每次编排的完整调用链路"""
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orchestration_id = Column(String(36), nullable=False, index=True)
    span_type = Column(String(20), nullable=False)
    agent_name = Column(String(30), nullable=False, default="orchestrator")
    parent_span_id = Column(Integer, nullable=True)
    objective = Column(String(200), default="")
    input_summary = Column(String(500), default="")
    output_summary = Column(String(500), default="")
    latency_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(String(300), default="")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AgentMetrics(Base):
    """Agent 每日指标聚合"""
    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    agent_name = Column(String(30), nullable=False)
    total_calls = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    avg_latency_ms = Column(Integer, default=0)
    p50_latency_ms = Column(Integer, default=0)
    p95_latency_ms = Column(Integer, default=0)
    total_token_estimate = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
