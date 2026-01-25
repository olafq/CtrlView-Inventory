from pydantic import BaseModel

class ChannelOut(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        orm_mode = True
