import enum


class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    AGENCY_MANAGER = "AGENCY_MANAGER"
    AGENCY_OPERATOR = "AGENCY_OPERATOR"
    CLIENT_DIRECTOR = "CLIENT_DIRECTOR"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"
    WITHDRAWN = "WITHDRAWN"


class OrgStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class OrgPlan(str, enum.Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class InvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class PlatformType(str, enum.Enum):
    YOUTUBE = "YOUTUBE"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    X = "X"
    NAVER_BLOG = "NAVER_BLOG"


class ChannelStatus(str, enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    ACTIVE = "ACTIVE"
    EXPIRING = "EXPIRING"
    EXPIRED = "EXPIRED"


class ChannelEventType(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    STATUS_CHANGED = "STATUS_CHANGED"


class ContentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    PARTIALLY_PUBLISHED = "PARTIALLY_PUBLISHED"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class PublishResultStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ApprovalStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalAction(str, enum.Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"


# ── Phase 1-B ENUMs ─────────────────────────────────────


class CommentSentiment(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    DANGEROUS = "DANGEROUS"


class CommentStatus(str, enum.Enum):
    UNPROCESSED = "UNPROCESSED"
    PUBLISHED = "PUBLISHED"
    HIDDEN = "HIDDEN"
    PENDING_DELETE = "PENDING_DELETE"
    DELETED = "DELETED"


class NotificationType(str, enum.Enum):
    PUBLISH_COMPLETE = "PUBLISH_COMPLETE"
    PUBLISH_FAILED = "PUBLISH_FAILED"
    APPROVAL_REQUEST = "APPROVAL_REQUEST"
    APPROVAL_RESULT = "APPROVAL_RESULT"
    DANGEROUS_COMMENT = "DANGEROUS_COMMENT"
    COMMENT_NEW = "COMMENT_NEW"
    TOKEN_EXPIRING = "TOKEN_EXPIRING"
    SYSTEM = "SYSTEM"


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    WEB_PUSH = "WEB_PUSH"
    TELEGRAM = "TELEGRAM"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    PUBLISH = "PUBLISH"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    INVITE = "INVITE"
    EXPORT = "EXPORT"
    CONNECT = "CONNECT"
    DISCONNECT = "DISCONNECT"


class AiTaskType(str, enum.Enum):
    TITLE = "TITLE"
    DESCRIPTION = "DESCRIPTION"
    HASHTAG = "HASHTAG"
    META_DESC = "META_DESC"
    ALT_TEXT = "ALT_TEXT"
    SENTIMENT = "SENTIMENT"
    COMMENT_REPLY = "COMMENT_REPLY"
    TONE_CONVERT = "TONE_CONVERT"
    CONTENT_REVIEW = "CONTENT_REVIEW"
    SUBTITLE = "SUBTITLE"
    SUBTITLE_BURNIN = "SUBTITLE_BURNIN"
    SHORTFORM = "SHORTFORM"
    SHORTFORM_RENDER = "SHORTFORM_RENDER"
    THUMBNAIL = "THUMBNAIL"
    TRANSLATION = "TRANSLATION"
    REPORT = "REPORT"
    PREDICTION = "PREDICTION"
    SUGGEST_EFFECTS = "SUGGEST_EFFECTS"
    IMPROVE_TEMPLATE = "IMPROVE_TEMPLATE"


# ── Phase 2 ENUMs ──────────────────────────────────────


class MediaType(str, enum.Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    DOCUMENT = "DOCUMENT"


class CalendarEventType(str, enum.Enum):
    SCHEDULED_POST = "SCHEDULED_POST"
    HOLIDAY = "HOLIDAY"
    ANNIVERSARY = "ANNIVERSARY"
    CUSTOM = "CUSTOM"


class AiJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AiJobType(str, enum.Enum):
    SUBTITLE = "SUBTITLE"
    SUBTITLE_BURNIN = "SUBTITLE_BURNIN"
    SHORTFORM = "SHORTFORM"
    SHORTFORM_RENDER = "SHORTFORM_RENDER"
    REPORT = "REPORT"
    THUMBNAIL = "THUMBNAIL"


# ── Phase 3 ENUMs ──────────────────────────────────────


class ReportPeriod(str, enum.Enum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class ReportStatus(str, enum.Enum):
    GENERATING = "GENERATING"
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class MediaRoleType(str, enum.Enum):
    SOURCE = "SOURCE"
    EDITED = "EDITED"
    SUBTITLE = "SUBTITLE"
    THUMBNAIL = "THUMBNAIL"
    EFFECT = "EFFECT"
