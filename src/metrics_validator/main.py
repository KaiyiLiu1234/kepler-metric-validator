from process.power import NodeExporter
from output import ErrorResult, GraphedResult
from prometheus import PromConnect, PromConfig
from validation import ValidationConfig, ValidationQuery
from stresser import StressProcessConfig

# everything here should be in cli
if __name__ == "__main__":

    pc = PromConfig(url="http://localhost:9090/", disable_ssl=True)
    prom = PromConnect(pc)
    vq = ValidationQuery(
        actual_query_name="doesntmatterrn",
        predicted_query_name="doesntmatterrnpredicted"
    )
    sc = StressProcessConfig(
        isolated_cpus=["15"],
        stress_load=25,
        stresser_timeout=120
    )
    vc = ValidationConfig(
        vq=vq,
        rate_interval='20s',
        sc=sc
    )
    v = NodeExporter(
        prom=prom,
        vc=vc
    )
    result = v.validate()
    
    e = ErrorResult(result)
    print(e.mae)
    print(e.mape)
    g = GraphedResult(result, "~/Downloads")
    g.generate_graph(True)
    