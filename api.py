import io
import os
import requests
import logging
from fastapi import FastAPI, HTTPException, Query, Request, Path, Depends
from fastapi.responses import JSONResponse
from typing import Annotated, Optional, List, Dict, Any, Literal
from fastapi.responses import FileResponse

from core.auth import login, verify_token, get_token
from core.utils import dump_json, load_json, CREDENTIALS_PATH
from core.semester import (
    sem,
    sem_sub,
    load_semsub,
    load_sem,
    get_valid_sem_no,
    validate_sem,
    validate_sub,
)
from core.subjects import load_sub
from core.documents import (
    help_doc,
    get_doc_entry,
    guess_media_type,
    build_streaming_response,
    get_subject_or_404,
    get_doc_or_404,
    get_doc_url_or_500,
)
from core.download import help_download_file
from core.attendence import o_attendance, d_attendance, s_attendance
from core.exceptions import add_exception_handlers
from core.logging_config import setup_logging
from core.pagination import paginate_list
from schema.pydantic_auth import (
    Auth,
    MessageResponse,
    HealthResponse,
    LoginSuccessResponse,
    LoginFailureResponse,
    MeResponse,
    TokenResponse,
    DeleteResponse,
)
from schema.pydantic_doc import DocumentListResponse, DocumentResponse
from schema.pydantic_sem import (
    Subject,
    Semester,
    Module,
    ListResponse,
    SemesterListResponse,
    SubjectListResponse,
    ModuleListResponse,
    SemesterResponse,
)
from schema.pydantic_att import AttendanceResponse
from fastapi.middleware.cors import CORSMiddleware

setup_logging()
logger = logging.getLogger("mydylms")

app = FastAPI(title="Unofficial mydylms-api API")

origins = [
    "http://127.0.0.1:5500",  # add all your dev URLs here
    "*",  # or "*" for all origins (be careful in production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods including OPTIONS
    allow_headers=["*"],
)

add_exception_handlers(app)
logger.info("Application startup complete")


@app.get("/", tags=["System"], summary="Root endpoint", response_model=MessageResponse)
def home():
    return {"message": "Unofficial MY-DY-Lms Api"}


@app.get(
    "/health", tags=["System"], summary="Health check", response_model=HealthResponse
)
def health_check():
    return {"status": "OK"}


@app.post(
    "/auth/login",
    tags=["Auth"],
    summary="Login and store credentials",
    responses={
        200: {"model": LoginSuccessResponse},
        400: {"model": LoginFailureResponse},
        503: {"description": "External service unavailable"},
    },
)
def authlogin(auth: Auth):
    try:
        token = login(auth.email, auth.password)
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503, detail=f"External login service error: {e}"
        )

    if not token:
        raise HTTPException(status_code=400, detail="Token not found")

    credentials = {"email": auth.email, "password": auth.password, "token": token}
    dump_json(credentials, CREDENTIALS_PATH)
    return {
        "status": "ok",
        "token": token,
        "success": True,
        "message": "Login successful",
    }


@app.get(
    "/auth/me",
    tags=["Auth"],
    summary="Get current stored credentials",
    response_model=MeResponse,
)
def authme():
    creds = load_json(CREDENTIALS_PATH)
    if not creds:
        raise HTTPException(
            status_code=404, detail="No credentials found. Please login first."
        )
    safe_creds = {k: v for k, v in creds.items() if k != "password"}
    return {"status": "ok", "credentials": safe_creds}


