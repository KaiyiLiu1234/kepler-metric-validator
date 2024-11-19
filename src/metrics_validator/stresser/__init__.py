import subprocess
from datetime import datetime
import time
from typing import NamedTuple, Set, List
from util import return_child_pids
import docker
import asyncio
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class StressProcessConfig(NamedTuple):
    isolated_cpus: List[str]
    stress_load: int
    stresser_timeout: int

class StressProcessOutput(NamedTuple):
    start_time: datetime
    end_time: datetime
    child_pids: Set[int]

# pinned to isolated cpus
class StressContainerConfig(NamedTuple):
    isolated_cpus: List[str]
    stress_script: str
    container_name: str

# pinned to isolated cpus
class StressContainerOutput(NamedTuple):
    start_time: datetime
    end_time: datetime
    container_id: str

# pinned to isolated node
class StressKubeJobConfig(NamedTuple):
    node_name: str
    kube_config: str
    stress_script: str

class StressKubeJobOutput(NamedTuple):
    start_time: datetime
    end_time: datetime
    pod_ids: List[str]

class StressPod:
    def __init__(self, sc: StressKubeJobConfig):
        self.target_node = sc.node_name
        self.stress_script = sc.stress_script
        config.load_kube_config(sc.kube_config)
        self.generate_new_stress_command()

    @property
    def stress_command(self) -> str:
        return self._stress_command

    def generate_new_stress_command(self):
        self._stress_command = ["/bin/bash", "/app/stress_script.sh"]


    async def stress(self) -> str:
        # Define the Job with hostPath volume
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {"name": "kepler-stress-test"},
            "spec": {
                "backoffLimit": 0,
                "template": {
                    "metadata": {"labels": {"app": "stress-script"}},
                    "spec": {
                        "affinity": {
                            "nodeAffinity": {
                                "requiredDuringSchedulingIgnoredDuringExecution": {
                                    "nodeSelectorTerms": [
                                        {
                                            "matchExpressions": [
                                                {
                                                    "key": "kubernetes.io/hostname",
                                                    "operator": "In",
                                                    "values": [f"{self.target_node}"]  # Specify the node name here
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                        },
                        "containers": [
                            {
                                "name": "stress-container",
                                "image": "fedora:latest",  # or ubuntu:latest
                                "command": self.stress_command,  # Command to run the script
                                "volumeMounts": [
                                    {
                                        "mountPath": "/app",  # Path inside the container
                                        "name": "stress-script",  # The volume name
                                    }
                                ],
                            }
                        ],
                        "volumes": [
                            {
                                "name": "stress-script",  # Volume name
                                "hostPath": {
                                    "path": f"{self.stress_script}",  # Local path to the script
                                    "type": "File",
                                },
                            }
                        ],
                        "restartPolicy": "Never",
                    },
                },
            },
        }
        start_time = datetime.now()
        batch_v1 = client.BatchV1Api()
        try:
            response = batch_v1.create_namespaced_job(namespace="default", body=job_manifest)
            print("Job created. Status='%s'" % str(response.status))
        except ApiException as e:
            raise Exception(e)

        job_name = "kepler-stress-test"
        while True:
            job_status = batch_v1.read_namespaced_job_status(name=job_name, namespace="default")
            if job_status.status.succeeded:
                print("Job completed successfully!")
                break
            elif job_status.status.failed:
                print("Job failed.")
                break
            await asyncio.sleep(1)
        end_time = datetime.now()
        
        core_v1 = client.CoreV1Api()
        pods = core_v1.list_namespaced_pod(namespace="default", label_selector=f"job_name={job_name}")
        pod_ids = [pod.metadata.name for pod in pods.items]

        try:
            batch_v1.delete_namespaced_job(name=job_name, namespace="default", body=client.V1DeleteOptions())
            print(f"Job {job_name} deleted.")
        except ApiException as e:
            raise Exception(e)
        return StressKubeJobOutput(
            start_time=start_time,
            end_time=end_time,
            pod_ids=pod_ids
        )

class StressContainer:
    def __init__(self, sc: StressContainerConfig):
        self.isolated_cpus = sc.isolated_cpus
        self.stress_script = sc.stress_script
        self.container_name = sc.container_name
        self.client = docker.from_env()
        self.generate_new_stress_command()

    @property
    def stress_command(self) -> str:
        return self._stress_command

    def generate_new_stress_command(self):
        self._stress_command = f"bash -c 'dnf update && dnf install -y stress-ng && bash /app/stress_script.sh'"
        

    async def stress(self) -> StressContainerOutput:
        image = "fedora:latest"
        try:
            self.client.images.pull(image)
            start_time = datetime.now()
            stress_container = self.client.containers.run(
                image=image,
                name=self.container_name,
                command=self.stress_command,
                volumes={self.stress_script: {'bind': '/app/stress_script.sh', 'mode': 'ro'}},
                remove=False,
                detach=True

            )
            id = stress_container.id
            print(f"Container ID: {id}")
            while True:
                stress_container.reload()
                if stress_container.status == "exited":
                    break
                await asyncio.sleep(1)
            end_time = datetime.now()

            print(stress_container.logs().decode("utf-8"))
            stress_container.remove()
            return StressContainerOutput(
                start_time=start_time,
                end_time=end_time,
                container_id=id,
            )

        except Exception as e:
            print(f"Stress Container Error: {e}")
            raise Exception(f"Stress Container Error: {e}")


class StressProcess:
    def __init__(self, sc: StressProcessConfig):
        self.isolated_cpus = sc.isolated_cpus
        self.stress_load = sc.stress_load
        self.stresser_timeout = sc.stresser_timeout
        self.generate_new_stress_command()
        print(self.stress_command)

    @property
    def stress_command(self) -> str:
        return self._stress_command
    
    def generate_new_stress_command(self) -> None:
        cpus = ",".join(self.isolated_cpus)
        cpu_num = len(self.isolated_cpus)
        if self.stresser_timeout < 12:
            raise Exception("Stresser timeout should be at least 12 seconds")
        # replace stress command with a script
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