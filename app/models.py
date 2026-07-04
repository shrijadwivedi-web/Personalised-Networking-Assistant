"""
Pydantic models that define the data contracts between the frontend and
backend. Using BaseModel gives us automatic request validation (FastAPI
returns a 422 with a clear error message if a field is missing or has the
wrong type) and automatic documentation in the Swagger UI.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class EventAnalysisRequest(BaseModel):
    """Input for the /analyze-event endpoint."""
    description: str = Field(..., description="Description of the networking event")
    candidate_labels: Optional[List[str]] = Field(
        default=None,
        description="Optional custom list of themes to classify against. "
                     "If omitted, a default set of networking-relevant themes is used.",
    )


class EventAnalysisResponse(BaseModel):
    themes: List[str]


class FactCheckRequest(BaseModel):
    """Input for the /fact-check endpoint."""
    query: str = Field(..., description="Topic or phrase to fact-check via Wikipedia")


class FactCheckResponse(BaseModel):
    query: str
    summary: str


class ConversationRequest(BaseModel):
    """Input for the /generate-conversation endpoint."""
    description: str = Field(..., description="Description of the networking event")
    interests: List[str] = Field(..., description="List of the user's interests")
    tone: str = Field(
        default="casual",
        description="Desired tone for generated starters: 'formal', 'casual', or 'witty'",
    )


class ConversationResponse(BaseModel):
    themes: List[str]
    suggestions: List[str]
    confidence_scores: List[int] = Field(
        ...,
        description="Parallel list to suggestions: a 1-5 icebreaker confidence "
                    "score for each generated starter (see app/services/scorer.py)",
    )
    confidence_explanations: List[str] = Field(
        ...,
        description="Parallel list to suggestions: a short human-readable reason "
                     "for each suggestion's confidence score",
    )


class FeedbackRequest(BaseModel):
    """Input for the /feedback endpoint."""
    suggestion: str = Field(..., description="The exact suggestion text being rated")
    action: str = Field(..., description="Either 'like' or 'dislike'")


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Profile schemas
# ---------------------------------------------------------------------------

class ProfileUpdateRequest(BaseModel):
    """Input for PUT /profile. All fields optional so a user can fill these
    in incrementally rather than all at once."""
    role: Optional[str] = Field(default=None, max_length=120, description="e.g. 'Backend developer'")
    industry: Optional[str] = Field(default=None, max_length=120, description="e.g. 'Fintech'")
    networking_goal: Optional[str] = Field(
        default=None,
        description="e.g. 'Looking to meet potential co-founders and early hires'",
    )


class ProfileResponse(BaseModel):
    role: Optional[str] = None
    industry: Optional[str] = None
    networking_goal: Optional[str] = None


# ---------------------------------------------------------------------------
# History schemas
# ---------------------------------------------------------------------------

class HistoryEntryResponse(BaseModel):
    id: int
    description: str
    interests: List[str]
    themes: List[str]
    suggestions: List[str]
    tone: Optional[str] = None
    confidence_scores: List[int] = []
    created_at: str