@app.get(
    "/auth/token",
    tags=["Auth"],
    summary="Get or regenerate token",
    response_model=TokenResponse,
)
def authtoken(regenerate: bool = Query(False, description="Regenerate token if true")):
    try:
        token = get_token(regenerate=regenerate)
        valid = verify_token(token) if token else False
        return {"token": token, "valid": valid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token error: {e}")


@app.delete(
    "/auth/token",
    tags=["Auth"],
    summary="Delete stored token",
    response_model=DeleteResponse,
)
def delete_token():
    creds = load_json(CREDENTIALS_PATH)
    if not creds:
        raise HTTPException(status_code=404, detail="credentials.json not found")
    if not creds.get("token"):
        return {
            "success": False,
            "message": "Token is not present",
        }  # soft fail, keep as 200
    creds["token"] = ""
    dump_json(creds, CREDENTIALS_PATH)
    return {"success": True, "message": "Token deleted"}


@app.delete(
    "/auth",
    tags=["Auth"],
    summary="Delete all stored credentials",
    response_model=DeleteResponse,
)
def delete_creds():
    if not os.path.exists(CREDENTIALS_PATH):
        raise HTTPException(status_code=404, detail="Credentials file not found")
    os.remove(CREDENTIALS_PATH)
    return {"success": True, "message": "All credentials deleted"}


@app.get(
    "/sem",
    tags=["Semester"],
    summary="Get all semesters",
    response_model=SemesterListResponse,
)
def get_all_semesters():
    semesters = load_sem()
    if not semesters:
        raise HTTPException(status_code=404, detail="No semesters found")
    return {"status": "ok", "data": semesters}


@app.get(
    "/sem/{sem_no}",
    tags=["Semester"],
    summary="Get a specific semester",
    response_model=SemesterResponse,
)
def get_semester(
    sem_no: int = Path(..., description="Semester number. Use -1 for latest semester")
):
    sem_no, semesters = get_valid_sem_no(sem_no)
    return {"status": "ok", "data": semesters[sem_no - 1]}


@app.get(
    "/sem/{sem_no}/sub",
    tags=["Semester"],
    summary="Get all subjects for a semester",
    response_model=SubjectListResponse,
)
def get_subjects(
    sem_no: int = Path(..., description="Semester number. Use -1 for latest semester")
):
    sem_no, _ = get_valid_sem_no(sem_no)
    subjects = load_semsub(sem_no)
    if not subjects:
        raise HTTPException(
            status_code=404, detail=f"No subjects found in Semester {sem_no}"
        )
    return {"status": "ok", "data": subjects}


@app.get(
    "/sem/{sem_no}/sub/{sub_id}",
    tags=["Semester"],
    summary="Get modules for a specific subject",
    response_model=ModuleListResponse,
)
def get_subject_in_semester(
    sem_no: int = Path(..., description="Semester number. Use -1 for latest semester"),
    sub_id: int = Path(..., ge=1, description="Subject ID (>=1)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    sem_no, _ = get_valid_sem_no(sem_no)
    subjects = load_semsub(sem_no)
    if not any(s["id"] == sub_id for s in subjects):
        raise HTTPException(
            status_code=404,
            detail=f"Subject ID {sub_id} not found in Semester {sem_no}",
        )

    modules = load_sub(sub_id)
    if not modules:
        raise HTTPException(
            status_code=404,
            detail=f"No modules found for Subject {sub_id} in Semester {sem_no}",
        )

    paginated = paginate_list(modules, page, page_size)
    return {
        "status": "ok",
        "data": paginated["items"],
        "pagination": paginated["pagination"],
    }


@app.get(
    "/sem/{sem_no}/sub/{sub_id}/doc",
    tags=["Semester"],
    summary="List all documents of a subject in a semester",
    response_model=DocumentListResponse,
)
def list_subject_docs(
    sem_no: int = Path(..., description="Semester number. Use -1 for latest"),
    sub_id: int = Path(..., ge=1, description="Subject ID (>=1)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    semesters=Depends(validate_sem),
):
    validate_sub(sem_no, sub_id)
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = []
    for entry in semsub:
        try:
            doc_url = help_doc(entry["mod_type"], entry["id"])
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching document {entry['id']}: {e}"
            )
        results.append({**entry, "doc_url": doc_url})

    paginated = paginate_list(results, page, page_size)
    return {
        "status": "ok",
        "data": paginated["items"],
        "pagination": paginated["pagination"],
    }


@app.get(
    "/sem/{sem_no}/sub/{sub_id}/doc/{doc_id}",
    tags=["Semester"],
    summary="Get metadata for a specific document",
    response_model=DocumentResponse,
)
def get_doc_metadata(
    sem_no: int = Path(..., description="Semester number"),
    sub_id: int = Path(..., ge=1),
    doc_id: int = Path(..., ge=1),
    semesters=Depends(validate_sem),
):
    validate_sub(sem_no, sub_id)
    doc_entry = get_doc_entry(sub_id, doc_id)

    try:
        doc_url = help_doc(doc_entry["mod_type"], doc_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching document {doc_id}: {e}"
        )

    return {**doc_entry, "doc_url": doc_url}


@app.get(
    "/sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/view",
    tags=["Semester"],
    summary="Inline view of a document",
)
def view_doc(
    sem_no: int = Path(..., description="Semester number"),
    sub_id: int = Path(..., ge=1),
    doc_id: int = Path(..., ge=1),
    semesters=Depends(validate_sem),
):
    validate_sub(sem_no, sub_id)
    doc_entry = get_doc_entry(sub_id, doc_id)

    doc_url = help_doc(doc_entry["mod_type"], doc_id)
    filename, content = help_download_file(doc_url)

    return build_streaming_response(filename, content, inline=True)


@app.get(
    "/sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/download",
    tags=["Semester"],
    summary="Download a document",
)
def download_doc(
    sem_no: int = Path(..., description="Semester number"),
    sub_id: int = Path(..., ge=1),
    doc_id: int = Path(..., ge=1),
    semesters=Depends(validate_sem),
):
    validate_sub(sem_no, sub_id)
    doc_entry = get_doc_entry(sub_id, doc_id)

    doc_url = help_doc(doc_entry["mod_type"], doc_id)
    filename, content = help_download_file(doc_url)

    return build_streaming_response(filename, content, inline=True)


@app.get(
    "/sub/{sub_id}",
    tags=["Subject"],
    summary="Get modules for a subject",
    response_model=ModuleListResponse,
)
def get_subject(semsub: List[Dict[str, Any]] = Depends(get_subject_or_404)):
    return {"status": "ok", "data": semsub}


@app.get(
    "/sub/{sub_id}/doc",
    tags=["Subject"],
    summary="Get all documents of a subject",
    response_model=DocumentListResponse,
)
def get_all_docs_from_subject(
    semsub: List[Dict[str, Any]] = Depends(get_subject_or_404),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    results = []
    for entry in semsub:
        doc_url = get_doc_url_or_500(entry["mod_type"], entry["id"])
        results.append({**entry, "doc_url": doc_url})

    paginated = paginate_list(results, page, page_size)  # <-- your existing function
    return {
        "status": "ok",
        "data": paginated["items"],
        "pagination": paginated["pagination"],
    }


@app.get(
    "/sub/{sub_id}/doc/{doc_id}",
    tags=["Subject"],
    summary="Get metadata of a specific document",
    response_model=DocumentResponse,
)
def get_doc_from_subject(doc_entry: Dict[str, Any] = Depends(get_doc_or_404)):
    doc_url = get_doc_url_or_500(doc_entry["mod_type"], doc_entry["id"])
    return {**doc_entry, "doc_url": doc_url}


@app.get(
    "/sub/{sub_id}/doc/{doc_id}/view",
    tags=["Subject"],
    summary="Inline view of a subject document",
)
def view_doc(doc_entry: Dict[str, Any] = Depends(get_doc_or_404)):
    doc_url = get_doc_url_or_500(doc_entry["mod_type"], doc_entry["id"])
    filename, content = help_download_file(doc_url)  # <-- your existing function
    return build_streaming_response(filename, content, inline=True)


@app.get(
    "/sub/{sub_id}/doc/{doc_id}/download",
    tags=["Subject"],
    summary="Download a subject document",
)
def download_doc(doc_entry: Dict[str, Any] = Depends(get_doc_or_404)):
    doc_url = get_doc_url_or_500(doc_entry["mod_type"], doc_entry["id"])
    filename, content = help_download_file(doc_url)
    return build_streaming_response(filename, content, inline=False)


@app.get(
    "/doc/{mod_type}/{doc_id}",
    tags=["Document"],
    summary="Get metadata of a specific document",
)
def get_doc_from_subject(doc_id: int, mod_type: str):
    doc_url = get_doc_url_or_500(mod_type, doc_id)
    return {
        "id": doc_id,
        "mod_type": mod_type,
        "doc_url": doc_url,
    }


@app.get(
    "/doc/{mod_type}/{doc_id}/view",
    tags=["Document"],
    summary="Inline view of a specific document",
)
def view_doc(doc_id: int, mod_type: str):
    doc_url = get_doc_url_or_500(mod_type, doc_id)
    filename, content = help_download_file(doc_url)
    return build_streaming_response(filename, content, inline=True)


@app.get(
    "/doc/{mod_type}/{doc_id}/download",
    tags=["Document"],
    summary="Download a specific document",
)
def download_doc(doc_id: int, mod_type: str):
    doc_url = get_doc_url_or_500(mod_type, doc_id)
    filename, content = help_download_file(doc_url)
    return build_streaming_response(filename, content, inline=False)


@app.get("/att", tags=["Attendance"], summary="Get overall or detailed attendance")
def get_attendance(
    type: Literal["overall", "detailed"] = Query(
        "overall", description="Type of attendance: overall or detailed"
    )
) -> Dict[str, Any]:
    """
    Returns overall or detailed attendance summary.
    """
    att = d_attendance() if type == "detailed" else o_attendance()
    return {"status": "ok", "data": att}


@app.get(
    "/att/{altid}",
    tags=["Attendance"],
    summary="Get detailed attendance for a specific subject (alternate ID)",
    response_model=AttendanceResponse,
)
def get_subject_attendance(
    altid: int = Path(..., description="Subject alternate ID")
) -> Dict[str, Any]:
    """
    Returns detailed attendance for a specific subject by its alternate ID.
    """
    att = s_attendance(altid)
    if att is None:
        raise HTTPException(
            status_code=404, detail=f"No attendance found for subject ALTID {altid}"
        )

    return {"status": "ok", "type": "subject", "data": att}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
