import io
import os
import requests
import logging
from fastapi import FastAPI, HTTPException, Query, Request, Path
from fastapi.responses import JSONResponse
from typing import Annotated, Optional, List, Dict, Any
from fastapi.responses import StreamingResponse, FileResponse

from core.auth import login, verify_token, get_token
from core.utils import dump_json, load_json, load_json_token, CREDENTIALS_PATH
from core.semester import sem, sem_sub, load_semsub, load_sem, get_valid_sem_no
from core.subjects import sub, load_sub
from core.documents import doc, help_doc
from core.download import download_file, help_download_file
from core.attendence import o_attendance, d_attendance, s_attendance
from core.exceptions import add_exception_handlers
from core.logging_config import setup_logging
from core.pagination import paginate_list
from schema.pydantic_auth import Auth, MessageResponse, HealthResponse, LoginSuccessResponse, LoginFailureResponse, MeResponse, TokenResponse, DeleteResponse
from schema.pydantic_sem import Subject, Semester, Module, ListResponse, SemesterListResponse, SubjectListResponse, ModuleListResponse, SemesterResponse
from fastapi.middleware.cors import CORSMiddleware

setup_logging()
logger = logging.getLogger("mydylms")

app = FastAPI(title="Unofficial mydylms-api API")

origins = [
    "http://127.0.0.1:5500",   # add all your dev URLs here
    "*",                       # or "*" for all origins (be careful in production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # Allow all HTTP methods including OPTIONS
    allow_headers=["*"],
)

add_exception_handlers(app)
logger.info("Application startup complete")

@app.get("/", tags=["System"], summary="Root endpoint", response_model=MessageResponse)
def home():
    return {"message": "Unofficial MY-DY-Lms Api"}

@app.get("/health", tags=["System"], summary="Health check", response_model=HealthResponse)
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
        raise HTTPException(status_code=503, detail=f"External login service error: {e}")

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

@app.get("/auth/me", tags=["Auth"], summary="Get current stored credentials", response_model=MeResponse)
def authme():
    creds = load_json(CREDENTIALS_PATH)
    if not creds:
        raise HTTPException(status_code=404, detail="No credentials found. Please login first.")
    safe_creds = {k: v for k, v in creds.items() if k != "password"}
    return {"status": "ok", "credentials": safe_creds}

@app.get("/auth/token", tags=["Auth"], summary="Get or regenerate token", response_model=TokenResponse)
def authtoken(regenerate: bool = Query(False, description="Regenerate token if true")):
    try:
        token = get_token(regenerate=regenerate)
        valid = verify_token(token) if token else False
        return {"token": token, "valid": valid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token error: {e}")

@app.delete("/auth/token", tags=["Auth"], summary="Delete stored token", response_model=DeleteResponse)
def delete_token():
    creds = load_json(CREDENTIALS_PATH)
    if not creds:
        raise HTTPException(status_code=404, detail="credentials.json not found")
    if not creds.get("token"):
        return {"success": False, "message": "Token is not present"}  # soft fail, keep as 200
    creds["token"] = ""
    dump_json(creds, CREDENTIALS_PATH)
    return {"success": True, "message": "Token deleted"}

@app.delete("/auth", tags=["Auth"], summary="Delete all stored credentials", response_model=DeleteResponse)
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
def get_subject(
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

@app.get('/sem/{sem_no}/sub/{sub_id}/doc')
def getsubjects(
    sem_no: int,
    sub_id: int
):
    semester = load_sem()
    if sem_no ==-1 or (sem_no <= len(semester) and sem_no > 0):
        pass
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Semester Number range(-1 or 1 to {len(semester)})')  
    
    semesters = load_semsub(sem_no)
    
    if any(item["id"] == sub_id for item in semesters):
        pass
    elif sub_id == None:
        return semesters
    else:
        raise HTTPException(status_code=400, detail=f'Subject ID {sub_id} is not present in the Semester {sem_no}')
    
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = []
    for entry in semsub:
        doc_id = entry["id"]
        mod_type = entry["mod_type"]
        name = entry["name"]

        try:
            doc_url = help_doc(mod_type, doc_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")

        results.append({
            "id": doc_id,
            "mod_type": mod_type,
            "name": name,
            "doc_url": doc_url 
        })

    return results    

@app.get('/sub/{sub_id}')
def getsubjects(sub_id: int):
    try:
        semsub = load_sub(sub_id)
        if semsub:
            return semsub
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))    
    return semsub

@app.get("/sub/{sub_id}/doc")
def get_all_docs_from_subject(sub_id: int):
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = []
    for entry in semsub:
        doc_id = entry["id"]
        mod_type = entry["mod_type"]
        name = entry["name"]

        try:
            doc_url = help_doc(mod_type, doc_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")

        results.append({
            "id": doc_id,
            "mod_type": mod_type,
            "name": name,
            "doc_url": doc_url 
        })

    return results

@app.get("/sub/{sub_id}/doc/{doc_id}")
def get_doc_from_subject(sub_id: int, doc_id: int):
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)
    
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")

    mod_type = doc_entry["mod_type"]
    name = doc_entry["name"]
    
    try:
        doc_url = help_doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    return {
        "id": doc_id,
        "mod_type": mod_type,
        "name": name,
        "doc_url": doc_url 
    }


@app.get('/sem/{sem_no}/sub/{sub_id}/doc/{doc_id}')
def getsubjects(
    sem_no: int,
    sub_id: int,
    doc_id: int
):
    semester = load_sem()
    if sem_no ==-1 or (sem_no <= len(semester) and sem_no > 0):
        pass
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Semester Number range(-1 or 1 to {len(semester)})')  
    
    semesters = load_semsub(sem_no)
    
    if any(item["id"] == sub_id for item in semesters):
        pass
    elif sub_id == None:
        return semesters
    else:
        raise HTTPException(status_code=400, detail=f'Subject ID {sub_id} is not present in the Semester {sem_no}')
    
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)    
    
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")  
    
    mod_type = doc_entry["mod_type"]
    name = doc_entry["name"]      
    
    try:
        doc_url = help_doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    return {
        "id": doc_id,
        "mod_type": mod_type,
        "name": name,
        "doc_url": doc_url 
    }     


