"""
Database Diagnostic Script
Checks what data is actually in the VirtualMachine table
"""
import sys
from pathlib import Path

# Add API path
project_root = Path(__file__).resolve().parents[2]
api_path = project_root / "api"
sys.path.insert(0, str(api_path))

from app.db.database import SessionLocal
from app.db.models import VirtualMachine


def check_vm_data():
    """Check what data exists in the database."""
    db = SessionLocal()
    
    try:
        vms = db.query(VirtualMachine).all()
        
        print("=" * 80)
        print(f"DATABASE DIAGNOSTIC - Found {len(vms)} VMs")
        print("=" * 80)
        
        if not vms:
            print("❌ No VMs found in database!")
            print("\n💡 Run: python data/seeds/seed_database.py")
            return
        
        # Check first VM in detail
        vm = vms[0]
        
        print(f"\n📊 Sample VM: {vm.vm_id} - {vm.name}")
        print("-" * 80)
        
        # Core fields
        print("\n🔹 CORE FIELDS:")
        print(f"  VM ID: {vm.vm_id}")
        print(f"  Name: {vm.name}")
        print(f"  Status: {vm.status}")
        print(f"  Host: {vm.host}")
        print(f"  OS Version: {vm.os_version}")
        
        # Health scores
        print("\n🔹 HEALTH & SECURITY:")
        print(f"  Health Score: {vm.health_score}")
        print(f"  Security Score: {vm.security_score}")
        print(f"  Uptime Hours: {vm.uptime_hours}")
        
        # Resources
        print("\n🔹 CURRENT RESOURCES:")
        print(f"  CPU: {vm.current_cpu}%")
        print(f"  Memory: {vm.current_memory}%")
        print(f"  Disk: {vm.current_disk}%")
        print(f"  Memory Total: {vm.memory_total_mb} MB")
        print(f"  Memory Used: {vm.memory_used_mb} MB")
        print(f"  Disk Total: {vm.disk_total_gb} GB")
        print(f"  Disk Used: {vm.disk_used_gb} GB")
        
        # Network
        print("\n🔹 NETWORK:")
        print(f"  Network In: {vm.network_in_mbps} MB/s")
        print(f"  Network Out: {vm.network_out_mbps} MB/s")
        
        # Security
        print("\n🔹 SECURITY:")
        print(f"  Open Vulnerabilities: {vm.open_vulnerabilities}")
        print(f"  Critical Vulnerabilities: {vm.critical_vulnerabilities}")
        print(f"  Last Patch Date: {vm.last_patch_date}")
        print(f"  Compliance Score: {vm.compliance_score}")
        print(f"  Firewall Enabled: {vm.firewall_enabled}")
        print(f"  SSH Key Auth: {vm.ssh_key_auth}")
        print(f"  Disk Encryption: {vm.disk_encryption}")
        
        # Alerts
        print("\n🔹 ALERTS & ANOMALIES:")
        print(f"  Alert Count: {vm.alert_count}")
        print(f"  Anomaly Detected: {vm.anomaly_detected}")
        print(f"  Last Anomaly Time: {vm.last_anomaly_time}")
        
        # 24h aggregates
        print("\n🔹 24-HOUR AGGREGATES:")
        print(f"  Avg CPU 24h: {vm.avg_cpu_24h}%")
        print(f"  Peak CPU 24h: {vm.peak_cpu_24h}%")
        print(f"  Metric Count 24h: {vm.metric_count_24h}")
        
        # Summary of all VMs
        print("\n" + "=" * 80)
        print("📊 FLEET SUMMARY")
        print("=" * 80)
        
        null_counts = {
            'host': 0,
            'os_version': 0,
            'health_score': 0,
            'security_score': 0,
            'current_cpu': 0,
            'current_memory': 0,
            'current_disk': 0,
            'memory_total_mb': 0,
            'open_vulnerabilities': 0,
            'compliance_score': 0
        }
        
        for vm in vms:
            for field in null_counts:
                if getattr(vm, field) is None:
                    null_counts[field] += 1
        
        print(f"\nTotal VMs: {len(vms)}")
        print(f"Online VMs: {sum(1 for vm in vms if vm.status == 'online')}")
        print(f"Offline VMs: {sum(1 for vm in vms if vm.status == 'offline')}")
        
        print("\n⚠️ NULL/MISSING FIELDS:")
        has_issues = False
        for field, count in null_counts.items():
            if count > 0:
                percentage = (count / len(vms)) * 100
                print(f"  {field}: {count}/{len(vms)} ({percentage:.1f}%) are NULL")
                has_issues = True
        
        if not has_issues:
            print("  ✅ All fields populated correctly!")
        else:
            print("\n💡 Some fields are NULL. This means:")
            print("   1. Database wasn't seeded with enhanced data, OR")
            print("   2. Migration wasn't run before seeding")
            print("\n📝 To fix:")
            print("   python data/seeds/migrate_database.py")
            print("   python data/seeds/seed_database.py")
        
        print("\n" + "=" * 80)
        
    except AttributeError as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 This means your VirtualMachine model doesn't have these fields.")
        print("   Update your models.py with the enhanced version.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    check_vm_data()