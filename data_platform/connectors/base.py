from abc import ABC, abstractmethod

class BaseConnector(ABC):

    def __init__(self):
        pass
    
    @abstractmethod
    def fetch(self, ticker : str, start_date : datetime, end_date : datetime, **kwargs):
        
    
    def 