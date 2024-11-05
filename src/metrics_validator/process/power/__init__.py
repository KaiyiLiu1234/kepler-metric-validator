from prometheus import PromConnect
from stresser import StressProcess
from validation import Validator, ValidationConfig, ValidationResult, QueryRange, DataPoint, common_timestamps, keep_timestamps
from datetime import datetime
from typing import Iterable
import subprocess

class TurboStat(Validator):
    pass

class NodeExporter(Validator):
    def __init__(self, prom: PromConnect, vc: ValidationConfig):
        self.prom = prom
        self.validation_query = vc.vq
        self.rate_interval = vc.rate_interval
        self.stress_process = StressProcess(vc.sc)

    def validate(self) -> ValidationResult:
        try:
            stress_output = self.stress_process.stress()
            cpu_time_ratio = self._retrieve_target_cpu_time_ratio(stress_output.start_time, 
                                                                             stress_output.end_time, 
                                                                             stress_output.child_pids)
            power_ratio = self._retrieve_target_power_ratio(stress_output.start_time, stress_output.end_time, stress_output.child_pids)

            common_timestamp_set = common_timestamps(cpu_time_ratio, power_ratio)
            cpu_time_ratio = keep_timestamps(common_timestamp_set, cpu_time_ratio)
            power_ratio = keep_timestamps(common_timestamp_set, power_ratio)
            return ValidationResult(
                vq=self.validation_query,
                predicted=[datapoint.value for datapoint in cpu_time_ratio.values],
                actual=[datapoint.value for datapoint in power_ratio.values]
            )

        except subprocess.CalledProcessError as e:
            print(f"Stress failed: {e}")

    # convert bottom methods into a single reusable one
    def _retrieve_target_cpu_time_ratio(self, start: datetime, end: datetime, target_pids: Iterable[int]) -> QueryRange:
        pid_label = "|".join(map(str, target_pids))
        target_query = f'sum(rate(kepler_process_bpf_cpu_time_ms_total{{pid=~"{pid_label}"}}[{self.rate_interval}]))'
        total_query = f'sum(rate(kepler_process_bpf_cpu_time_ms_total[{self.rate_interval}]))'
        print(target_query)
        print(total_query)
        target_cpu_time = self.prom.get_metric_range(
            query=target_query,
            start=start,
            end=end
        )
        total_cpu_time = self.prom.get_metric_range(
            query=total_query,
            start=start,
            end=end
        )
        common_timestamps_set = common_timestamps(target_cpu_time, total_cpu_time)
        target_cpu_time = keep_timestamps(common_timestamps_set, target_cpu_time)
        total_cpu_time = keep_timestamps(common_timestamps_set, total_cpu_time)

        ratio_datapoints = [DataPoint(datapoint.timestamp, datapoint.value / (total_cpu_time.values)[index].value) for index, datapoint in enumerate(target_cpu_time.values)]
        ratio = QueryRange(
            query=f"{target_cpu_time.query} / {total_cpu_time.query}",
            values = ratio_datapoints
        )
        return ratio

    def _retrieve_target_power_ratio(self, start: datetime, end: datetime, target_pids: Iterable[int]) -> QueryRange:
        pid_label = "|".join(map(str, target_pids))
        target_query = f'sum(rate(kepler_process_package_joules_total{{pid=~"{pid_label}"}}[{self.rate_interval}]))'
        total_query = f'sum(rate(kepler_process_package_joules_total[{self.rate_interval}]))'
        print(target_query)
        print(total_query)
        target_power = self.prom.get_metric_range(
            query=target_query,
            start=start,
            end=end
        )
        total_power = self.prom.get_metric_range(
            query=total_query,
            start=start,
            end=end
        )
        common_timestamps_set = common_timestamps(target_power, total_power)
        target_power = keep_timestamps(common_timestamps_set, target_power)
        total_power = keep_timestamps(common_timestamps_set, total_power)

        ratio_datapoints = [DataPoint(datapoint.timestamp, datapoint.value / (total_power.values)[index].value) for index, datapoint in enumerate(target_power.values)]
        ratio = QueryRange(
            query=f"{target_power.query} / {total_power.query}",
            values = ratio_datapoints
        )
        return ratio


class Scaphandre(Validator):
    def __init__(self, prom: PromConnect, vc: ValidationConfig):
        self.prom = prom
        self.validation_query = vc.vq
        self.rate_interval = vc.rate_interval
        self.stress_process = StressProcess(vc.sc)

    def validate(self) -> ValidationResult:
        try: 
            stress_output = self.stress_process.stress()
            kepler_process_power = self._retrieve_kepler(stress_output.start_time, 
                                                                             stress_output.end_time, 
                                                                             stress_output.child_pids)
            scaph_process_power = self._retrieve_scaph(stress_output.start_time, stress_output.end_time, stress_output.child_pids)

            common_timestamp_set = common_timestamps(kepler_process_power, scaph_process_power)
            kepler_process_power = keep_timestamps(common_timestamp_set, kepler_process_power)
            scaph_process_power = keep_timestamps(common_timestamp_set, scaph_process_power)

            return ValidationResult(
                predicted_query_name=kepler_process_power.query,
                actual_query_name=scaph_process_power.query,
                predicted=[datapoint.value for datapoint in kepler_process_power.values],
                actual=[datapoint.value for datapoint in scaph_process_power.values]
            )
        except subprocess.CalledProcessError as e:
            print(f"Stress failed: {e}")

    def _retrieve_kepler(self, start: datetime, end: datetime, target_pids: Iterable[int]) -> QueryRange:
        pid_label = "|".join(map(str, target_pids))
        query = f'sum(rate(kepler_process_package_joules_total{{pid=~"{pid_label}"}}[{self.rate_interval}])) * 1000'
        return self.prom.get_metric_range(
            query=query,
            start=start,
            end=end
        )

    def _retrieve_scaph(self, start: datetime, end: datetime, target_pids: Iterable[int]) -> QueryRange:
        pid_label = "|".join(map(str, target_pids))
        #query = f'sum(rate(node_cpu_seconds_total{{cpu="{self.isolated_cpu}", mode!~"idle|system"}}[{self.rate_interval}])) * 1000'
        query = f'sum(rate(scaph_process_power_consumption_microwatts{{pid=~"{pid_label}"}}[{self.rate_interval}]))'
        return self.prom.get_metric_range(
            query=query,
            start=start,
            end=end
        )