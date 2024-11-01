from util import QueryRange, DataPoint, ValidationResult, common_timestamps, return_child_pids
from prometheus import PromConnect
from stresser import StressProcessConfig
import subprocess
from datetime import datetime
import time
from typing import Iterable

class ValidateCPUTime:
    def __init__(self, rate_interval="20s", prom_url="http://localhost:9090", isolated_cpu=15, stress_load=100, stresser_timeout=120):
        self.prom = PromConnect(prom_url)
        self.rate_interval = rate_interval
        self.stress_process = StressProcessConfig(
            isolated_cpu=isolated_cpu,
            stress_load=stress_load,
            stresser_timeout=stresser_timeout
        )

    def validate(self) -> ValidationResult:
        try: 
            start_time = datetime.now()
            target_popen = subprocess.Popen(self.stress_process.stress_command, shell=True)
            time.sleep(1)
            target_process_pid = target_popen.pid
            all_child_pids = set([target_process_pid])
            while target_popen.poll() is None:
                child_pids = return_child_pids(target_process_pid)
                all_child_pids = all_child_pids.union(child_pids)
                time.sleep(1)
            end_time = datetime.now()
            print(all_child_pids)
            kepler_process_cpu_time = self._retrieve_kepler_process_cpu_time(start_time, end_time, all_child_pids)
            node_exporter_cpu_time = self._retrieve_node_cpu_time(start_time, end_time)

            common_timestamp_set = common_timestamps(kepler_process_cpu_time, node_exporter_cpu_time)
            aligned_kepler_process_cpu_time_datapoints = [DataPoint(datapoint.timestamp, datapoint.value) for datapoint in kepler_process_cpu_time.values if datapoint.timestamp in common_timestamp_set]
            aligned_kepler_process_cpu_time_datapoints.sort(key=lambda datapoint: datapoint.timestamp)
            kepler_process_cpu_time = QueryRange(kepler_process_cpu_time.query, aligned_kepler_process_cpu_time_datapoints)

            aligned_kepler_node_cpu_time_datapoints = [DataPoint(datapoint.timestamp, datapoint.value) for datapoint in node_exporter_cpu_time.values if datapoint.timestamp in common_timestamp_set]
            aligned_kepler_node_cpu_time_datapoints.sort(key=lambda datapoint: datapoint.timestamp)

            node_exporter_cpu_time = QueryRange(node_exporter_cpu_time.query, aligned_kepler_node_cpu_time_datapoints)
            
            return ValidationResult(
                predicted_query_name=kepler_process_cpu_time.query,
                actual_query_name=node_exporter_cpu_time.query,
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
        query = f'sum(rate(node_cpu_seconds_total{{cpu="{self.stress_process.isolated_cpu}", mode="user"}}[{self.rate_interval}])) * 1000'
        print(query)
        return self.prom.get_metric_range(
            query=query,
            start=start,
            end=end
        )