"""SQLAlchemy models.

Importing this package registers every table on ``Base.metadata``, which is what
Alembic autogenerate and ``create_all`` both rely on.
"""

from app.models.base import Base
from app.models.drill import AssignmentDrill, Drill, WeeklyAssignment
from app.models.enums import (
    Difficulty,
    DominantFoot,
    DrillCategory,
    LeaderboardScope,
    LeaderboardWindow,
    MetricType,
    PointsReason,
    RosterStatus,
    SubmissionSource,
    SubmissionStatus,
    UserRole,
)
from app.models.progress import PointsLedger, StudentStreak, WeekResult
from app.models.submission import Submission
from app.models.user import CoachProfile, StudentProfile, User

__all__ = [
    "Base",
    "User",
    "CoachProfile",
    "StudentProfile",
    "Drill",
    "WeeklyAssignment",
    "AssignmentDrill",
    "Submission",
    "PointsLedger",
    "WeekResult",
    "StudentStreak",
    "UserRole",
    "RosterStatus",
    "DominantFoot",
    "DrillCategory",
    "MetricType",
    "Difficulty",
    "SubmissionStatus",
    "SubmissionSource",
    "PointsReason",
    "LeaderboardScope",
    "LeaderboardWindow",
]
