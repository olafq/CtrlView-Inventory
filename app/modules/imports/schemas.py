from pydantic import BaseModel
from datetime import datetime

class ImportRunOut(BaseModel):
    id: int
    channel_id: int
    status: str
    started_at: datetime

    class Config:
        orm_mode = True
