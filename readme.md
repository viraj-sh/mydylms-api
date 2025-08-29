## MYDY LMS API (Unofficial)

This is a FastAPI-based wrapper for the MYDY LMS.  
It provides endpoints to access login, semesters, subjects, documents, and attendance data.

---

### Installation

```bash
pip install -r requirements.txt
```

---

### Running the Server

```bash
uvicorn api:app --reload
```

API will be available at:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Endpoints Overview

#### Root & Health

- `GET /` – API info message
- `GET /health` – health check
- `GET /creds` – view stored credentials

#### Authentication

- `POST /auth/login` – login with email and password, saves token
- `GET /auth/token` – check if stored token is valid
- `DELETE /auth/delete` – remove token

#### Semesters and Subjects

- `GET /sem` – list all semesters (`?sem_no=` optional, `-1` for latest, or a number within range)
- `GET /sem/{sem_no}` – list subjects in a semester
- `GET /sem/{sem_no}/sub` – list subjects in a semester or fetch subject details with `?sub_id=`
- `GET /sem/{sem_no}/sub/{sub_id}` – get subject details for a semester subject
- `GET /sub/{sub_id}` – get subject details

#### Documents (by Semester/Subject)

- `GET /sem/{sem_no}/sub/{sub_id}/doc` – list all documents for a subject
- `GET /sem/{sem_no}/sub/{sub_id}/doc/{doc_id}` – get single document info
- `GET /sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/download` – download a document
- `GET /sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/view` – view a document inline

#### Documents (by Subject only)

- `GET /sub/{sub_id}/doc` – list all documents for a subject
- `GET /sub/{sub_id}/doc/{doc_id}` – get single document info
- `GET /sub/{sub_id}/doc/{doc_id}/download` – download a document
- `GET /sub/{sub_id}/doc/{doc_id}/view` – view a document inline

#### Documents (direct)

- `GET /doc?doc_id=&mod_type=` – fetch document info
- `GET /doc/download?doc_id=&mod_type=` – download a document
- `GET /doc/view?doc_id=&mod_type=` – view a document inline

#### Attendance

- `GET /attendance` – overall attendance
- `GET /attendance?filter=detailed` – detailed attendance
- `GET /attendance/{altid}` – attendance for a subject

---

### Notes

- Session is managed automatically after `/auth/login`.
- `GET /creds` shows stored credentials.
- Documents can be downloaded or viewed inline depending on the endpoint.
- Data is stored locally in `./data/`.

---

### Usage and Disclaimer

- This project is for **personal and educational purposes only**.
- It is **not affiliated with, endorsed by, or supported by DY Patil University**.
- Use of this API is at your own risk. The author is **not responsible for any misuse, data loss, or violations of institutional policies**.
- Do not use this to overload, abuse, or disrupt official LMS services.
