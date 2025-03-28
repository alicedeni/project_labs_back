from pydantic import BaseModel
from typing import List, Optional

class Result_Method(BaseModel):
    status: int
    
class Criteria(BaseModel):
    criteria: List[str]
    score: List[float]

class Result(BaseModel):
    criteria: str
    score: float
    comment: str

class Result_Method(BaseModel):
    status: str 
    summary: Optional[dict] = None 
    error: Optional[str] = None