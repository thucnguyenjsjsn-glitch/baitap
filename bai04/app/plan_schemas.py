from pydantic import BaseModel, Field, ConfigDict, field_validator

class Task(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    owner: str | None = None
    @field_validator('id', 'title')
    @classmethod
    def strip_nonempty(cls, v):
        if not v.strip(): raise ValueError('Không được để trống')
        return v.strip()

class Dependency(BaseModel):
    model_config = ConfigDict(extra='forbid')
    before: str = Field(min_length=1)
    after: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    @field_validator('before','after','evidence')
    @classmethod
    def strip_nonempty(cls,v):
        if not v.strip(): raise ValueError('Không được để trống')
        return v.strip()

class PlanExtracted(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tasks: list[Task]
    dependencies: list[Dependency]

class ExtractRequest(BaseModel):
    text: str = Field(min_length=1)

class ValidateRequest(BaseModel):
    extracted: PlanExtracted

class OrderRequest(BaseModel):
    original_text: str = Field(min_length=1)
    extracted: PlanExtracted
    ai_extracted: PlanExtracted | None = None
    save: bool = True
