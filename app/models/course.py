"""LEDA Course definitions and scoring session models.

Course data is based on the LEDA_CallScript.pdf NIST Standard Test Methods.
Each course level has maneuvers, each maneuver has a sequence of expected
bucket images the pilot must capture in order.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json
import os
import uuid


@dataclass
class ManeuverStep:
    """A single step in a maneuver sequence."""
    step_number: int
    instruction: str
    expected_bucket: str  # e.g., "1", "2A", "3B", "L" (landing pad)
    captures_image: bool = True  # False for movement-only steps like "LAND"


@dataclass
class Maneuver:
    """A maneuver (lane) within a course level."""
    id: str
    name: str
    short_name: str  # e.g., "MAN 1", "MAN 2"
    steps: list[ManeuverStep] = field(default_factory=list)

    @property
    def image_count(self) -> int:
        return sum(1 for s in self.steps if s.captures_image)

    @property
    def expected_buckets(self) -> list[str]:
        return [s.expected_bucket for s in self.steps if s.captures_image]


@dataclass
class Course:
    """A complete LEDA proficiency course level."""
    id: str
    name: str
    level: int
    description: str
    time_limit_minutes: int
    lane_spacing_options: list[str]  # e.g., ["10 FT", "20 FT", "30 FT"]
    maneuvers: list[Maneuver] = field(default_factory=list)

    @property
    def total_images(self) -> int:
        return sum(m.image_count for m in self.maneuvers)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScoringSession:
    """A scoring session for a pilot's check-ride attempt."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str = ""
    pilot_last_name: str = ""
    pilot_first_name: str = ""
    pilot_organization: str = ""
    drone_make: str = ""
    drone_model: str = ""
    facility_location: str = ""
    proctor_name: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    lane_spacing: str = "5 FT"
    lighting: str = "Daylight"
    wind_average_mph: str = ""
    wind_gusts_mph: str = ""
    pilot_view: str = "Line of Sight"
    # Image results: list of {image_index, maneuver_id, expected_bucket, filename, analysis, score}
    image_results: list[dict] = field(default_factory=list)
    # Tracks OCR-detected bucket IDs in submission order for duplicate/out-of-order detection
    seen_bucket_ids: list[str] = field(default_factory=list)
    elapsed_times: dict = field(default_factory=dict)  # maneuver_id -> MM:SS
    status: str = "pending"  # pending, in_progress, completed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# LEDA Level 1 Course Definition
# ---------------------------------------------------------------------------

def _build_level1() -> Course:
    """Build Level 1 course: Position + Traverse, 7-minute time limit."""

    # MAN 1 - Position Lane
    man1_steps = [
        ManeuverStep(1, "Launch and hover over stand #1, align with bucket", "1"),
        ManeuverStep(2, "Gimbal up, capture image of bucket 2A", "2A"),
        ManeuverStep(3, "Yaw left 360° over stand #1, align with bucket", "1"),
        ManeuverStep(4, "Gimbal up, capture image of bucket 2A", "2A"),
        ManeuverStep(5, "Yaw right 360° over stand #1, align with bucket", "1"),
        ManeuverStep(6, "Gimbal up, capture image of bucket 2A", "2A"),
        ManeuverStep(7, "Climb vertically over stand #1, align with bucket", "1"),
        ManeuverStep(8, "Gimbal up, capture image of bucket 3A", "3A"),
        ManeuverStep(9, "Descend vertically over stand #1, align with bucket", "1"),
        ManeuverStep(10, "Gimbal up, capture image of bucket 2A", "2A"),
        ManeuverStep(11, "Pitch forward over stand #2, align with bucket", "2"),
        ManeuverStep(12, "Gimbal up, capture image of bucket 3A", "3A"),
        ManeuverStep(13, "Pitch backward over stand #1, align with bucket", "1"),
        ManeuverStep(14, "Gimbal up, capture image of bucket 2A", "2A"),
        ManeuverStep(15, "Pitch forward over stand #2, yaw left 180° (upside-down bucket)", "2"),
        ManeuverStep(16, "Gimbal up, capture image of bucket 1C", "1C"),
        ManeuverStep(17, "Pitch forward over landing pad, yaw right 180°", "L"),
        ManeuverStep(18, "Gimbal up, capture image of bucket 1A", "1A"),
        ManeuverStep(19, "Land in circle", "0", captures_image=False),
    ]

    man1 = Maneuver(
        id="level1_man1",
        name="Position",
        short_name="MAN 1",
        steps=man1_steps,
    )

    # MAN 2 - Traverse Lane
    man2_steps = [
        ManeuverStep(1, "Hover over launch platform, align with bucket 1A", "1A"),
        ManeuverStep(2, "Orbit left 90° around stand #1, align with bucket 1B", "1B"),
        ManeuverStep(3, "Roll leftward to stand #2, align with bucket 2B", "2B"),
        ManeuverStep(4, "Roll leftward to stand #3, align with bucket 3B", "3B"),
        ManeuverStep(5, "Orbit left 90° around stand #3, align with bucket 3C", "3C"),
        ManeuverStep(6, "Orbit left 90° around stand #3, align with bucket 3D", "3D"),
        ManeuverStep(7, "Roll leftward to stand #2, align with bucket 2D", "2D"),
        ManeuverStep(8, "Roll leftward to stand #1, align with bucket 1D", "1D"),
        ManeuverStep(9, "Orbit left 90° around stand #1, align with bucket 1A", "1A"),
        ManeuverStep(10, "Land in circle", "0", captures_image=False),
        ManeuverStep(11, "Launch, hover over launch platform, align with bucket 1A", "1A"),
        ManeuverStep(12, "Orbit right 90° around stand #1, align with bucket 1D", "1D"),
        ManeuverStep(13, "Roll rightward to stand #2, align with bucket 2D", "2D"),
        ManeuverStep(14, "Roll rightward to stand #3, align with bucket 3D", "3D"),
        ManeuverStep(15, "Orbit right 90° around stand #3, align with bucket 3C", "3C"),
        ManeuverStep(16, "Orbit right 90° around stand #3, align with bucket 3B", "3B"),
        ManeuverStep(17, "Roll rightward to stand #2, align with bucket 2B", "2B"),
        ManeuverStep(18, "Roll rightward to stand #1, align with bucket 1B", "1B"),
        ManeuverStep(19, "Orbit right 90° around stand #1, align with bucket 1A", "1A"),
        ManeuverStep(20, "Land in circle", "0", captures_image=False),
    ]

    man2 = Maneuver(
        id="level1_man2",
        name="Traverse",
        short_name="MAN 2",
        steps=man2_steps,
    )

    return Course(
        id="level1",
        name="LEDA Level 1 Proficiency",
        level=1,
        description="Level 1 proficiency check-ride: Position and Traverse maneuvers. "
                    "2 maneuvers, 7-minute time limit per maneuver.",
        time_limit_minutes=7,
        lane_spacing_options=["10 FT", "20 FT", "30 FT"],
        maneuvers=[man1, man2],
    )


