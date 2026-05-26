from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

# --- IMPORT THE AI PREDICTOR SERVICE ---
from ai_predictor import FinancePredictor

import auth
from database import Base, engine, get_db
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Backend API", version="0.1.0")


@app.get("/")
def health_check():
    return {"status": "ok", "service": "finance-backend"}



@app.get("/api/predict-spending")
def predict_spending():
    predictor = FinancePredictor()
    return predictor.predict_next_30_days()



@app.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(models.User)
        .filter(or_(models.User.username == payload.username, models.User.email == payload.email))
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=auth.get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username_or_email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    return schemas.Token(access_token=auth.create_access_token(str(user.id)))


@app.post("/token", response_model=schemas.Token)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    return schemas.Token(access_token=auth.create_access_token(str(user.id)))


def authenticate_user(db: Session, username_or_email: str, password: str) -> models.User | None:
    user = (
        db.query(models.User)
        .filter(
            or_(
                models.User.username == username_or_email,
                models.User.email == username_or_email,
            )
        )
        .first()
    )
    if user is None or not auth.verify_password(password, user.hashed_password):
        return None
    return user


@app.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.post("/categories", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    category = models.Category(
        user_id=current_user.id,
        name=payload.name,
        type=payload.type,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@app.get("/categories", response_model=list[schemas.CategoryRead])
def list_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.Category)
        .filter(models.Category.user_id == current_user.id)
        .order_by(models.Category.name.asc())
        .all()
    )


@app.post("/transactions", response_model=schemas.TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if payload.category_id is not None:
        category = (
            db.query(models.Category)
            .filter(
                models.Category.id == payload.category_id,
                models.Category.user_id == current_user.id,
            )
            .first()
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        if category.type != payload.type:
            raise HTTPException(status_code=400, detail="Category type does not match transaction type")

    transaction = models.Transaction(
        user_id=current_user.id,
        amount=payload.amount,
        type=payload.type,
        category_id=payload.category_id,
        note=payload.note,
        occurred_at=payload.occurred_at or models.utc_now(),
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@app.get("/transactions", response_model=list[schemas.TransactionRead])
def list_transactions(
    type: schemas.TransactionType | None = None,
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id)
    if type is not None:
        query = query.filter(models.Transaction.type == type)
    if start_date is not None:
        query = query.filter(models.Transaction.occurred_at >= start_date)
    if end_date is not None:
        query = query.filter(models.Transaction.occurred_at <= end_date)
    return query.order_by(models.Transaction.occurred_at.desc()).all()


@app.get("/transactions/summary", response_model=schemas.TransactionSummary)
def transaction_summary(
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id)
    if start_date is not None:
        query = query.filter(models.Transaction.occurred_at >= start_date)
    if end_date is not None:
        query = query.filter(models.Transaction.occurred_at <= end_date)

    rows = query.with_entities(
        models.Transaction.type,
        func.coalesce(func.sum(models.Transaction.amount), 0),
        func.count(models.Transaction.id),
    ).group_by(models.Transaction.type).all()

    income = sum(amount for transaction_type, amount, _ in rows if transaction_type == "income")
    expense = sum(amount for transaction_type, amount, _ in rows if transaction_type == "expense")
    count = sum(row_count for _, _, row_count in rows)
    return schemas.TransactionSummary(
        income=income,
        expense=expense,
        balance=income - expense,
        transaction_count=count,
    )


@app.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    transaction = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id,
            models.Transaction.user_id == current_user.id,
        )
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(transaction)
    db.commit()
    return None


@app.post("/predictions", response_model=schemas.PredictionRead, status_code=status.HTTP_201_CREATED)
def create_prediction(
    payload: schemas.PredictionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if payload.period_end <= payload.period_start:
        raise HTTPException(status_code=400, detail="period_end must be after period_start")
    prediction = models.Prediction(user_id=current_user.id, **payload.model_dump())
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


@app.get("/predictions", response_model=list[schemas.PredictionRead])
def list_predictions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.Prediction)
        .filter(models.Prediction.user_id == current_user.id)
        .order_by(models.Prediction.created_at.desc())
        .all()
    )


@app.post("/warnings", response_model=schemas.WarningRead, status_code=status.HTTP_201_CREATED)
def create_warning(
    payload: schemas.WarningCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    warning = models.Warning(user_id=current_user.id, **payload.model_dump())
    db.add(warning)
    db.commit()
    db.refresh(warning)
    return warning


@app.post(
    "/integrations/users/{user_id}/predictions",
    response_model=schemas.PredictionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth.verify_internal_api_key)],
)
def create_prediction_for_user(
    user_id: int,
    payload: schemas.PredictionCreate,
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.period_end <= payload.period_start:
        raise HTTPException(status_code=400, detail="period_end must be after period_start")
    prediction = models.Prediction(user_id=user_id, **payload.model_dump())
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


@app.post(
    "/integrations/users/{user_id}/warnings",
    response_model=schemas.WarningRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth.verify_internal_api_key)],
)
def create_warning_for_user(
    user_id: int,
    payload: schemas.WarningCreate,
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    warning = models.Warning(user_id=user_id, **payload.model_dump())
    db.add(warning)
    db.commit()
    db.refresh(warning)
    return warning


@app.get("/warnings", response_model=list[schemas.WarningRead])
def list_warnings(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Warning).filter(models.Warning.user_id == current_user.id)
    if unread_only:
        query = query.filter(models.Warning.is_read.is_(False))
    return query.order_by(models.Warning.created_at.desc()).all()


@app.patch("/warnings/{warning_id}/read", response_model=schemas.WarningRead)
def mark_warning_read(
    warning_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    warning = (
        db.query(models.Warning)
        .filter(models.Warning.id == warning_id, models.Warning.user_id == current_user.id)
        .first()
    )
    if warning is None:
        raise HTTPException(status_code=404, detail="Warning not found")
    warning.is_read = True
    db.commit()
    db.refresh(warning)
    return warning