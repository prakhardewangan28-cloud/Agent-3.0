"""Pydantic models and schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., json_schema_extra={"example": "ok"})
    mock_mode: Optional[bool] = None
    version: Optional[str] = None


class SearchQuery(BaseModel):
    """Search query request model."""
    query: str = Field(..., min_length=1, max_length=500, json_schema_extra={"example": "What is climate change?"})
    max_results: Optional[int] = Field(None, ge=1, le=50, json_schema_extra={"example": 10})


class ResearchStartRequest(BaseModel):
    """Request to start research."""
    query: str = Field(..., min_length=1, max_length=500)
    language: str = Field("en", pattern="^(en|hi|es|fr|de|pt|zh|ja|ar)$")


class ResearchStartResponse(BaseModel):
    """Response from starting research."""
    session_id: str
    needs_refinement: bool
    options: List[Dict[str, Any]] = []
    status: str


class RefineRequest(BaseModel):
    """Request to refine a query."""
    session_id: str
    chosen_direction: str = Field(..., min_length=1)


class RefineResponse(BaseModel):
    """Response from refining a query."""
    session_id: str
    status: str


class SessionListItem(BaseModel):
    """Session list item."""
    id: str
    original_query: str
    status: str
    created_at: str


class ClaimResponse(BaseModel):
    """Individual claim response."""
    claim: str
    confidence: float
    sources: List[str]


class ResearchResponse(BaseModel):
    """Research result response model."""
    query: str
    claims: List[ClaimResponse]
    timestamp: datetime = Field(default_factory=datetime.utcnow)



class CounterArgumentSource(BaseModel):
    """Counter-argument supporting source."""
    source_id: int
    url: str
    domain: str
    credibility_score: float
    reason: str


class CounterArgument(BaseModel):
    """Counter-argument to the research report."""
    counter_argument: str
    supporting_sources: List[CounterArgumentSource]
    strength: str  # "strong" | "moderate" | "weak" | "none"
    explanation: str


class ResearchSessionResponse(BaseModel):
    """Complete research session response."""
    session_id: str
    status: str
    original_query: str
    refined_query: Optional[str] = None
    sources: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    landscape: Dict[str, Any]
    final_report: Optional[str] = None
    counter_argument: Optional[CounterArgument] = None
    node_timings: Dict[str, float] = {}
    error: Optional[str] = None
