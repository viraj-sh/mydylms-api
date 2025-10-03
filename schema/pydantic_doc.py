from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class DocumentResponse(BaseModel):
    id: int
    mod_type: str
    name: str
    doc_url: str


class DocumentListResponse(BaseModel):
    status: str
    data: List[DocumentResponse]
    pagination: Optional[Dict[str, Any]] = None
