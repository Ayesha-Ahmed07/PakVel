from pydantic import BaseModel
from typing import Optional

class Broker(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None