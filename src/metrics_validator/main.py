import process.power as p
import process.cpu_time as ct
from output import ErrorResult, GraphedResult
from prometheus import PromConnect, PromConfig
from validation import ValidationConfig, ValidationQuery
from stresser import StressProcessConfig, Local
from container.one_to_one import ContainerValidator
import asyncio

# everything here should be in cli
if __name__ == "__main__":

    pc = PromConfig(url="http://localhost:9091/", disable_ssl=True)
    prom = PromConnect(pc)
    vq = ValidationQuery(
        actual_query_name="actual process power",
        predicted_query_name="process power predicted"
    )
    sc = StressProcessConfig(
        isolated_cpus=["15"],
        stress_load=100,
        stresser_timeout=120
    )
    vc = ValidationConfig(
        vq=vq,
        rate_interval='20s',
        sc=sc
    )
    # v = NodeExporter(
    #     prom=prom,
    #     vc=vc
    # )
    l = Local(
            isolated_cpu="5",
            #load_curve="0:20,25:20,50:20,75:20,50:20,25:20,0:20",
            #load_curve="0:20,25:30,50:30,75:30,100:30,75:30,50:30,25:30,0:20",
            load_curve="0:20,50:30,100:30,50:30,0:20",
            mount_dir="/tmp",
            container_name="",
            iterations="2"
        )
    v = p.NodeExporter(
        prom=prom,
        vc=vc,
        config=l
    )
    result = v.validate()
    e = ErrorResult(result)
    print(e.mae)
    print(e.mape)
    g = GraphedResult(result, "~/Downloads")
    g.generate_graph(True)

    # sc = StressContainerConfig(
    #     isolated_cpus=["15"],
    #     stress_script="stress_script.sh",
    #     container_name="kepler-stress-test-container"
    # )
    # vcontainer = ContainerValidator(
    #     prom=prom,
    #     sc=sc
    # )
    # result = asyncio.run(vcontainer.validate())

    # e = ErrorResult(result)
    # print(e.mae)
    # print(e.mape)
    # g = GraphedResult(result, "~/Downloads")
    # g.generate_graph(True)