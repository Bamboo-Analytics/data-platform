

from core.models.abstract import QueryResponse, Data

class Mapper[R : QueryResponse, D : Data]:

    @classmethod
    def map(cls) -> list[D]:
        raise NotImplementedError("Provider specific mapping not implemented")

    