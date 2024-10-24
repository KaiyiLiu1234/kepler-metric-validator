from typing import NamedTuple, List, Set
import psutil
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
import matplotlib.pyplot as plt
import os

class DataPoint(NamedTuple):
    timestamp: int
    value: float

class QueryRange(NamedTuple):
    query: str
    values: List[DataPoint]

    def __str__(self):
        return f"query: {self.query}, values: {self.values}"

# I should redirect these classes to a separate module
class ValidationResult(NamedTuple):
    predicted_query_name: str
    predicted: List[float]
    actual_query_name: str
    actual: List[float]  


class ErrorResult:
    mape: float
    mae: float

    def __init__(self, v: ValidationResult):
        self.mape = mean_absolute_percentage_error(v.actual, v.predicted)
        self.mae = mean_absolute_error(v.actual, v.predicted)


class GraphedResult:
    save_path: str
    predicted: List[float]
    actual: List[float]
    predicted_name: str
    actual_name: str
    
    def __init__(self, v: ValidationResult, save_path=""):
        self.save_path = save_path
        self.predicted = v.predicted
        self.actual = v.actual
        self.predicted_name = v.predicted_query_name
        self.actual_name = v.actual_query_name
    
    def generate_graph(self, show_plt=False):
        plt.plot(self.predicted, label=f"{self.predicted_name}", color="red")
        plt.plot(self.actual, label=f"{self.actual_name}", color="blue")
        plt.title("Baremetal Validation Result")
        plt.xlabel("Datapoints")
        plt.ylabel("CPU Time in seconds")
        plt.legend()
        expanded_save_path = os.path.expanduser(self.save_path)
        filepath = os.path.join(expanded_save_path, "Baremtal_CPU_Time_Validation.png")
        if self.save_path:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')

        if show_plt:
            plt.show()


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