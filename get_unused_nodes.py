import subprocess
import json
import collections
import sys

units = {
    "B": 1,
    "Ki": 1024,
    "K": 1000,
    "Mi": 1024**2,
    "M": 1000**2,
    "Gi": 1024**3,
    "G": 1000**3,
}

# Alternative unit definitions, notably used by Windows:
# units = {"B": 1, "KB": 2**10, "MB": 2**20, "GB": 2**30, "TB": 2**40}


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


def get_nodes():
    output = subprocess.run(
        ["kubectl", "get", "nodes", "-o", "json"], capture_output=True
    )

    data = json.loads(output.stdout)
    return data["items"]


def get_pods():
    output = subprocess.run(
        ["kubectl", "get", "pods", "-A", "-o", "json"], capture_output=True
    )

    data = json.loads(output.stdout)
    return data["items"]


nodes = get_nodes()
pods = get_pods()


nodes_map = {node["metadata"]["name"]: node for node in nodes}

for node in nodes_map:
    nodes_map[node]["pods_cpu_millis"] = 0
    nodes_map[node]["pods_memory_bytes"] = 0


def get_pod_resources(pod):
    cpu_millis = 0
    memory_bytes = 0

    for container in pod["spec"]["containers"]:
        if len(container["resources"]) == 0:
            continue

        if "requests" not in container["resources"]:
            continue

        cpu = container["resources"]["requests"].get("cpu", "0")
        if cpu.endswith("m"):
            cpu_millis += int(cpu[0:-1])
        else:
            cpu_millis += int(cpu) * 1000

        memory = container["resources"]["requests"].get("memory", "0")
        memory_bytes += parse_size(memory)

    return cpu_millis, memory_bytes


for pod in pods:
    cpu_millis, memory_bytes = get_pod_resources(pod)
    node = pod["spec"].get("nodeName")

    if not node:
        continue

    if node not in nodes_map:
        continue

    nodes_map[node]["pods_cpu_millis"] += cpu_millis
    nodes_map[node]["pods_memory_bytes"] += memory_bytes


min_unused = 0.8

final_list = []


for name, node in nodes_map.items():
    cpu_ratio = node["pods_cpu_millis"] / int(
        node["status"]["allocatable"]["cpu"][0:-1]
    )
    memory_ratio = node["pods_memory_bytes"] / parse_size(
        node["status"]["allocatable"]["memory"]
    )

    #if cpu_ratio >= min_unused and memory_ratio >= min_unused:
    #    continue


    avg_ratio = ((cpu_ratio *3) + (memory_ratio))/4

    final_list.append((name, cpu_ratio, memory_ratio, avg_ratio))


final_list.sort(key=lambda x: x[3])

for l in final_list:
    print("%50s %0.2f %0.2f %0.2f" % l)
