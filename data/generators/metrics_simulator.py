"""
Continuous metrics simulator for Project Fortify.
Sends comprehensive metrics to the API every few seconds for all VMs.
Enhanced to simulate CPU, memory, disk, network, and other parameters.
IMPROVED: Now fetches and updates the API's computed health score.
"""
import time
import random
import requests
from datetime import datetime, UTC
from typing import Dict, Any

API_URL = "http://localhost:8000/api/v1/metrics"  # CPU metrics endpoint
VM_UPDATE_URL = "http://localhost:8000/api/v1/vms"  # VM update endpoint
HEALTH_SCORE_URL = "http://localhost:8000/api/v1/health"

# List of all VM IDs from your seed
VM_IDS = [f"vm-{i:03d}" for i in range(1, 21)]

# VM profiles to simulate different behaviors
VM_PROFILES = {
    "web": {"base_cpu": 40, "base_mem": 55, "variance": 15, "spike_chance": 0.03},
    "api": {"base_cpu": 45, "base_mem": 60, "variance": 18, "spike_chance": 0.04},
    "db": {"base_cpu": 65, "base_mem": 78, "variance": 12, "spike_chance": 0.02},
    "cache": {"base_cpu": 25, "base_mem": 40, "variance": 10, "spike_chance": 0.01},
    "worker": {"base_cpu": 75, "base_mem": 72, "variance": 20, "spike_chance": 0.06},
    "monitor": {"base_cpu": 20, "base_mem": 35, "variance": 8, "spike_chance": 0.01},
    "backup": {"base_cpu": 15, "base_mem": 38, "variance": 12, "spike_chance": 0.02},
    "load-balancer": {"base_cpu": 18, "base_mem": 30, "variance": 8, "spike_chance": 0.01},
    "firewall": {"base_cpu": 12, "base_mem": 25, "variance": 5, "spike_chance": 0.01},
    "default": {"base_cpu": 35, "base_mem": 50, "variance": 15, "spike_chance": 0.03}
}


def get_vm_profile(vm_id: str) -> Dict[str, Any]:
    """Determine VM profile based on VM ID or name pattern."""
    for profile_type in VM_PROFILES.keys():
        if profile_type in vm_id.lower():
            return VM_PROFILES[profile_type]
    return VM_PROFILES["default"]


def simulate_anomaly(vm_id: str, cpu: float, memory: float) -> tuple[bool, int]:
    """
    Detect if current metrics represent an anomaly.
    Returns (is_anomaly, alert_count).
    """
    is_anomaly = False
    alert_count = 0
    
    # CPU alerts
    if cpu > 90:
        alert_count += 2
        is_anomaly = True
    elif cpu > 75:
        alert_count += 1
    
    # Memory alerts
    if memory > 90:
        alert_count += 2
        is_anomaly = True
    elif memory > 80:
        alert_count += 1
    
    return is_anomaly, alert_count


def get_computed_health_score(vm_id: str) -> int:
    """
    Fetch the computed health score from the API's health endpoint.
    """
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

def generate_comprehensive_metrics(vm_id: str) -> Dict[str, Any]:
    """
    Generate comprehensive metrics for a VM including CPU, memory, disk, network.
    Health score will be fetched from API after metrics are sent.
    """
    profile = get_vm_profile(vm_id)
    
    # Time-based factor (higher during business hours)
    hour = datetime.now().hour
    if 9 <= hour <= 17:
        time_factor = 1.2
    elif 0 <= hour <= 6:
        time_factor = 0.7
    else:
        time_factor = 1.0
    
    # Generate CPU
    cpu = profile["base_cpu"] * time_factor + random.uniform(-profile["variance"], profile["variance"])
    cpu = max(0.0, min(100.0, cpu))
    
    # Occasional spikes
    if random.random() < profile["spike_chance"]:
        cpu = min(100.0, cpu + random.uniform(15, 30))
    
    # Generate Memory (slightly correlated with CPU)
    memory = profile["base_mem"] * time_factor + random.uniform(-profile["variance"], profile["variance"])
    memory = max(0.0, min(100.0, memory))
    
    # Add correlation: if CPU spikes, memory tends to spike too
    if cpu > 80:
        memory = min(100.0, memory + random.uniform(5, 15))
    
    # Generate Disk (grows slowly over time, not time-of-day dependent)
    disk = 40 + random.uniform(-5, 5)  # Around 40% with small variation
    disk = max(10.0, min(95.0, disk))
    
    # Generate Network (correlated with CPU load)
    if cpu > 60:
        network_in = random.uniform(3.0, 10.0)
        network_out = random.uniform(2.0, 8.0)
    else:
        network_in = random.uniform(0.5, 4.0)
        network_out = random.uniform(0.3, 3.0)
    
    # Detect anomalies and alerts (for immediate feedback)
    anomaly_detected, alert_count = simulate_anomaly(vm_id, cpu, memory)
    
    return {
        "vm_id": vm_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "cpu_percent": round(cpu, 2),
        "memory_percent": round(memory, 2),
        "disk_percent": round(disk, 2),
        "network_in_mbps": round(network_in, 2),
        "network_out_mbps": round(network_out, 2),
        "alert_count": alert_count,
        "anomaly_detected": anomaly_detected
    }


