"""
Continuous metrics simulator for Project Fortify.
Sends CPU metrics to the API every few seconds for all VMs.
"""
import time
import random
import requests
from datetime import datetime, UTC

API_URL = "http://localhost:8000/api/v1/metrics"  # adjust if needed

# List of all VM IDs from your seed
VM_IDS = [f"vm-{i:03d}" for i in range(1, 21)]

def send_metric(vm_id):
    """Generate and send a single CPU metric."""
    # Base CPU pattern by VM type (same logic as seed)
    if "web" in vm_id or "api" in vm_id:
        cpu = random.uniform(30, 70)
    elif "db" in vm_id:
        cpu = random.uniform(50, 85)
    elif "worker" in vm_id:
        cpu = random.uniform(40, 95)
    else:
        cpu = random.uniform(20, 60)
    
    payload = {
        "vm_id": vm_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "cpu_percent": round(cpu, 2),
        "source": "simulator"
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent {vm_id}: {cpu:.1f}%")
        else:
            print(f"Error {response.status_code} for {vm_id}")
    except Exception as e:
        print(f"Connection error: {e}")

def main():
    print("Starting continuous metrics simulator...")
    print("Press Ctrl+C to stop.\n")
    
    while True:
        for vm_id in VM_IDS:
            send_metric(vm_id)
            time.sleep(0.5)  # 0.5s between VMs = ~10s per full cycle
        time.sleep(5)        # pause between cycles (adjust as needed)

if __name__ == "__main__":
    main()