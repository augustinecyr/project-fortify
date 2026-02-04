"""
Database seeding script for Project Fortify.
Loads VM fixtures and generates CPU metrics for testing.
"""
import json
import sys
import random
from pathlib import Path
from datetime import UTC, datetime, timedelta

# Add parent directories to path
project_root = Path(__file__).resolve().parents[2]
api_path = project_root / "api"
sys.path.insert(0, str(api_path))

from app.db.database import SessionLocal
from app.db.models import VirtualMachine, CPUMetric


def load_vm_fixtures():
    """Load VM fixtures from JSON file."""
    fixtures_path = project_root / "data" / "fixtures" / "vms.json"
    with open(fixtures_path, 'r') as f:
        return json.load(f)


def generate_cpu_metrics(vm_id: str, days: int = 7):
    """
    Generate realistic CPU metrics for a VM.
    
    Args:
        vm_id: Virtual machine ID
        days: Number of days of historical data to generate
    
    Returns:
        List of CPUMetric objects
    """
    metrics = []
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    
    # Generate metrics every 1 minute
    current_time = start_time
    interval = timedelta(minutes=1)
    
    # Base CPU pattern (varies by VM type)
    if "web" in vm_id or "api" in vm_id:
        base_cpu = 45.0
        variance = 20.0
    elif "db" in vm_id:
        base_cpu = 60.0
        variance = 15.0
    elif "worker" in vm_id:
        base_cpu = 70.0
        variance = 25.0
    else:
        base_cpu = 30.0
        variance = 15.0
    
    while current_time <= end_time:
        # Add daily pattern (higher during business hours)
        hour = current_time.hour
        if 9 <= hour <= 17:
            time_factor = 1.2
        elif 0 <= hour <= 6:
            time_factor = 0.7
        else:
            time_factor = 1.0
        
        # Generate CPU percentage with some randomness
        cpu_percent = base_cpu * time_factor + random.uniform(-variance, variance)
        cpu_percent = max(0.0, min(100.0, cpu_percent))  # Clamp between 0-100
        
        # Occasionally add spikes (5% chance)
        if random.random() < 0.05:
            cpu_percent = min(100.0, cpu_percent + random.uniform(15, 30))
        
        metrics.append(
            CPUMetric(
                vm_id=vm_id,
                timestamp=current_time,
                cpu_percent=round(cpu_percent, 2),
                source="mock_monitoring"
            )
        )
        
        current_time += interval
    
    return metrics


def seed_database():
    """Main seeding function."""
    db = SessionLocal()
    
    try:
        print("Starting database seeding...")
        
        # Load VM fixtures
        vm_fixtures = load_vm_fixtures()
        print(f"Loaded {len(vm_fixtures)} VM fixtures")
        
        # Clear existing data
        print("Clearing existing data...")
        db.query(CPUMetric).delete()
        db.query(VirtualMachine).delete()
        db.commit()
        
        # Insert VMs
        print("Inserting VMs...")
        vms_created = 0
        for vm_data in vm_fixtures:
            vm = VirtualMachine(
                vm_id=vm_data["vm_id"],
                name=vm_data["name"]
            )
            db.add(vm)
            vms_created += 1
        
        db.commit()
        print(f"Created {vms_created} VMs")
        
        # Generate CPU metrics for each VM
        print("Generating CPU metrics (this may take a moment)...")
        total_metrics = 0
        
        for vm_data in vm_fixtures:
            vm_id = vm_data["vm_id"]
            metrics = generate_cpu_metrics(vm_id, days=7)
            
            # Bulk insert in batches of 1000
            for i in range(0, len(metrics), 1000):
                batch = metrics[i:i+1000]
                db.bulk_save_objects(batch)
                db.commit()
            
            total_metrics += len(metrics)
            print(f"  Generated {len(metrics)} metrics for {vm_id}")
        
        print(f"\nSeeding complete!")
        print(f"Total VMs: {vms_created}")
        print(f"Total CPU metrics: {total_metrics}")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()