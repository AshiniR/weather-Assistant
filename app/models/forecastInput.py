from pydantic import BaseModel, Field

class ForecastInput(BaseModel):
    location: str = Field(description="City and optionally country, e.g., 'London, UK'")
    days: int = Field(description="Number of days (1-7)", ge=1, le=7)