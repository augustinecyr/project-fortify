"""
Continuous metrics simulator for Project Fortify.
Enhanced with more varied profiles, per‑VM personality, and status updates.
"""

import time
import random
import math                # <-- IMPORTANT: previously missing
import requests
from datetime import datetime, UTC
from typing import Dict, Any

API_URL = "http://localhost:8000/api/v1/metrics"
VM_UPDATE_URL = "http://localhost:8000/api/v1/vms"
HEALTH_SCORE_URL = "http://localhost:8000/api/v1/health"

VM_IDS = [f"vm-{i:03d}" for i in range(1, 21)]

# ========== VM PROFILES – now with wider variety ==========
VM_PROFILES = {
    # name: (base_cpu, base_mem, variance, spike_chance, personality_factor)
    "web":        (40, 55, 15, 0.03, 1.0),
    "api":        (45, 60, 18, 0.04, 1.2),
    "db":         (65, 78, 12, 0.02, 0.8),
    "cache":      (25, 40, 10, 0.01, 0.5),
    "worker":     (75, 72, 20, 0.06, 1.5),
    "monitor":    (20, 35,  8, 0.01, 0.4),
    "backup":     (15, 38, 12, 0.02, 0.6),
    "load-balancer": (18, 30, 8, 0.01, 0.3),
    "firewall":   (12, 25,  5, 0.01, 0.2),
    "batch":      (60, 50, 25, 0.10, 1.8),   # new: batch job VM
    "idle":       ( 5, 20,  5, 0.00, 0.1),   # new: almost idle
    "default":    (35, 50, 15, 0.03, 1.0)
}

# Assign each VM a persistent "personality" (profile + extra drift)
vm_personality = {}
for vm_id in VM_IDS:
    # Extract profile type from name (or fallback to default)
    profile_type = "default"
    for key in VM_PROFILES.keys():
        if key in vm_id.lower():
            profile_type = key
            break
    # Store a persistent drift factor unique to this VM
    vm_personality[vm_id] = {
        "profile": profile_type,
        "drift": random.uniform(0.8, 1.2),          # long‑term trend
        "phase": random.uniform(0, 2 * 3.14159),    # for sinusoidal variation
        "last_anomaly_time": None
    }


def get_vm_profile(vm_id: str) -> tuple:
    """Return the base profile tuple (cpu, mem, variance, spike, personality)."""
    ptype = vm_personality[vm_id]["profile"]
    return VM_PROFILES[ptype]


def simulate_anomaly(vm_id: str, cpu: float, memory: float) -> tuple[bool, int]:
    """Detect if current metrics represent an anomaly."""
    is_anomaly = False
    alert_count = 0
    if cpu > 90:
        alert_count += 2
        is_anomaly = True
    elif cpu > 75:
        alert_count += 1
    if memory > 90:
        alert_count += 2
        is_anomaly = True
    elif memory > 80:
        alert_count += 1
    return is_anomaly, alert_count


