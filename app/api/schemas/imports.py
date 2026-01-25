from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ImportRunOut(BaseModel):
    id: int
    channel_id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
