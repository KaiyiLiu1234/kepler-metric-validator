from typing import List
import psutil

def return_child_pids(parent_pid: int) -> List[int]:
    try:
        parent_process = psutil.Process(parent_pid)
        children_processes = parent_process.children(recursive=True)
        return [child_process.pid for child_process in children_processes]
    except psutil.NoSuchProcess:
        return []