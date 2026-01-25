from sqlalchemy.orm import Session
from typing import List
from app.db.models import Channel

def get_channels(db: Session) -> List[Channel]:
    return db.query(Channel).order_by(Channel.id).all()
