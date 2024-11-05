from typing import NamedTuple, List, Iterable, Set
from abc import ABC, abstractmethod
from stresser import StressProcessConfig

# everything below should be in validation module
class DataPoint(NamedTuple):
    timestamp: int
    value: float

class QueryRange(NamedTuple):
    query: str
    values: List[DataPoint]

    def __str__(self) -> str:
        return f"query: {self.query}, values: {self.values}"

class ValidationQuery(NamedTuple):
    actual_query_name: str
    predicted_query_name: str
    
class ValidationConfig(NamedTuple):
    vq: ValidationQuery
    sc: StressProcessConfig
    rate_interval: str

class ValidationResult(NamedTuple):
    vq: ValidationQuery
    predicted: List[float]
    actual: List[float]

class Validator(ABC):
    @abstractmethod
    def validate(self) -> ValidationResult:
        """Validate Target Metrics"""
        pass

def common_timestamps(range_one: QueryRange, range_two: QueryRange) -> Set[int]:
    timestamps_one = set([range_one_val.timestamp for range_one_val in range_one.values])
    timestamps_two = set(range_two_val.timestamp for range_two_val in range_two.values)
    timestamps = timestamps_one.intersection(timestamps_two)
    return timestamps

def keep_timestamps(timestamps: Iterable[int], query_range: QueryRange) -> QueryRange:
    aligned_range = [DataPoint(datapoint.timestamp, datapoint.value) for datapoint in query_range.values if datapoint.timestamp in timestamps]
    aligned_range.sort(key=lambda datapoint: datapoint.timestamp)
    return QueryRange(query_range.query, aligned_range)