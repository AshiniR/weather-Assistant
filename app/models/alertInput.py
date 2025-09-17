from pydantic import BaseModel, Field

class AlertInput(BaseModel):
    location: str = Field(description="City and optionally country, e.g., 'New York, USA'")