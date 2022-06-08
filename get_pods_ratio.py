import json
import subprocess
from collections import Counter


def get_pods():
    output = subprocess.run(
        ["kubectl", "get", "pods", "-A", "-o", "json"], capture_output=True
    )

    data = json.loads(output.stdout)
    return data["items"]


pods = get_pods()

units = {
    "B": 1,
    "Ki": 1024,
    "K": 1000,
    "Mi": 1024**2,
    "M": 1000**2,
    "Gi": 1024**3,
    "G": 1000**3,
}

def parse_size(size):
    if size == "0":
        return 0

    if size[-1].isdigit():
        return int(size)

    if size[-2].isdigit():
        number, unit = size[0:-1], size[-1:]
    else:
        number, unit = size[0:-2], size[-2:]

    return int(float(number) * units[unit])


buckets = Counter()
cpus = Counter()


for pod in pods:
    cpu_millis = 0
    memory_bytes = 0

    for container in pod["spec"]["containers"]:
        if len(container["resources"]) == 0:
            continue

        if not "requests" in container["resources"]:
            continue

        cpu = container["resources"]["requests"].get("cpu", "0")
        if cpu.endswith("m"):
            cpu_millis += int(cpu[0:-1])
        else:
            cpu_millis += int(cpu) * 1000

        memory = container["resources"]["requests"].get("memory", "0")

        memory_bytes += parse_size(memory)

    if pod["metadata"]["namespace"] in ("kube-system", "kube-system"):
        continue

    if cpu_millis == 0:
        continue

    if not "ownerReferences" in pod["metadata"]:
        continue

    if pod["metadata"]["ownerReferences"][0]["kind"] == "DaemonSet":
        continue

    ratio = (memory_bytes / 1024 / 1024 / 1024) / (cpu_millis / 1000)

    buckets[ratio] += 1
    cpus[ratio] += cpu_millis



print("Most common ratio")

print("Ratio\tPods\tCPUs")
for ratio in buckets.items():
    print("%0.2f\t%s\t%d" % (ratio + (cpus[ratio[0]]/1000,)))