# ---------------------------------------------------------------------------
# LEDA Level 2 Course Definition
# ---------------------------------------------------------------------------

def _build_level2() -> Course:
    """Build Level 2 course: all 5 maneuvers, timed per maneuver."""

    level1 = _build_level1()
    # Reuse Position and Traverse from Level 1 with updated IDs
    man1 = Maneuver(
        id="level2_man1",
        name="Position",
        short_name="MAN 1",
        steps=[ManeuverStep(s.step_number, s.instruction, s.expected_bucket, s.captures_image)
               for s in level1.maneuvers[0].steps],
    )
    man2 = Maneuver(
        id="level2_man2",
        name="Traverse",
        short_name="MAN 2",
        steps=[ManeuverStep(s.step_number, s.instruction, s.expected_bucket, s.captures_image)
               for s in level1.maneuvers[1].steps],
    )

    # MAN 3 - Orbit Lane
    man3_steps = [
        ManeuverStep(1, "Launch to 2S over stand #1, take picture of bucket 1", "1"),
        ManeuverStep(2, "Gimbal up, capture image of bucket 3A", "3A"),
        ManeuverStep(3, "Orbit left 90°, capture image of bucket 3B", "3B"),
        ManeuverStep(4, "Orbit left 90°, capture image of bucket 3C", "3C"),
        ManeuverStep(5, "Orbit left 90°, capture image of bucket 3D", "3D"),
        ManeuverStep(6, "Orbit left 90°, gimbal down, capture image of bucket 1", "1"),
        ManeuverStep(7, "Gimbal up, capture image of bucket 3A", "3A"),
        ManeuverStep(8, "Orbit right 90°, capture image of bucket 3D", "3D"),
        ManeuverStep(9, "Orbit right 90°, capture image of bucket 3C", "3C"),
        ManeuverStep(10, "Orbit right 90°, capture image of bucket 3B", "3B"),
        ManeuverStep(11, "Orbit right, descend to S over stand #2, capture image of bucket 2", "2"),
        ManeuverStep(12, "Gimbal up, capture image of bucket 3A", "3A"),
        ManeuverStep(13, "Orbit left 90°, capture image of bucket 3B", "3B"),
        ManeuverStep(14, "Orbit left 90°, capture image of bucket 3C", "3C"),
        ManeuverStep(15, "Orbit left 90°, capture image of bucket 3D", "3D"),
        ManeuverStep(16, "Orbit left 90°, gimbal down, capture image of bucket 2", "2"),
        ManeuverStep(17, "Gimbal up, capture image of bucket 3A", "3A"),
        ManeuverStep(18, "Orbit right 90°, capture image of bucket 3D", "3D"),
        ManeuverStep(19, "Orbit right 90°, capture image of bucket 3C", "3C"),
        ManeuverStep(20, "Orbit right 90°, capture image of bucket 3B", "3B"),
        ManeuverStep(21, "Land", "0", captures_image=False),
    ]

    man3 = Maneuver(
        id="level2_man3",
        name="Orbit",
        short_name="MAN 3",
        steps=man3_steps,
    )

    # MAN 4 - Inspect Lane
    man4_steps = [
        ManeuverStep(1, "Launch to 1/2S over stand #1, capture image of bucket 1", "1"),
        ManeuverStep(2, "Pitch backward, capture image of bucket 1A", "1A"),
        ManeuverStep(3, "Orbit left 90°, capture image of bucket 1B", "1B"),
        ManeuverStep(4, "Orbit left 90°, capture image of bucket 1C", "1C"),
        ManeuverStep(5, "Orbit left 90°, capture image of bucket 1D", "1D"),
        ManeuverStep(6, "Fly over stand #2, capture image of bucket 2", "2"),
        ManeuverStep(7, "Pitch backward, capture image of bucket 2A", "2A"),
        ManeuverStep(8, "Orbit right 90°, capture image of bucket 2D", "2D"),
        ManeuverStep(9, "Orbit right 90°, capture image of bucket 2C", "2C"),
        ManeuverStep(10, "Orbit right 90°, capture image of bucket 2B", "2B"),
        ManeuverStep(11, "Fly over stand #3, capture image of bucket 3", "3"),
        ManeuverStep(12, "Pitch backward, capture image of bucket 3A", "3A"),
        ManeuverStep(13, "Orbit left 90°, capture image of bucket 3B", "3B"),
        ManeuverStep(14, "Orbit left 90°, capture image of bucket 3C", "3C"),
        ManeuverStep(15, "Orbit left 90°, capture image of bucket 3D", "3D"),
        ManeuverStep(16, "Fly over stand #4, capture image of bucket 4", "4"),
        ManeuverStep(17, "Pitch backward, capture image of bucket 4A", "4A"),
        ManeuverStep(18, "Orbit right 90°, capture image of bucket 4D", "4D"),
        ManeuverStep(19, "Orbit right 90°, capture image of bucket 4C", "4C"),
        ManeuverStep(20, "Orbit right 90°, capture image of bucket 4B", "4B"),
        ManeuverStep(21, "Land", "0", captures_image=False),
    ]

    man4 = Maneuver(
        id="level2_man4",
        name="Inspect",
        short_name="MAN 4",
        steps=man4_steps,
    )

    # MAN 5 - Recon Lane (5 laps)
    man5_steps = []
    step_num = 1
    for lap in range(1, 6):
        man5_steps.extend([
            ManeuverStep(step_num, f"Lap {lap}: Pitch forward over stand #4, capture image of bucket 4", "4"),
            ManeuverStep(step_num + 1, f"Lap {lap}: Yaw left 180°, capture upside-down bucket 4", "4"),
            ManeuverStep(step_num + 2, f"Lap {lap}: Pitch forward over landing pad, yaw right 180°, capture landing pad", "L"),
            ManeuverStep(step_num + 3, f"Lap {lap}: Gimbal up, capture image of bucket 1A", "1A"),
        ])
        step_num += 4
    man5_steps.append(ManeuverStep(step_num, "Land", "0", captures_image=False))

    man5 = Maneuver(
        id="level2_man5",
        name="Recon",
        short_name="MAN 5",
        steps=man5_steps,
    )

    return Course(
        id="level2",
        name="LEDA Level 2 Proficiency Check-Ride",
        level=2,
        description="Level 2 proficiency check-ride: all 5 maneuvers (Position, Traverse, "
                    "Orbit, Inspect, Recon). Timed per maneuver.",
        time_limit_minutes=7,
        lane_spacing_options=["10 FT", "20 FT", "30 FT"],
        maneuvers=[man1, man2, man3, man4, man5],
    )


