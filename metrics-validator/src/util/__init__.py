from typing import NamedTuple, List, Set
import psutil

class DataPoint(NamedTuple):
    timestamp: int
    value: float

class QueryRange(NamedTuple):
    query: str
    values: List[DataPoint]

    def __str__(self):
        return f"query: {self.query}, values: {self.values}"
    
def calculate_mape(actual: List[float], predicted: List[float]):
    if len(actual) != len(predicted):
        raise ValueError("The length of actual and forecast lists must be the same.")
    
    n = len(actual)
    mape = sum(abs((a - f) / a) for a, f in zip(actual, predicted) if a != 0) / n * 100
    
    return mape

def calculate_mae(actual, predicted):
    if len(actual) != len(predicted):
        raise ValueError("The length of actual and predicted lists must be the same.")
    
    n = len(actual)
    mae = sum(abs(a - p) for a, p in zip(actual, predicted)) / n
    
    return mae


    
class ValidationResult:
    predicted_query_name: str
    predicted: List[float]
    actual_query_name: str
    actual: List[float]
    mape: float
    mae: float

    def __init__(self, predicted_query_name: str, actual_query_name: str, predicted: List[float], actual: List[float]):
        self.predicted_query_name = predicted_query_name
        self.actual_query_name = actual_query_name
        self.predicted = predicted
        self.actual = actual
        self.mape = calculate_mape(self.actual, self.predicted)
        self.mae = calculate_mae(self.actual, self.predicted)


class GraphedValidationResult:
    pass
            
    
def common_timestamps(range_one: QueryRange, range_two: QueryRange) -> Set[int]:
    timestamps_one = set([range_one_val.timestamp for range_one_val in range_one.values])
    timestamps_two = set(range_two_val.timestamp for range_two_val in range_two.values)
    timestamps = timestamps_one.intersection(timestamps_two)
    return timestamps

def return_child_pids(parent_pid: int) -> List[int]:
    try:
        parent_process = psutil.Process(parent_pid)
        children_processes = parent_process.children(recursive=True)
        return [child_process.pid for child_process in children_processes]
    except psutil.NoSuchProcess:
        return []