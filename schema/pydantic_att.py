from typing import Dict, Any
from fastapi import Path, Query, HTTPException
from pydantic import BaseModel

class AttendanceResponse(BaseModel):
    status: str
    type: str
    data: Any