# ---------------------------------------------------------------------------
# Course registry
# ---------------------------------------------------------------------------

_COURSES: dict[str, Course] = {}


def _init_courses():
    if not _COURSES:
        for course in [_build_level1(), _build_level2()]:
            _COURSES[course.id] = course


def get_all_courses() -> list[Course]:
    _init_courses()
    return list(_COURSES.values())


def get_course(course_id: str) -> Optional[Course]:
    _init_courses()
    return _COURSES.get(course_id)


# ---------------------------------------------------------------------------
# Session persistence (JSON file-based for now)
# ---------------------------------------------------------------------------

def _sessions_file() -> str:
    from flask import current_app
    return os.path.join(current_app.config["COURSE_DATA_DIR"], "sessions.json")


def _load_sessions() -> dict[str, dict]:
    path = _sessions_file()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_sessions(sessions: dict[str, dict]):
    path = _sessions_file()
    with open(path, "w") as f:
        json.dump(sessions, f, indent=2)


def create_session(session: ScoringSession) -> ScoringSession:
    sessions = _load_sessions()
    sessions[session.id] = session.to_dict()
    _save_sessions(sessions)
    return session


def get_session(session_id: str) -> Optional[ScoringSession]:
    sessions = _load_sessions()
    data = sessions.get(session_id)
    if data:
        return ScoringSession(**{k: v for k, v in data.items()
                                 if k in ScoringSession.__dataclass_fields__})
    return None


def update_session(session: ScoringSession):
    sessions = _load_sessions()
    sessions[session.id] = session.to_dict()
    _save_sessions(sessions)


def list_sessions() -> list[dict]:
    sessions = _load_sessions()
    return list(sessions.values())
