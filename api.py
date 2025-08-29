import io
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from typing import Annotated, Optional
from pathlib import Path
from fastapi.responses import StreamingResponse

from core.auth import login, verify_token
from core.utils import dump_json, load_json, load_json_token
from core.semester import sem, sem_sub
from core.subjects import sub
from core.documents import doc
from core.download import download_file
from core.attendence import o_attendance, d_attendance, s_attendance

app = FastAPI()
CREDENTIALS_PATH = Path("./data/credentials.json")
token = load_json_token(CREDENTIALS_PATH)
data = sem(token)
dump_json(data,Path("./data/sem.json"))

class Auth(BaseModel):
    email: Annotated[EmailStr, Field(..., description="email used to login mydylms portal", examples=["abc@dypatil.edu"])]
    password: Annotated[str, Field(..., description="password used to login mydylms portal")]
    
@app.get('/creds')
def mycreds():
    creds = load_json(CREDENTIALS_PATH)
    return creds
    
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
    
@app.get('/auth/token')    
def authtoken():
    # creds = load_json(CREDENTIALS_PATH)
    # token = creds["token"]
    status = verify_token(token)
    return JSONResponse(
                status_code=201,
                content={"token": token,"valid":status}
            )
    
@app.delete('/auth/delete')    
def authdeltoken():
    # CREDENTIALS_PATH = Path("./data/credentials.json")
    creds = load_json(CREDENTIALS_PATH)
    if creds is None:
        raise HTTPException(status_code=404, detail="credentials.json not found")
    token = creds.get("token", "")
    if not token:
        return {"success": False, "message": "Token is not present"}
    creds["token"] = ""
    dump_json(creds, CREDENTIALS_PATH)
    updated_creds = load_json(CREDENTIALS_PATH)
    if updated_creds and not updated_creds.get("token"):
        return {"success": True, "message": "Token deleted"}
    else:
        return {"success": False, "message": "Token could not be deleted"}
    
@app.get('/sem')    
def getsemesters(
    sem_no: Optional[int] = Query(None, description="Semester Number")
):
    semester = load_json(Path("./data/sem.json"))
    if sem_no == None or sem_no ==-1 or (sem_no <= len(semester) and sem_no > 0):
        pass
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Semester Number range(-1 or 1 to {len(semester)})')
    
    if sem_no == None:
        pass
    elif sem_no <= len(semester):
        if sem_no == -1:
            semester = semester[sem_no]
        else:
            semester = semester[sem_no-1]
    else:
        HTTPException(status_code=404, detail=f"Invalid Semester Number should be less than {len(semester)}")
    return semester



@app.get('/sem/{sem_no}')    
def getsemesters(sem_no: int):
    semester = load_json(Path("./data/sem.json"))
    if sem_no ==-1 or (sem_no <= len(semester) and sem_no > 0):
        pass
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Semester Number range(-1 or 1 to {len(semester)})')    
    
    semesters = sem_sub(Path("./data/sem.json"), int(sem_no))
    
    return semesters

@app.get('/sem/{sem_no}/sub')
def getsubjects(
    sem_no: int,
    sub_id: Optional[int] = Query(None, description="Subject ID")
):
    semester = load_json(Path("./data/sem.json"))
    if sem_no ==-1 or (sem_no <= len(semester) and sem_no > 0):
        pass
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Semester Number range(-1 or 1 to {len(semester)})')  
    
    semesters = sem_sub(Path("./data/sem.json"), int(sem_no))
    
    if any(item["id"] == sub_id for item in semesters):
        pass
    elif sub_id == None:
        return semesters
    else:
        raise HTTPException(status_code=400, detail=f'Invalid Subject ID)')
    semsub = sub(sub_id, token)
    return semsub

@app.get('/sub/{sub_id}')
def getsubjects(sub_id: int):
    try:
        semsub = sub(sub_id, token)
        if semsub:
            return semsub
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))    
    return semsub

@app.get("/sub/{sub_id}/doc")
def get_all_docs_from_subject(sub_id: int):
    try:
        semsub = sub(sub_id, token)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = []
    for entry in semsub:
        doc_id = entry["id"]
        mod_type = entry["mod_type"]
        name = entry["name"]

        try:
            doc_url = doc(mod_type, doc_id, token)
        except Exception as e:
            # This should not happen since doc_id comes from semsub
            raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")

        results.append({
            "id": doc_id,
            "mod_type": mod_type,
            "name": name,
            "doc_url": doc_url  # could be None or string
        })

    return results
    
@app.get("/sub/{sub_id}/doc/{doc_id}")
def get_doc_from_subject(sub_id: int, doc_id: int):
    try:
        semsub = sub(sub_id, token)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)
    
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")

    mod_type = doc_entry["mod_type"]
    name = doc_entry["name"]
    
    try:
        doc_url = doc(mod_type, doc_id, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    return {
        "id": doc_id,
        "mod_type": mod_type,
        "name": name,
        "doc_url": doc_url 
    }
    
    
    
@app.get("/sub/{sub_id}/doc/{doc_id}/download")
def download(sub_id: int, doc_id: int):
    
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")

    mod_type = doc_entry["mod_type"]
    name = doc_entry["name"]
    
    try:
        doc_url = doc(mod_type, doc_id, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    if not doc_url:
        raise HTTPException(status_code=404, detail=f"No file available for document {doc_id}")

    filename, content = download_file(doc_url, token)

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/sub/{sub_id}/doc/{doc_id}/view")
def view_doc(sub_id: int, doc_id: int):
    try:
        semsub = sub(sub_id, token)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    doc_entry = next((d for d in semsub if str(d["id"]) == str(doc_id)), None)
    if not doc_entry:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in subject {sub_id}")

    mod_type = doc_entry["mod_type"]

    try:
        doc_url = doc(mod_type, doc_id, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")

    if not doc_url:
        raise HTTPException(status_code=404, detail=f"No file available for document {doc_id}")

    # Download the file with MoodleSession
    filename, content = download_file(doc_url, token)

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
        doc_url = doc(mod_type, doc_id, token)
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
        doc_url = doc(mod_type, doc_id, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    filename, content = download_file(doc_url, token)

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
        doc_url = doc(mod_type, doc_id, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching document {doc_id}: {e}")
    
    filename, content = download_file(doc_url, token)

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
    att = o_attendance(token)
    if filter == "detailed":
        att = d_attendance(token)

    return att

@app.get('/attendance/{altid}') 
def getattendance(
    altid: int
):
    att = s_attendance(altid, token)
    return att