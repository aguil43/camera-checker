from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class CameraStatus(str, Enum):
    OK = "OK"
    OFFLINE = "OFFLINE"
    AUTH_FAILED = "AUTH_FAILED"
    NO_RECORDINGS = "NO_RECORDINGS"
    ERROR = "ERROR"

class RecordingItem(BaseModel):
    file_name: str
    storage: Optional[str] = None
    trigger_type: Optional[str] = None
    start_time_str: str
    end_time_str: Optional[str] = None
    media_type: Optional[str] = None
    start_time: Optional[datetime] = None

class Camera(BaseModel):
    id: Optional[int] = None
    name: str
    ip_or_url: str
    username: str
    password: str
    vendor_type: str = "vivotek"
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CheckLog(BaseModel):
    id: Optional[int] = None
    camera_id: int
    camera_name: Optional[str] = None
    status: CameraStatus
    recordings_count: int = 0
    latest_recording_time: Optional[str] = None
    details: str
    screenshot_path: Optional[str] = None
    checked_at: Optional[datetime] = None

class AlertHistory(BaseModel):
    id: Optional[int] = None
    camera_id: int
    alert_type: CameraStatus
    recipient: str
    details: str
    sent_at: Optional[datetime] = None
