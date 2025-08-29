## DY Patil LMS API (Unofficial)

This is a FastAPI-based wrapper for the DY Patil LMS.
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

#### Authentication

- `POST /auth/login` – login with email and password, saves token
- `GET /auth/token` – check if stored token is valid
- `DELETE /auth/delete` – remove token

#### Semesters and Subjects

- `GET /sem` – list all semesters
- `GET /sem/{sem_no}` – list subjects in a semester
- `GET /sub/{sub_id}` – get documents for a subject

#### Documents

- `GET /sub/{sub_id}/doc` – all docs for a subject
- `GET /sub/{sub_id}/doc/{doc_id}` – single doc info
- `GET /sub/{sub_id}/doc/{doc_id}/download` – download a document
- `GET /sub/{sub_id}/doc/{doc_id}/view` – view a document inline

#### Attendance

- `GET /attendance` – overall attendance
- `GET /attendance?filter=detailed` – detailed attendance
- `GET /attendance/{altid}` – attendance for a subject

---

### Notes

- Session is managed automatically after `/auth/login`.
- Documents can be downloaded or viewed inline depending on the endpoint.
- Data is stored locally in `./data/`.

---

### Usage and Disclaimer

- This project is for **personal and educational purposes only**.
- It is **not affiliated with, endorsed by, or supported by DY Patil University**.
- Use of this API is at your own risk. The author is **not responsible for any misuse, data loss, or violations of institutional policies**.
- Do not use this to overload, abuse, or disrupt official LMS services.
