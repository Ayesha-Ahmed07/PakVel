# app/models/user_model.py

from pydantic import BaseModel, EmailStr
from typing import Optional

# Shared base model for users
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "traveler"  # traveler or broker

# Used when a new user registers
class UserCreate(UserBase):
    password: str

# Used for login requests
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Model used for reading user data (response)
class UserOut(UserBase):
    id: str

# Optional — internal DB representation if needed
class UserInDB(UserBase):
    hashed_password: str
