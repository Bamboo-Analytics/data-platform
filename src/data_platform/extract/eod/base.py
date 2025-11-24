from abc import ABC, abstractmethod
import polars as pl

class BaseEOD:

    def __init__(self):
        pass

    @abstractmethod
    def get_historical_price(
        self, 
        ticker : str, 
        period : str = "max", 
        start : str | None = None, 
        end : str | None = None
        ) -> pl.DataFrame:
        
        pass

    