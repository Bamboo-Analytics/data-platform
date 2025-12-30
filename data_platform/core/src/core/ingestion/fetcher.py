# from typing import Generic, TypeVar

# from pandas.core.dtypes.concat import ABCCategoricalIndex
# from data_platform.core.models import QueryParams, RawData, StandardizedData
# from abc import abstractmethod
# from typing import TypeVar, Type

from core.models.abstract import QueryParams, QueryResponse
from pydantic import BaseModel
from typing import Any

class Fetcher[P : QueryParams, R : QueryResponse]:

    @classmethod
    def query_type(cls) -> type[P]:
        return cls.__orig_bases__[0].__args__[0]

    @classmethod
    def response_type(cls) -> type[R]:
        return cls.__orig_bases__[0].__args__[1]

    @classmethod
    def _validate_query(cls, params: dict[str, Any]) -> P:
        return cls.query_type()(**params)

    @classmethod
    def _extract_response(cls, params: dict[str, Any]) -> list[dict]:
        raise NotImplementedError("Provider specific extraction not implemented")

    @classmethod
    def _validate_response(cls, response: list[dict]) -> list[R]:
        model = cls.response_type()
        return [model(**row) for row in response]

    @classmethod
    def fetch(cls, params: dict[str, Any]) -> list[R]:
        validated_params = cls._validate_query(params)
        raw_response = cls._extract_response(validated_params)
        return cls._validate_response(raw_response)

