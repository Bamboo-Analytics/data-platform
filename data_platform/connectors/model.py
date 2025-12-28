from pydantic import BaseModel
from datetime import datetime

class OHLCV(BaseModel):
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
class 