from pydantic import BaseModel, Field

class ClothingInput(BaseModel):
    location: str = Field(description="City and optionally country, e.g., 'Berlin, Germany'")