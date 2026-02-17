from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime


class UserRecord(BaseModel):
    username: str
    source: str = "csv"  # "csv", "api", etc.


class QueryResult(BaseModel):
    username: str
    connector_id: str
    exists: bool
    error: str | None = None


class VerificationResults(BaseModel):
    users: List[str]
    sources: List[str]
    results: Dict[str, Dict[str, bool]]  # {username: {connector_id: exists}}
    timestamp: datetime


class UploadResponse(BaseModel):
    user_count: int
    users: List[str]
    message: str
