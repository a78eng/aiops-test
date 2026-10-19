import httpx
import subprocess
from datetime import datetime, timedelta
from config import settings

# ============ Prometheus 查询 ============
async def prom_query(query: str):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{settings.PROMETHEUS_URL}/api/v1/query", params={"query": query})
        resp.raise_for_status()
        return resp.json()

async def prom_query_range(query: str, hours: int = 1, step: str = "60s"):
    end = datetime.now()
    start = end - timedelta(hours=hours)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{settings.PROMETHEUS_URL}/api/v1/query_range", params={
            "query": query,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": step,
        })
        resp.raise_for_status()
        return resp.json()

def _first_value(data: dict):
    """从 Prometheus 即时查询结果中提取第一个值"""
    try:
        return data["data"]["result"][0]["value"][1]
    except Exception:
        return None

# ============ GPU（nvidia-smi 直采，无需额外 exporter） ============
def get_gpu_info() -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        used, total, util = [x.strip() for x in out.stdout.strip().split(",")]
        return f"{used}/{total} MB ({util}%)"
    except Exception:
        return "N/A"

# ============ 实时指标（前端仪表盘卡片） ============
async def get_current_metrics() -> dict:
    try:
        cpu = _first_value(await prom_query('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'))
        mem = _first_value(await prom_query('(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100'))
        disk = _first_value(await prom_query('(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100'))
    except Exception:
        cpu = mem = disk = None
    return {
        "cpu": round(float(cpu), 1) if cpu else None,
        "mem": round(float(mem), 1) if mem else None,
        "disk": round(float(disk), 1) if disk else None,
        "gpu": get_gpu_info(),
    }

# ============ 趋势数据（前端 ECharts） ============
async def get_metric_range(hours: int = 1) -> dict:
    def parse(data: dict):
        result = data.get("data", {}).get("result", [])
        if not result:
            return []
        return [{"time": datetime.fromtimestamp(v[0]).strftime("%H:%M"),
                 "value": round(float(v[1]), 1)} for v in result[0]["values"]]
    try:
        cpu = parse(await prom_query_range('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)', hours))
        mem = parse(await prom_query_range('(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100', hours))
    except Exception:
        cpu = mem = []
    return {"cpu": cpu, "mem": mem}

# ============ Loki 错误日志拉取（AI 报告素材） ============
async def get_recent_error_logs(hours: int = 24, limit: int = 50) -> list:
    """查询最近 N 小时包含 error/failed/exception/fatal 的日志行"""
    query = '{job=~"varlogs|docker"} |~ "(?i)error|failed|exception|fatal"'
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{settings.LOKI_URL}/loki/api/v1/query_range", params={
                "query": query,
                "start": int((datetime.now() - timedelta(hours=hours)).timestamp() * 1e9),
                "end": int(datetime.now().timestamp() * 1e9),
                "limit": limit,
            })
            resp.raise_for_status()
            data = resp.json()
        logs = []
        for stream in data.get("data", {}).get("result", []):
            for entry in stream.get("values", []):
                logs.append(entry[1])
        return logs[:limit]
    except Exception:
        return []

# ============ 拼装给大模型的指标摘要 ============
async def build_metrics_summary() -> str:
    m = await get_current_metrics()
    return (
        f"CPU 使用率: {m['cpu']}%\n"
        f"内存使用率: {m['mem']}%\n"
        f"磁盘使用率: {m['disk']}%\n"
        f"GPU 状态: {m['gpu']}\n"
    )
# ============ ★ 系统全局巡检数据采集 ============
def get_docker_summary() -> dict:
    """采集 Docker 容器概况：总数 + 每个容器的名称/镜像/状态（即业务信息）"""
    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Image}}|{{.Status}}"],
            capture_output=True, text=True, timeout=10)
        containers = []
        for line in out.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                containers.append({"name": parts[0], "image": parts[1], "status": parts[2]})
        return {"available": True, "count": len(containers), "containers": containers}
    except FileNotFoundError:
        return {"available": False, "reason": "Docker 未安装"}
    except Exception as e:
        return {"available": False, "reason": str(e)}
def get_k8s_summary() -> dict:
    """采集 K8s 集群概况：节点、Pod 总数、异常 Pod。未部署则 available=False，不报错"""
    try:
        nodes = subprocess.run(["kubectl", "get", "nodes", "-o", "name"],
                               capture_output=True, text=True, timeout=10)
        if nodes.returncode != 0:
            return {"available": False, "reason": "kubectl 无法连接集群"}
        node_names = [n.strip() for n in nodes.stdout.strip().splitlines()]
        pods = subprocess.run(["kubectl", "get", "pods", "--all-namespaces", "--no-headers"],
                              capture_output=True, text=True, timeout=15)
        if pods.returncode != 0:
            return {"available": False, "reason": "无法获取 Pod 信息"}
        pod_list, issues = [], []
        for line in pods.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                ns, name, ready, status = parts[0], parts[1], parts[2], parts[3]
                pod_list.append({"namespace": ns, "name": name, "ready": ready, "status": status})
                ready_ok = "/" not in ready or ready.split("/")[0] == ready.split("/")[1]
                if status not in ("Running", "Completed") or not ready_ok:
                    issues.append(f"{ns}/{name} 状态 {status}（ready {ready}）")
        return {"available": True, "nodes": node_names, "node_count": len(node_names),
                "pods_total": len(pod_list), "pods": pod_list, "issues": issues}
    except FileNotFoundError:
        return {"available": False, "reason": "kubectl 未安装"}
    except Exception as e:
        return {"available": False, "reason": str(e)}
def get_system_snapshot() -> str:
    """拼装给大模型看的全局架构概况文本（Docker + K8s）"""
    docker = get_docker_summary()
    k8s = get_k8s_summary()
    lines = []
    if docker.get("available"):
        lines.append(f"Docker：共 {docker['count']} 个运行中容器")
        for c in docker["containers"]:
            lines.append(f"  - {c['name']}（{c['image']}）：{c['status']}")
    else:
        lines.append("Docker：未部署或不可用")
    if k8s.get("available"):
        lines.append(f"K8s：{k8s['node_count']} 个节点，{k8s['pods_total']} 个 Pod")
        if k8s.get("issues"):
            lines.append("异常 Pod：")
            for i in k8s["issues"][:20]:
                lines.append(f"  - {i}")
        else:
            lines.append("K8s：全部 Pod 运行正常")
    else:
        lines.append("K8s：未部署集群（当前为 Docker 单机架构）")
    return "\n".join(lines)
