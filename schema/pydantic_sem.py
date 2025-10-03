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


class ListResponse(BaseModel):
    status: str
    data: list


class SemesterListResponse(BaseModel):
    status: str
    data: List[Semester]


class SubjectListResponse(BaseModel):
    status: str
    data: List[Subject]


class ModuleListResponse(BaseModel):
    status: str
    data: List[Module]

class SemesterResponse(BaseModel):
    status: str
    data: Semester
