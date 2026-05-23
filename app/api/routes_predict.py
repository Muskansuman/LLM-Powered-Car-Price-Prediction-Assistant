from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_api_key, get_current_user
from app.core.rate_limit import limiter
from app.services.model_service import predict_car_price

router = APIRouter()


class CarFeatures(BaseModel):
    company: str
    year: int = Field(ge=1990, le=2030)
    owner: str
    fuel: str
    seller_type: str
    transmission: str
    km_driven: float = Field(ge=0)
    mileage_mpg: float = Field(ge=0)
    engine_cc: float = Field(ge=0)
    max_power_bhp: float = Field(ge=0)
    torque_nm: float = Field(ge=0)
    seats: float = Field(ge=1, le=15)


class PredictionResponse(BaseModel):
    predicted_price: float
    currency: str = "INR"
    formatted_price: str


@router.post("/predict", response_model=PredictionResponse)
@limiter.limit(settings.RATE_LIMIT_PREDICT)
def predict_price(
    request: Request,
    car: CarFeatures,
    user=Depends(get_current_user),
    _=Depends(get_api_key),
):
    prediction = predict_car_price(car.model_dump())
    return PredictionResponse(
        predicted_price=round(prediction, 2),
        formatted_price=f"\u20b9{prediction:,.2f}",
    )