def generate_comprehensive_metrics(vm_id: str) -> Dict[str, Any]:
    personality = vm_personality[vm_id]
    base_cpu, base_mem, variance, spike_chance, profile_factor = get_vm_profile(vm_id)

    # Time‑of‑day factor – now with VM‑specific phase to stagger peaks
    hour = datetime.now().hour + personality["phase"] / (2 * 3.14159) * 24
    hour = hour % 24
    if 9 <= hour <= 17:
        time_factor = 1.2
    elif 0 <= hour <= 6:
        time_factor = 0.7
    else:
        time_factor = 1.0

    # Apply persistent drift and profile personality
    drift = personality["drift"]
    effective_cpu = base_cpu * time_factor * drift * profile_factor
    effective_mem = base_mem * time_factor * drift * profile_factor

    # Add sinusoidal 24‑hour wave (peak at different hours per VM)
    wave = 0.2 * math.sin(2 * 3.14159 * (hour / 24) + personality["phase"])
    effective_cpu *= (1 + wave)
    effective_mem *= (1 + wave * 0.5)   # memory less volatile

    # Generate CPU with randomness
    cpu = effective_cpu + random.uniform(-variance, variance)
    cpu = max(0.0, min(100.0, cpu))

    # Occasional spikes
    if random.random() < spike_chance:
        cpu = min(100.0, cpu + random.uniform(15, 30))
       
    # Memory (correlated with CPU)
    mem = effective_mem + random.uniform(-variance, variance) + 0.3 * (cpu - effective_cpu)
    mem = max(0.0, min(100.0, mem))

    # Disk (grows slowly over time – simulate daily growth)
    disk = 40 + random.uniform(-5, 5) + (datetime.now().day % 30) * 0.5
    disk = max(10.0, min(95.0, disk))

    # Network (correlated with CPU)
    if cpu > 60:
        net_in = random.uniform(3.0, 10.0)
        net_out = random.uniform(2.0, 8.0)
    else:
        net_in = random.uniform(0.5, 4.0)
        net_out = random.uniform(0.3, 3.0)

    anomaly, alert_count = simulate_anomaly(vm_id, cpu, mem)
    
    if anomaly:
        personality["last_anomaly_time"] = datetime.now(UTC)
    
    return {
        "vm_id": vm_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "cpu_percent": round(cpu, 2),
        "memory_percent": round(mem, 2),
        "disk_percent": round(disk, 2),
        "network_in_mbps": round(net_in, 2),
        "network_out_mbps": round(net_out, 2),
        "alert_count": alert_count,
        "anomaly_detected": anomaly,
        "last_anomaly_time": personality["last_anomaly_time"].isoformat() if personality["last_anomaly_time"] else None,
    }


