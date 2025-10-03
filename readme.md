## MYDY LMS API (Unofficial)

This is a FastAPI-based wrapper for the MYDY LMS.  
It provides endpoints to access login, semesters, subjects, documents, and attendance data.

---

### Installation

```bash
pip install -r requirements.txt
```

---

### Running the Server (Locally)

```bash
uvicorn api:app --reload
```

API will be available at:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Running with Docker

You can run this API using Docker in two ways:

#### 1. Build Locally

A `Dockerfile` is included in the root directory.
To build and run:

```bash
docker build -t mydylms-api .
docker run -p 8000:8000 mydylms-api
```

#### 2. Use Prebuilt Image from Docker Hub

A prebuilt image is available on Docker Hub:

```bash
docker pull virajsh/mydylms-api:latest
docker run -p 8000:8000 virajsh/mydylms-api:latest
```

---

### Endpoints Overview

#### System

- `GET /` – Root endpoint
  Returns a basic API info message.

- `GET /health` – Health check
  Returns service status and uptime confirmation.

---

#### Authentication

- `POST /auth/login` – Login and store credentials
  Accepts `email` and `password`, retrieves and saves a valid token locally.

- `GET /auth/me` – Get current stored credentials
  Returns stored credentials (excluding password).

- `GET /auth/token` – Get or regenerate token
  Retrieves the current token or regenerates it if requested using `?regenerate=true`.

- `DELETE /auth/token` – Delete stored token
  Deletes only the saved token while keeping other credentials intact.

- `DELETE /auth` – Delete all stored credentials
  Deletes the entire stored credentials file.

---

#### Semesters and Subjects

- `GET /sem` – Get all semesters
  Returns a list of all semesters available locally.

- `GET /sem/{sem_no}` – Get a specific semester
  Returns details of the specified semester. Use `-1` to fetch the latest semester.

- `GET /sem/{sem_no}/sub` – Get all subjects for a semester
  Returns all subjects in the specified semester.

- `GET /sem/{sem_no}/sub/{sub_id}` – Get modules for a specific subject
  Returns paginated module data for a given subject within a semester.

---

#### Documents (by Semester and Subject)

- `GET /sem/{sem_no}/sub/{sub_id}/doc` – List all documents of a subject in a semester
  Returns a paginated list of documents for a subject.

- `GET /sem/{sem_no}/sub/{sub_id}/doc/{doc_id}` – Get metadata for a specific document
  Returns document metadata and related information.

- `GET /sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/view` – View a document inline
  Streams a document for in-browser viewing.

- `GET /sem/{sem_no}/sub/{sub_id}/doc/{doc_id}/download` – Download a document
  Downloads the requested document as a file.

---

#### Documents (by Subject)

- `GET /sub/{sub_id}` – Get modules for a subject
  Returns module data for the specified subject.

- `GET /sub/{sub_id}/doc` – Get all documents of a subject
  Returns a paginated list of all documents for the given subject.

- `GET /sub/{sub_id}/doc/{doc_id}` – Get metadata of a specific document
  Returns metadata for the specified document.

- `GET /sub/{sub_id}/doc/{doc_id}/view` – View a document inline
  Streams a document for in-browser viewing.

- `GET /sub/{sub_id}/doc/{doc_id}/download` – Download a document
  Downloads the document file.

---

### Notes

- Authentication credentials and tokens are stored locally after a successful `/auth/login`.
- Use `/auth/me` to view stored credentials (passwords are never returned).
- Tokens can be regenerated, deleted individually, or removed along with all credentials using `/auth/token` and `/auth`.
- Most list-based endpoints support pagination using `?page=` and `?page_size=` query parameters.
- Documents can be either viewed inline or downloaded, depending on the chosen endpoint.
- Data is cached and stored locally in the `./data/` directory for faster subsequent access.
- All endpoints return structured JSON responses with `status`, `data`, and (where applicable) `pagination` metadata.

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