@app.get('/sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/download')
def getsubjects(
    sem_no: int,
    sub_id: int,
    doc_id: int
):
    semester = load_sem()
    if sem_no ==-1 or (sem_no <= len(semester) and sem_no > 0):
        pass
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Semester Number range(-1 or 1 to {len(semester)})')  
    
    semesters = load_semsub(sem_no)
    
    if any(item["id"] == sub_id for item in semesters):
        pass
    elif sub_id == None:
        return semesters
    else:
        raise HTTPException(status_code=400, detail=f'Subject ID {sub_id} is not present in the Semester {sem_no}')
    
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)    
    
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")  
    
    mod_type = doc_entry["mod_type"]
    name = doc_entry["name"]      
    
    try:
        doc_url = help_doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    filename, content = help_download_file(doc_url)

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )   

@app.get('/sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/view')
def getsubjects(
    sem_no: int,
    sub_id: int,
    doc_id: int
):
    semester = load_sem()
    if sem_no ==-1 or (sem_no <= len(semester) and sem_no > 0):
        pass
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Semester Number range(-1 or 1 to {len(semester)})')  
    
    semesters = load_semsub(sem_no)
    
    if any(item["id"] == sub_id for item in semesters):
        pass
    elif sub_id == None:
        return semesters
    else:
        raise HTTPException(status_code=400, detail=f'Subject ID {sub_id} is not present in the Semester {sem_no}')
    
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)    
    
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")  
    
    mod_type = doc_entry["mod_type"]
    name = doc_entry["name"]      
    
    try:
        doc_url = help_doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    # Download the file with MoodleSession
    filename, content = help_download_file(doc_url)

    # Guess media type (basic: PDF, else default)
    if filename.lower().endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
        media_type = f"image/{filename.split('.')[-1].lower()}"
    else:
        media_type = "application/octet-stream"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@app.get("/sub/{sub_id}/doc/{doc_id}/download")
def download(sub_id: int, doc_id: int):
    
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))    
    
    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)    
    
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")

    mod_type = doc_entry["mod_type"]
    name = doc_entry["name"]
    
    try:
        doc_url = doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    if not doc_url:
        raise HTTPException(status_code=404, detail=f"No file available for document {doc_id}")

    filename, content = help_download_file(doc_url)

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/sub/{sub_id}/doc/{doc_id}/view")
def view_doc(sub_id: int, doc_id: int):
    try:
        semsub = load_sub(sub_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")

    mod_type = doc_entry["mod_type"]

    try:
        doc_url = doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")

    if not doc_url:
        raise HTTPException(status_code=404, detail=f"No file available for document {doc_id}")

    # Download the file with MoodleSession
    filename, content = help_download_file(doc_url)

    # Guess media type (basic: PDF, else default)
    if filename.lower().endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
        media_type = f"image/{filename.split('.')[-1].lower()}"
    else:
        media_type = "application/octet-stream"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@app.get("/doc")
def get_doc_from_subject(
    doc_id: int = Query(..., description="Document ID"),
    mod_type: str = Query(...,description="Mod Type of the Document")
):
 
    try:
        doc_url = help_doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    return {
        "id": doc_id,
        "mod_type": mod_type,
        "doc_url": doc_url 
    }

@app.get("/doc/download")
def get_doc_from_subject(
    doc_id: int = Query(..., description="Document ID"),
    mod_type: str = Query(...,description="Mod Type of the Document")
):
 
    try:
        doc_url = doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    filename, content = help_download_file(doc_url)

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/doc/view")
def get_doc_from_subject(
    doc_id: int = Query(..., description="Document ID"),
    mod_type: str = Query(...,description="Mod Type of the Document")
):
 
    try:
        doc_url = doc(mod_type, doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    filename, content = help_download(doc_url)

    # Guess media type (basic: PDF, else default)
    if filename.lower().endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
        media_type = f"image/{filename.split('.')[-1].lower()}"
    else:
        media_type = "application/octet-stream"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@app.get('/attendance') 
def getattendance(
    filter: Optional[str] = Query("overall", description="Type of Attendance overall or detailed")
):
    att = o_attendance()
    if filter == "detailed":
        att = d_attendance()

    return att

@app.get('/attendance/{altid}') 
def getattendance(
    altid: int
):
    att = s_attendance(altid)
    return att

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug = True)
