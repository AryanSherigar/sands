"""Result shapes of one evaluation run; serialised to eval/reports/<run_id>.json."""

from pydantic import BaseModel, Field

from eval.prices import RunUsage


class IntervalOut(BaseModel):
    mean: float
    low: float
    high: float
    count: int


class ProbeRecord(BaseModel):
    probe_id: str
    failure_class: str
    arm: str
    required_total: int
    required_found: int
    forbidden_count: int
    stale_span_count: int = 0
    distractor_count: int = 0
    style: str = "direct"
    irrelevant_token_share: float
    recalled_tokens: int = 0
    hit_at: dict[int, float] = Field(default_factory=dict)
    reciprocal_rank: float = 0.0
    ndcg: float = 0.0
    branch_hits: dict[str, int] = Field(default_factory=dict)
    graph_only_found: int = 0
    retrieve_ms: float | None = None
    degraded_reasons: list[str] = Field(default_factory=list)
    skipped_branches: list[str] = Field(default_factory=list)


class TypeScoreOut(BaseModel):
    recall: IntervalOut | None
    precision: IntervalOut | None
    recall_hits: int
    label_count: int
    predicted_count: int
    wrong_status: int


class ExtractionRecord(BaseModel):
    campaign_id: str
    by_type: dict[str, TypeScoreOut]
    forbidden_extracted: int
    duplicate_entity_rate: float
    new_entity_count: int
    negated_fact_count: int = 0


class LatencyRecord(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float
    count: int
    skipped_branch_count: int


class RunReport(BaseModel):
    run_id: str
    corpus_version: str
    content_hashes: dict[str, str]
    pinned: dict[str, str]
    is_complete: bool
    probes: list[ProbeRecord] = Field(default_factory=list)
    extraction: list[ExtractionRecord] = Field(default_factory=list)
    latency: LatencyRecord | None = None
    usage: RunUsage | None = None
    unmeasured_classes: list[str] = Field(default_factory=list)
    label_audit: dict[str, int] = Field(default_factory=dict)
    stage_ms: dict[str, float] = Field(default_factory=dict)
    extraction_stage_ms: dict[str, float] = Field(default_factory=dict)
    cost_usd: float | None = None
    turn_count: int = 0
    env_overrides: dict[str, str] = Field(default_factory=dict)
