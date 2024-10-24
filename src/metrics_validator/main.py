from process.cpu_time.validate import ValidateCPUTime
from util import ErrorResult, GraphedResult

# everything here should be in cli
if __name__ == "__main__":
    v = ValidateCPUTime(
        stresser_timeout=60,
        stress_load=100
    )
    result = v.validate()
    
    e = ErrorResult(result)
    print(e.mae)
    print(e.mape)
    g = GraphedResult(result, "~/Downloads")
    g.generate_graph(True)
    