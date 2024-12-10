from prometheus import PromConnect
from stresser import Process, Local
from validation import Validator, ValidationConfig, ValidationResult, ValidationQuery, QueryRange, DataPoint, common_timestamps, keep_timestamps
from datetime import datetime
from typing import Iterable
import subprocess

class TurboStat(Validator):
    pass

class NodeExporter(Validator):
    def __init__(self, prom: PromConnect, vc: ValidationConfig, config: Local):
        self.prom = prom
        self.validation_query = vc.vq
        self.rate_interval = vc.rate_interval
        self.stress_process = Process(
            config=config
        )
    def validate(self) -> ValidationResult:
        try:
            stress_output = self.stress_process.stress()
            cpu_time_ratio = self._retrieve_target_cpu_time_ratio(stress_output.script_result.start_time, 
                                                                             stress_output.script_result.end_time, 
                                                                             stress_output.relevant_pids)
            # cpu ratio time and multiply with total node exporter power
            #power_ratio = self._retrieve_target_power_ratio(stress_output.start_time, stress_output.end_time, stress_output.child_pids)
            total_node_rapl_power = self._retrieve_node_rapl_power(stress_output.script_result.start_time, stress_output.script_result.end_time)
            process_rapl_power = self._retrieve_target_process_package_power(stress_output.script_result.start_time, stress_output.script_result.end_time, stress_output.relevant_pids)
            print(len(total_node_rapl_power.values))
            print(len(cpu_time_ratio.values))
            print(len(process_rapl_power.values))
            common_timestamp_set = common_timestamps(cpu_time_ratio, total_node_rapl_power)
            cpu_time_ratio = keep_timestamps(common_timestamp_set, cpu_time_ratio)
            node_rapl_power = keep_timestamps(common_timestamp_set, total_node_rapl_power)
            process_kepler_power = keep_timestamps(common_timestamp_set, process_rapl_power)
            expected_rapl_power = []
            for ratio, node_power in zip(cpu_time_ratio.values, node_rapl_power.values):
                timestamp = ratio.timestamp
                process_power = ratio.value * node_power.value
                expected_rapl_power.append(DataPoint(
                    timestamp=timestamp,
                    value = process_power
                ))
            print("TOTAL POWER RATIO")
            pid_label = "|".join(map(str, stress_output.relevant_pids))
            target_query = f'sum(rate(kepler_process_bpf_cpu_time_ms_total{{pid=~"{pid_label}"}}[{self.rate_interval}]))'
            total_query = f'sum(rate(kepler_process_bpf_cpu_time_ms_total[{self.rate_interval}]))'
            node_rapl_query = f'sum(rate(node_rapl_package_joules_total{{path="{"/host/sys/class/powercap/intel-rapl:0"}"}}[{self.rate_interval}]))'
            test2 = self.prom.get_metric_range(
                query=f"({target_query} / {total_query}) * {node_rapl_query}",
                start=stress_output.script_result.start_time,
                end=stress_output.script_result.end_time
            )
            for val1, val2 in zip(expected_rapl_power, test2.values):
                print(val1.timestamp == val2.timestamp, val1.value == val2.value)
            print("--------------------------------")
            process_power_qr = QueryRange("expected package power process", expected_rapl_power)
            new_vq = ValidationQuery(
                actual_query_name=process_power_qr.query,
                predicted_query_name=process_kepler_power.query
            )
            return ValidationResult(
                vq=new_vq,
                predicted=[datapoint.value for datapoint in process_kepler_power.values],
                actual=[datapoint.value for datapoint in process_power_qr.values]
            )

        except subprocess.CalledProcessError as e:
            print(f"Stress failed: {e}")

    def _retrieve_node_rapl_power(self, start: datetime, end:datetime) -> QueryRange:
        query = f'sum(rate(node_rapl_package_joules_total{{path="{"/host/sys/class/powercap/intel-rapl:0"}"}}[{self.rate_interval}]))'
        target_node_power = self.prom.get_metric_range(
            query=query,
            start=start,
            end=end
        )
        return target_node_power
    
    def _retrieve_target_process_package_power(self, start: datetime, end: datetime, target_pids: Iterable[int]) -> QueryRange:
        pid_label = "|".join(map(str, target_pids))
        target_query = f'sum(rate(kepler_process_package_joules_total{{pid=~"{pid_label}"}}[{self.rate_interval}]))'
        print(target_query)
        target_power = self.prom.get_metric_range(
            query=target_query,
            start=start,
            end=end
        )
        return target_power

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

        test = self.prom.get_metric_range(
            query=f"{target_query} / {total_query}",
            start=start,
            end=end
        )
        print("OUR TEST VALS")
        
        for val in test.values:
            print(val.timestamp, val.value)
        print("-----------------")

        # print("TOTAL POWER RATIO")
        # node_rapl_query = f'sum(rate(node_rapl_package_joules_total{{path="{"/host/sys/class/powercap/intel-rapl:0"}"}}[{self.rate_interval}]))'
        # test2 = self.prom.get_metric_range(
        #     query=f"({target_query} / {total_query}) * {node_rapl_query}",
        #     start=start,
        #     end=end
        # )
        # for val1, val2 in zip(test.values, test2.values):
        #     print(val1.timestamp == val2.timestamp, val1.value == val2.value)
        # print("--------------------------------")

        common_timestamps_set = common_timestamps(target_cpu_time, total_cpu_time)
        target_cpu_time = keep_timestamps(common_timestamps_set, target_cpu_time)
        total_cpu_time = keep_timestamps(common_timestamps_set, total_cpu_time)

        ratio_datapoints = [DataPoint(datapoint.timestamp, datapoint.value / (total_cpu_time.values)[index].value) for index, datapoint in enumerate(target_cpu_time.values)]
        ratio = QueryRange(
            query=f"{target_cpu_time.query} / {total_cpu_time.query}",
            values = ratio_datapoints
        )
        print("OUR ACTUAL VALS")
        for val in ratio.values:
            print(val.timestamp, val.value)
        print("------------------------")

        return ratio

    # def _retrieve_target_power_ratio(self, start: datetime, end: datetime, target_pids: Iterable[int]) -> QueryRange:
    #     pid_label = "|".join(map(str, target_pids))
    #     target_query = f'sum(rate(kepler_process_package_joules_total{{pid=~"{pid_label}"}}[{self.rate_interval}]))'
    #     total_query = f'sum(rate(kepler_process_package_joules_total[{self.rate_interval}]))'
    #     print(target_query)
    #     print(total_query)
    #     target_power = self.prom.get_metric_range(
    #         query=target_query,
    #         start=start,
    #         end=end
    #     )
    #     total_power = self.prom.get_metric_range(
    #         query=total_query,
    #         start=start,
    #         end=end
    #     )
    #     common_timestamps_set = common_timestamps(target_power, total_power)
    #     target_power = keep_timestamps(common_timestamps_set, target_power)
    #     total_power = keep_timestamps(common_timestamps_set, total_power)

    #     ratio_datapoints = [DataPoint(datapoint.timestamp, datapoint.value / (total_power.values)[index].value) for index, datapoint in enumerate(target_power.values)]
    #     ratio = QueryRange(
    #         query=f"{target_power.query} / {total_power.query}",
    #         values = ratio_datapoints
    #     )
    #     return ratio


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