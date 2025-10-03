import io
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Annotated, Optional, List
from pathlib import Path
from fastapi.responses import StreamingResponse, FileResponse

from core.auth import login, verify_token, get_token
from core.utils import dump_json, load_json, load_json_token, CREDENTIALS_PATH
from core.semester import sem, sem_sub, load_semsub, load_sem, get_valid_sem_no
from core.subjects import sub, load_sub
from core.documents import doc, help_doc
from core.download import download_file, help_download_file
from core.attendence import o_attendance, d_attendance, s_attendance
from schema.pydantic_auth import Auth
from schema.pydantic_sem import Subject, Semester, Module
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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

@app.get('/')
def home():
    return {'message':'Unofficial MY-DY-Lms Api'}

@app.get('/health')
def health_check():
    return {
        'status': 'OK'
    }
    
@app.get("/creds")
def mycreds():
    creds = load_json(CREDENTIALS_PATH)
    if not creds:
        return {
            "status": "error",
            "message": "No credentials found. Please login via /auth/login first."
        }
    return {"status": "ok", "credentials": creds}
    
@app.post('/auth/login')
def authlogin(auth: Auth):
    try:
        token = login(auth.email, auth.password)
        if token:
            credentials = {
                "email": auth.email,
                "password": auth.password,
                "token": token
            }
            dump_json(credentials, CREDENTIALS_PATH)
            return JSONResponse(
                status_code=201,
                content={"token": token, "success": True}
            )
        return JSONResponse(
            status_code=400,
            content={"token": None, "success": False, "message": "Token not found"}
        )
    except ValueError as e:
        # Wrong credentials
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        # Unexpected login failure
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/auth/token")
def authtoken(regenerate: bool = Query(False)):
    try:
        token = get_token(regenerate=regenerate)
        valid = verify_token(token) if token else False
        return JSONResponse(
            status_code=200,
            content={"token": token, "valid": valid}
        )
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"token": None, "valid": False, "error": str(e)}
        )

@app.delete("/auth/delete-token")
def delete_token():
    creds = load_json(CREDENTIALS_PATH)
    if not creds:
        raise HTTPException(status_code=404, detail="credentials.json not found")
    if not creds.get("token"):
        return {"success": False, "message": "Token is not present"}
    creds["token"] = ""
    dump_json(creds, CREDENTIALS_PATH)
    return {"success": True, "message": "Token deleted"}

@app.delete("/auth/delete-creds")
def delete_creds():
    if not os.path.exists(CREDENTIALS_PATH):
        return {"success": False, "message": "Credentials file not found"}
    os.remove(CREDENTIALS_PATH)
    return {"success": True, "message": "All credentials deleted"}
    
@app.get('/sem', response_model=List[Semester])
def get_all_semesters():
    return load_sem()

@app.get('/sem/{sem_no}', response_model=Semester)
def get_semester(sem_no: int):
    sem_no, semesters = get_valid_sem_no(sem_no)
    return semesters[sem_no - 1]

@app.get('/sem/{sem_no}/sub', response_model=List[Subject])
def get_subjects(sem_no: int):
    sem_no, semesters = get_valid_sem_no(sem_no)
    subjects = load_semsub(sem_no)
    if not subjects:
        raise HTTPException(
            status_code=404,
            detail=f'No subjects found in Semester {sem_no}'
        )
    return subjects

@app.get('/sem/{sem_no}/sub/{sub_id}', response_model=List[Module])
def get_subject(sem_no: int, sub_id: int):
    sem_no, semesters = get_valid_sem_no(sem_no)
    subjects = load_semsub(sem_no)
    if not any(s["id"] == sub_id for s in subjects):
        raise HTTPException(
            status_code=404,
            detail=f'Subject ID {sub_id} not found in Semester {sem_no}'
        )
    return load_sub(sub_id)  

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
