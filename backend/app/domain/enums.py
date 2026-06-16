from enum import StrEnum


class Subject(StrEnum):
    MATH_PROFILE = "math_profile"
    INFORMATICS = "informatics"


class Role(StrEnum):
    STUDENT = "student"
    GUARDIAN = "guardian"
    OPERATOR = "operator"


class MissionStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"
    REPEAT = "repeat"
    SKIPPED = "skipped"


class AttemptMode(StrEnum):
    CLEAN_SHEET = "clean_sheet"
    WITH_HINT = "with_hint"
    UNKNOWN = "unknown"


class AttemptKind(StrEnum):
    TEXT = "text"
    CODE = "code"
    PHOTO = "photo"
    MIXED = "mixed"


class AiPolicy(StrEnum):
    ATTEMPT_FIRST = "attempt_first"
    BLOCKED = "blocked"
    ALLOWED_AFTER_ATTEMPT = "allowed_after_attempt"


class EvidenceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class ErrorCategory(StrEnum):
    ARITHMETIC = "arithmetic"
    SIGN_TRANSFER = "sign_transfer"
    ODZ_LOGIC = "odz_logic"
    CONDITION_READING = "condition_reading"
    PROBABILITY_DOUBLE_COUNT = "probability_double_count"
    UNKNOWN_METHOD = "unknown_method"
    ALGORITHM_LOGIC = "algorithm_logic"
    CODE_SYNTAX = "code_syntax"
    CODE_ALGORITHM = "code_algorithm"
    TIME_MANAGEMENT = "time_management"
    NONE = "none"
    OTHER = "other"


class ReviewStatus(StrEnum):
    DUE = "due"
    DONE = "done"
    BACK_TO_WORK = "back_to_work"
