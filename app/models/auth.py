from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Any, Optional
from datetime import datetime

class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)  # Solo validación de longitud mínima

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)  # Solo validación de longitud mínima

class UserResponse(BaseModel):
    id: int
    firebase_uid: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

class SignupResponse(BaseModel):
    message: str
    user: Dict[str, Any]

class LoginResponse(BaseModel):
    message: str
    id_token: str  # Token estándar de Firebase
    firebase_uid: str
    custom_jwt: Optional[str] = None  # Solo presente para admins
    is_admin: bool
    instructions: dict

