from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.modules.integrations.mercadolibre.service import process_ml_notification

router = APIRouter(prefix="/webhooks/ml", tags=["Webhooks"])

@router.post("/notify")
async def ml_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    data = await request.json()
    
    # ML envía: {"resource": "/orders/123", "user_id": 456, "topic": "orders", ...}
    topic = data.get("topic")
    
    if topic in ["orders", "orders_v2"]:
        # Lo procesamos en segundo plano para responder '200' rápido a ML
        background_tasks.add_task(process_ml_notification, data, db)
    
    return {"status": "received"}