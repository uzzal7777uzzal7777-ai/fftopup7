import os, re, secrets, hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./alpha_topup.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass
class Order(Base):
    __tablename__ = "orders"
    order_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    game: Mapped[str] = mapped_column(String(20))
    player_id: Mapped[str] = mapped_column(String(25))
    region: Mapped[str] = mapped_column(String(80))
    package_amount: Mapped[int] = mapped_column(Integer)
    price_bdt: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String(40))
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="awaiting_payment")
    provider_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ALPHA TOP UP API", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type","X-Admin-Token"])

CATALOG = {
    "ff": {"name":"Free Fire", "amounts":{100:80,310:240,520:400,1060:800,2180:1600,5600:3900}},
    "pubg":{"name":"PUBG Mobile", "amounts":{60:80,325:400,660:800,1800:2000,3850:4000,8100:8000}}
}
class OrderCreate(BaseModel):
    game: str
    player_id: str = Field(min_length=5, max_length=25, pattern=r"^[a-zA-Z0-9-]+$")
    region: str = Field(min_length=1, max_length=80)
    package_amount: int = Field(gt=0)
    price_bdt: int = Field(gt=0)
    payment_method: str = Field(min_length=1, max_length=40)
    payment_reference: Optional[str] = Field(default=None, max_length=100)

class PaymentUpdate(BaseModel):
    payment_reference: str = Field(min_length=4, max_length=100)
class StatusUpdate(BaseModel):
    status: str
    provider_reference: Optional[str] = Field(default=None, max_length=100)

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def require_admin(x_admin_token: Optional[str] = Header(default=None)):
    token=os.getenv("ADMIN_TOKEN","")
    if len(token)<24:
        raise HTTPException(503,"Admin is not configured. Set a strong ADMIN_TOKEN environment variable.")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, token):
        raise HTTPException(401,"Invalid admin token.")
    return True

@app.get("/")
def root(): return {"service":"ALPHA TOP UP API","status":"ok","docs":"/docs"}
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/api/catalog")
def catalog():
    return [{"game":g,"name":d["name"],"packages":[{"amount":a,"price_bdt":p} for a,p in d["amounts"].items()]} for g,d in CATALOG.items()]

@app.post("/api/orders", status_code=201)
def create_order(body: OrderCreate, db: Session=Depends(get_db)):
    if body.game not in CATALOG: raise HTTPException(400,"Unsupported game.")
    expected=CATALOG[body.game]["amounts"].get(body.package_amount)
    if expected is None or expected != body.price_bdt:
        raise HTTPException(400,"Package or price mismatch. Refresh the page and try again.")
    if body.payment_method not in ("bKash","Nagad","Discuss with store"):
        raise HTTPException(400,"Unsupported payment method.")
    order_id="ALP-"+secrets.token_hex(6).upper()
    order=Order(order_id=order_id,game=body.game,player_id=body.player_id,region=body.region,
                package_amount=body.package_amount,price_bdt=expected,payment_method=body.payment_method,
                payment_reference=body.payment_reference,status="awaiting_payment")
    db.add(order);db.commit()
    return {"order_id":order.order_id,"status":order.status,"message":"Order request created. Payment must be verified by the store before fulfillment."}

@app.get("/api/orders/{order_id}")
def get_order(order_id: str, db: Session=Depends(get_db)):
    if not re.fullmatch(r"ALP-[A-F0-9]{12}",order_id): raise HTTPException(404,"Order not found.")
    o=db.get(Order,order_id)
    if not o: raise HTTPException(404,"Order not found.")
    # Public endpoint exposes only status and order details required for tracking.
    return {"order_id":o.order_id,"game":CATALOG[o.game]["name"],"package_amount":o.package_amount,
            "player_id":o.player_id,"region":o.region,"price_bdt":o.price_bdt,"status":o.status,
            "created_at":o.created_at.isoformat() if o.created_at else None}

@app.post("/api/admin/orders/{order_id}/payment-reference", dependencies=[Depends(require_admin)])
def set_payment_reference(order_id: str, body: PaymentUpdate, db: Session=Depends(get_db)):
    o=db.get(Order,order_id)
    if not o: raise HTTPException(404,"Order not found.")
    o.payment_reference=body.payment_reference;o.status="payment_submitted";db.commit()
    return {"order_id":o.order_id,"status":o.status}

@app.post("/api/admin/orders/{order_id}/status", dependencies=[Depends(require_admin)])
def set_status(order_id: str, body: StatusUpdate, db: Session=Depends(get_db)):
    allowed={"awaiting_payment","payment_submitted","paid_verified","processing","completed","failed","refunded"}
    if body.status not in allowed: raise HTTPException(400,"Invalid status.")
    o=db.get(Order,order_id)
    if not o: raise HTTPException(404,"Order not found.")
    # No status change triggers a top-up automatically in this starter.
    # Connect a real provider only after payment verification and provider-specific safeguards.
    o.status=body.status
    if body.provider_reference:o.provider_reference=body.provider_reference
    db.commit()
    return {"order_id":o.order_id,"status":o.status}

@app.get("/api/admin/orders", dependencies=[Depends(require_admin)])
def admin_orders(limit: int=50, db: Session=Depends(get_db)):
    limit=max(1,min(limit,100))
    rows=db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
    return [{"order_id":o.order_id,"game":o.game,"player_id":o.player_id,"package_amount":o.package_amount,
             "price_bdt":o.price_bdt,"payment_method":o.payment_method,"payment_reference":o.payment_reference,
             "status":o.status,"created_at":o.created_at.isoformat() if o.created_at else None} for o in rows]

# Provider adapter intentionally not implemented: add the official provider's documented API,
# signature verification, idempotency and retry rules here. Never mark an order completed
# solely because a browser claims payment succeeded.
