import subprocess
from datetime import datetime
import time
from typing import NamedTuple, Set, List
from util import return_child_pids

class StressProcessConfig(NamedTuple):
    isolated_cpus: List[str]
    stress_load: int
    stresser_timeout: int

class StressProcessOutput(NamedTuple):
    start_time: datetime
    end_time: datetime
    child_pids: Set[int]

class StressProcess:
    def __init__(self, sc: StressProcessConfig):
        self.isolated_cpus = sc.isolated_cpus
        self.stress_load = sc.stress_load
        self.stresser_timeout = sc.stresser_timeout
        self.generate_new_stress_command()
        print(self._stress_command)

    @property
    def stress_command(self) -> str:
        return self._stress_command
    
    def generate_new_stress_command(self) -> None:
        cpus = ",".join(self.isolated_cpus)
        cpu_num = len(self.isolated_cpus)
        if self.stresser_timeout < 12:
            raise Exception("Stresser timeout should be at least 12 seconds")
        self._stress_command = f"taskset -c {cpus} stress-ng --cpu {cpu_num} --cpu-load {self.stress_load} --cpu-method ackermann --timeout {self.stresser_timeout}s"

    def stress(self):
        start_time = datetime.now()
        target_popen = subprocess.Popen(self.stress_command, shell=True)
        time.sleep(1)
        target_process_pid = target_popen.pid
        all_child_pids = set([target_process_pid])
        while target_popen.poll() is None:
            child_pids = return_child_pids(target_process_pid)
            all_child_pids = all_child_pids.union(child_pids)
            time.sleep(1)
        end_time = datetime.now()
        
        return StressProcessOutput(
            start_time=start_time,
            end_time=end_time,
            child_pids=all_child_pids
        )