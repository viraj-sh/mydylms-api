from pydantic import BaseModel, Field, EmailStr
from typing import Annotated, Optional


class Auth(BaseModel):
    email: Annotated[EmailStr, Field(..., description="email used to login mydylms portal", examples=["abc@dypatil.edu"])]
    password: Annotated[str, Field(..., description="password used to login mydylms portal")]