def get_computed_health_score(vm_id: str) -> int:
    try:
        response = requests.get(f"{HEALTH_SCORE_URL}/{vm_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return int(data.get("health_score", 0))
        else:
            print(f"  ⚠️  Health score fetch failed for {vm_id}: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ⚠️  Health score fetch error for {vm_id}: {e}")
    return 0


def update_vm_state(vm_id: str, metrics: Dict[str, Any], computed_health: int):
    if computed_health >= 80:
        status = "online"
    elif computed_health >= 60:
        status = "warning"
    else:
        status = "critical"

    update_payload = {
    "current_cpu": metrics["cpu_percent"],
    "current_memory": metrics["memory_percent"],
    "current_disk": metrics["disk_percent"],
    "network_in_mbps": metrics["network_in_mbps"],
    "network_out_mbps": metrics["network_out_mbps"],
    "health_score": computed_health,
    "alert_count": metrics["alert_count"],
    "anomaly_detected": metrics["anomaly_detected"],
    "status": status,
    # ADD THESE THREE:
    "avg_memory_24h": metrics["memory_percent"],   # use current reading as rolling proxy
    "avg_disk_24h": metrics["disk_percent"],
    "last_anomaly_time": metrics.get("last_anomaly_time"),
}

    try:
        response = requests.patch(f"{VM_UPDATE_URL}/{vm_id}", json=update_payload, timeout=2)
        if response.status_code in [200, 204]:
            return True
        else:
            print(f"  ⚠️  PATCH failed for {vm_id}: HTTP {response.status_code} – {response.text}")
            return False
    except Exception as e:
        print(f"  ⚠️  PATCH error for {vm_id}: {e}")
        return False


def send_cpu_metric(vm_id: str, cpu_percent: float, timestamp: str):
    payload = {
        "vm_id": vm_id,
        "timestamp": timestamp,
        "cpu_percent": cpu_percent,
        "source": "simulator"
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=3)
        if response.status_code == 200:
            return True
        else:
            print(f"  ⚠️  POST failed for {vm_id}: HTTP {response.status_code} – {response.text}")
            return False
    except Exception as e:
        print(f"  Connection error sending CPU: {e}")
        return False


def send_metrics(vm_id: str):
    metrics = generate_comprehensive_metrics(vm_id)
    if not send_cpu_metric(vm_id, metrics["cpu_percent"], metrics["timestamp"]):
        return

    computed_health = get_computed_health_score(vm_id)
    update_vm_state(vm_id, metrics, computed_health)

    # Print status
    timestamp = datetime.now().strftime('%H:%M:%S')
    status_icon = "🔴" if metrics["anomaly_detected"] else "🟢"
    if computed_health >= 80:
        health_icon = "💚"
        health_label = "Healthy"
    elif computed_health >= 60:
        health_icon = "🟡"
        health_label = "Warning"
    elif computed_health > 0:
        health_icon = "🔴"
        health_label = "Critical"
    else:
        health_icon = "⚪"
        health_label = "N/A"

    print(f"[{timestamp}] {status_icon} {vm_id}: "
          f"CPU {metrics['cpu_percent']:.1f}% | "
          f"MEM {metrics['memory_percent']:.1f}% | "
          f"Health {health_icon} {computed_health} ({health_label})")
    if metrics["alert_count"] > 0:
        print(f"           ⚠️  {metrics['alert_count']} alert(s) detected")


def print_banner():
    print("=" * 70)
    print("  PROJECT FORTIFY - ENHANCED METRICS SIMULATOR v2.1")
    print("=" * 70)
    print(f"  Simulating {len(VM_IDS)} VMs with API-computed health scores")
    print(f"  CPU endpoint:    {API_URL}")
    print(f"  VM update:       {VM_UPDATE_URL}")
    print(f"  Health compute:  {HEALTH_SCORE_URL}/{{vm_id}}")
    print(f"  Started at:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\n  Press Ctrl+C to stop.\n")


def print_summary_stats(metrics_count: int, start_time: datetime):
    runtime = (datetime.now() - start_time).total_seconds()
    metrics_per_sec = metrics_count / runtime if runtime > 0 else 0
    print(f"\n{'─' * 70}")
    print(f"  Runtime: {runtime:.0f}s | "
          f"Total metrics sent: {metrics_count} | "
          f"Rate: {metrics_per_sec:.1f}/sec")
    print(f"{'─' * 70}\n")


def test_api_connectivity():
    print("\n  Testing API connectivity...")
    try:
        response = requests.get(f"{API_URL.replace('/metrics', '')}/health", timeout=2)
        print(f"  ✓ API health check: OK")
    except:
        print(f"  ⚠️  Cannot reach API at {API_URL}")

    try:
        test_vm = VM_IDS[0]
        response = requests.get(f"{HEALTH_SCORE_URL}/{test_vm}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Health score endpoint: OK (test: {test_vm} = {data.get('health_score', 'N/A')})")
        else:
            print(f"  ⚠️  Health score endpoint returned: HTTP {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"  ⚠️  Health score endpoint timeout (>5s)")
    except Exception as e:
        print(f"  ⚠️  Health score endpoint error: {e}")
    print()


def main():
    try:
        print_banner()
        test_api_connectivity()

        metrics_count = 0
        start_time = datetime.now()
        last_summary = start_time

        while True:
            cycle_start = time.time()

            for vm_id in VM_IDS:
                send_metrics(vm_id)
                metrics_count += 1
                time.sleep(0.3)

            if (datetime.now() - last_summary).total_seconds() >= 300:
                print_summary_stats(metrics_count, start_time)
                last_summary = datetime.now()

            cycle_duration = time.time() - cycle_start
            sleep_time = max(0, 10 - cycle_duration)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("  Simulator stopped by user")
        print_summary_stats(metrics_count, start_time)
        print("=" * 70)
    except Exception as e:
        # Print any unexpected error to stderr (will appear in red in PowerShell)
        import sys
        print(f"\n❌ Simulator crashed: {e}", file=sys.stderr)
        raise   # re-raise so the process exits with non‑zero code


if __name__ == "__main__":
    main()