def send_cpu_metric(vm_id: str, cpu_percent: float, timestamp: str):
    """Send CPU metric to the API (backward compatible)."""
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
            print(f"  Error {response.status_code} sending CPU metric for {vm_id}")
            return False
    except Exception as e:
        print(f"  Connection error sending CPU: {e}")
        return False


def update_vm_state(vm_id: str, metrics: Dict[str, Any], computed_health: int):
    """
    Update VM state with comprehensive metrics including computed health score.
    Falls back gracefully if endpoint not available.
    """
    try:
        update_payload = {
            "current_cpu": metrics["cpu_percent"],
            "current_memory": metrics["memory_percent"],
            "current_disk": metrics["disk_percent"],
            "network_in_mbps": metrics["network_in_mbps"],
            "network_out_mbps": metrics["network_out_mbps"],
            "health_score": computed_health,  # Use API's computed score
            "alert_count": metrics["alert_count"],
            "anomaly_detected": metrics["anomaly_detected"]
        }
        
        response = requests.patch(f"{VM_UPDATE_URL}/{vm_id}", json=update_payload, timeout=2)
        if response.status_code in [200, 204]:
            return True
    except requests.exceptions.Timeout:
        pass  # Silently skip if endpoint doesn't exist or times out
    except Exception:
        pass  # Endpoint might not exist yet, that's okay
    
    return False


def send_metrics(vm_id: str):
    """Generate and send comprehensive metrics for a VM."""
    metrics = generate_comprehensive_metrics(vm_id)
    
    # Step 1: Send CPU metric (creates historical data for health computation)
    cpu_sent = send_cpu_metric(vm_id, metrics["cpu_percent"], metrics["timestamp"])
    
    if not cpu_sent:
        return  # Skip if CPU metric failed
    
    # Step 2: Fetch computed health score from API
    # Note: API computes health score on-demand, so we fetch it immediately
    computed_health = get_computed_health_score(vm_id)
    
    # Step 3: Update VM state with computed health score
    vm_updated = update_vm_state(vm_id, metrics, computed_health)
    
    # Print status
    timestamp = datetime.now().strftime('%H:%M:%S')
    status_icon = "🔴" if metrics["anomaly_detected"] else "🟢"
    
    # Health icon based on computed score
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
    """Print startup banner."""
    print("=" * 70)
    print("  PROJECT FORTIFY - ENHANCED METRICS SIMULATOR v2.0")
    print("=" * 70)
    print(f"  Simulating {len(VM_IDS)} VMs with API-computed health scores")
    print(f"  CPU endpoint:    {API_URL}")
    print(f"  VM update:       {VM_UPDATE_URL}")
    print(f"  Health compute:  {HEALTH_SCORE_URL}/{{vm_id}}/health")
    print(f"  Started at:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print("\n  Press Ctrl+C to stop.\n")


def print_summary_stats(metrics_count: int, start_time: datetime):
    """Print periodic summary statistics."""
    runtime = (datetime.now() - start_time).total_seconds()
    metrics_per_sec = metrics_count / runtime if runtime > 0 else 0
    
    print(f"\n{'─' * 70}")
    print(f"  Runtime: {runtime:.0f}s | "
          f"Total metrics sent: {metrics_count} | "
          f"Rate: {metrics_per_sec:.1f}/sec")
    print(f"{'─' * 70}\n")


def test_api_connectivity():
    """Test API connectivity on startup."""
    print("\n  Testing API connectivity...")
    
    # Test CPU metrics endpoint
    try:
        response = requests.get(f"{API_URL.replace('/metrics', '')}/health", timeout=2)
        print(f"  ✓ API health check: OK")
    except:
        print(f"  ⚠️  Cannot reach API at {API_URL}")
    
    # Test health score endpoint with first VM
    try:
        test_vm = VM_IDS[0]
        response = requests.get(f"{HEALTH_SCORE_URL}/{test_vm}/health", timeout=5)
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
    """Main simulator loop."""
    print_banner()
    test_api_connectivity()
    
    metrics_count = 0
    start_time = datetime.now()
    last_summary = start_time
    
    try:
        while True:
            cycle_start = time.time()
            
            # Send metrics for all VMs
            for vm_id in VM_IDS:
                send_metrics(vm_id)
                metrics_count += 1
                time.sleep(0.3)  # 0.3s between VMs = ~6s per full cycle
            
            # Print summary every 5 minutes
            if (datetime.now() - last_summary).total_seconds() >= 300:
                print_summary_stats(metrics_count, start_time)
                last_summary = datetime.now()
            
            # Wait before next cycle (total cycle time: ~10s)
            cycle_duration = time.time() - cycle_start
            sleep_time = max(0, 10 - cycle_duration)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("  Simulator stopped by user")
        print_summary_stats(metrics_count, start_time)
        print("=" * 70)


if __name__ == "__main__":
    main()