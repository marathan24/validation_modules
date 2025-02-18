from pydantic import BaseModel

class ReasoningInput(BaseModel):
    func_name: str
    problem: str

class SystemPromptSchema(BaseModel):
    role: str