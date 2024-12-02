from validation import QueryRange, ValidationConfig, Validator, ValidationResult, common_timestamps, keep_timestamps
from prometheus import PromConnect
from stresser import Process, Local
import subprocess
from datetime import datetime
from typing import Iterable


class NodeExporter(Validator):
    def __init__(self, prom: PromConnect, vc: ValidationConfig): #rate_interval="20s", #prom_url="http://localhost:9090", isolated_cpu=15, stress_load=100, stresser_timeout=120):
        self.prom = prom
        self.validation_query = vc.vq
        self.rate_interval = vc.rate_interval
        self.isolated_cpus = vc.sc.isolated_cpus
        #self.stress_process = StressProcess(vc.sc)
        l = Local(
            isolated_cpu="5",
            #load_curve="0:20,25:20,50:20,75:20,50:20,25:20,0:20",
            load_curve="0:20,25:30,50:30,75:30,100:30,75:30,50:30,25:30,0:20",
            mount_dir="/tmp",
            container_name="",
            iterations="1"
        )
        self.stress_process = Process(
            config=l
        )

    def validate(self) -> ValidationResult:
        try: 
            stress_output = self.stress_process.stress()
            kepler_process_cpu_time = self._retrieve_kepler_process_cpu_time(stress_output.script_result.start_time, stress_output.script_result.end_time, stress_output.relevant_pids)
            node_exporter_cpu_time = self._retrieve_node_cpu_time(stress_output.script_result.start_time, stress_output.script_result.end_time)
            # logic makes sense to always sum it
            common_timestamp_set = common_timestamps(kepler_process_cpu_time, node_exporter_cpu_time)
            kepler_process_cpu_time = keep_timestamps(common_timestamp_set, kepler_process_cpu_time)
            node_exporter_cpu_time = keep_timestamps(common_timestamp_set, node_exporter_cpu_time)
            # aligned_kepler_process_cpu_time_datapoints = [DataPoint(datapoint.timestamp, datapoint.value) for datapoint in kepler_process_cpu_time.values if datapoint.timestamp in common_timestamp_set]
            # aligned_kepler_process_cpu_time_datapoints.sort(key=lambda datapoint: datapoint.timestamp)
            # kepler_process_cpu_time = QueryRange(kepler_process_cpu_time.query, aligned_kepler_process_cpu_time_datapoints)

            # aligned_kepler_node_cpu_time_datapoints = [DataPoint(datapoint.timestamp, datapoint.value) for datapoint in node_exporter_cpu_time.values if datapoint.timestamp in common_timestamp_set]
            # aligned_kepler_node_cpu_time_datapoints.sort(key=lambda datapoint: datapoint.timestamp)

            # node_exporter_cpu_time = QueryRange(node_exporter_cpu_time.query, aligned_kepler_node_cpu_time_datapoints)
            print(kepler_process_cpu_time.values)
            print(node_exporter_cpu_time.values)
            return ValidationResult(
                vq=self.validation_query,
                predicted=[datapoint.value for datapoint in kepler_process_cpu_time.values],
                actual=[datapoint.value for datapoint in node_exporter_cpu_time.values]
            )
        except subprocess.CalledProcessError as e:
            print(f"Stress failed: {e}")

    def _retrieve_kepler_process_cpu_time(self, start: datetime, end: datetime, target_pids: Iterable[int]) -> QueryRange:
        pid_label = "|".join(map(str, target_pids))
        query = f'sum(rate(kepler_process_bpf_cpu_time_ms_total{{pid=~"{pid_label}"}}[{self.rate_interval}]))'
        print(query)
        return self.prom.get_metric_range(
            query=query,
            start=start,
            end=end
        )

    def _retrieve_node_cpu_time(self, start: datetime, end: datetime) -> QueryRange:
        #query = f'sum(rate(node_cpu_seconds_total{{cpu="{self.isolated_cpu}", mode!~"idle|system"}}[{self.rate_interval}])) * 1000'
        cpu_label = "|".join(map(str, "5"))
        query = f'sum(rate(node_cpu_seconds_total{{cpu=~"{cpu_label}", mode!="idle"}}[{self.rate_interval}])) * 1000'
        print(query)
        return self.prom.get_metric_range(
            query=query,
            start=start,
            end=end
        )