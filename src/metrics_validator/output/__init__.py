from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
import matplotlib.pyplot as plt
from validation import ValidationResult
from typing import List
import os

# everything below should be output package
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
        self.predicted_name = v.vq.predicted_query_name
        self.actual_name = v.vq.actual_query_name
    
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