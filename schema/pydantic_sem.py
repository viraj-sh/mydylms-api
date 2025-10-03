from pydantic import BaseModel
from typing import List

class Subject(BaseModel):
    id: int
    name: str

class Semester(BaseModel):
    semester: str
    subjects: List[Subject]
    
class Module(BaseModel):
    id: str
    name: str
    mod_type: str
    