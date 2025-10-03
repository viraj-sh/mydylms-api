from pydantic import BaseModel, Field, EmailStr
from typing import Annotated, Optional


class Auth(BaseModel):
    email: Annotated[
        EmailStr,
        Field(..., description="Email used to login to MY-DY LMS portal", examples=["abc@dypatil.edu"])
    ]
    password: Annotated[
        str,
        Field(..., description="Password used to login to MY-DY LMS portal")
    ]
    
class MessageResponse(BaseModel):
    message: str

class HealthResponse(BaseModel):
    status: str

class LoginSuccessResponse(BaseModel):
    token: str
    success: bool = True
    message: str = "Login successful"

class LoginFailureResponse(BaseModel):
    token: Optional[str] = None
    success: bool = False
    message: str

class MeResponse(BaseModel):
    status: str
    credentials: dict

class TokenResponse(BaseModel):
    token: str | None
    valid: bool
    error: str | None = None

class DeleteResponse(BaseModel):
    success: bool
    message: str    