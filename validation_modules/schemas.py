from pydantic import BaseModel
from typing import List, Optional

class InputSchema(BaseModel):
    func_name: str
    problem: str
    thoughts: List[str]
    
class SystemPromptSchema(BaseModel):
    role: str

class ValidationResult(BaseModel):
    valid_thoughts: List[str]
    scores: List[int]
    best_thought: str
    best_thought_index: int
    verification_details: List[str]