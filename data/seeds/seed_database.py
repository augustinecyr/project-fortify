"""
Database seeding script for Project Fortify.
Generates dynamic VM fixtures and comprehensive metrics for testing.
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


# ============================================================================
# EMBEDDED VM DATA GENERATOR (fallback if generate_vm_data.py not available)
# ============================================================================

class VMDataGenerator:
    """Generate realistic VM data dynamically."""
    
    VM_TEMPLATES = {
        "web": ["web-server-prod", "web-server-staging", "web-app"],
        "api": ["api-gateway", "api-service"],
        "db": ["db-server-primary", "db-server-replica", "database"],
        "cache": ["cache-server", "redis-cluster"],
        "worker": ["worker-node", "batch-processor", "queue-worker"],
        "monitor": ["monitoring-server", "metrics-collector"],
        "log": ["log-aggregator", "logging-server"],
        "backup": ["backup-server", "snapshot-manager"],
        "test": ["test-env-web", "test-env-db", "test-env-api"],
        "staging": ["staging-web", "staging-api", "staging-worker"],
        "dev": ["dev-environment", "dev-box"],
        "lb": ["load-balancer", "reverse-proxy"],
        "firewall": ["firewall-gateway", "security-gateway"]
    }
    
    OS_VERSIONS = [
        "Ubuntu 22.04 LTS", "Ubuntu 20.04 LTS", "CentOS 8",
        "Debian 11", "Red Hat Enterprise Linux 8", "pfSense 2.7.0"
    ]
    
    HOSTS = ["host-01", "host-02", "host-03", "host-04"]
    
    def __init__(self, num_vms: int = 20, seed: int = None):
        self.num_vms = num_vms
        if seed is not None:
            random.seed(seed)
    
    def _get_vm_type(self, index: int) -> str:
        types = list(self.VM_TEMPLATES.keys())
        return types[index % len(types)]
    
    def _generate_vm_name(self, vm_type: str) -> str:
        template = random.choice(self.VM_TEMPLATES[vm_type])
        suffix = random.randint(1, 99)
        return f"{template}-{suffix:02d}"
    
    def _generate_uptime_hours(self, vm_type: str) -> float:
        if vm_type in ["firewall", "lb", "monitor"]:
            return random.uniform(1000, 3000)
        elif vm_type in ["db", "cache"]:
            return random.uniform(500, 1500)
        elif vm_type in ["test", "dev"]:
            return random.uniform(1, 200)
        else:
            return random.uniform(100, 1000)
    
    def _generate_health_score(self, vm_type: str) -> int:
        if vm_type in ["firewall", "lb", "monitor"]:
            return random.randint(90, 99)
        elif vm_type in ["db", "worker"]:
            return random.randint(65, 85)
        elif vm_type in ["test", "dev"]:
            return random.randint(80, 98)
        else:
            return random.randint(75, 95)
    
    def _generate_security_score(self, vm_type: str, last_patch_days_ago: int) -> int:
        base_score = 90
        if last_patch_days_ago > 30:
            base_score -= 20
        elif last_patch_days_ago > 14:
            base_score -= 10
        elif last_patch_days_ago > 7:
            base_score -= 5
        
        if vm_type in ["firewall", "lb"]:
            base_score = min(99, base_score + 10)
        elif vm_type in ["test", "dev"]:
            base_score = max(70, base_score - 15)
        
        return max(60, min(99, base_score + random.randint(-5, 5)))
    
    def _generate_cpu_usage(self, vm_type: str) -> float:
        if vm_type == "worker":
            return random.uniform(70, 90)
        elif vm_type == "db":
            return random.uniform(60, 85)
        elif vm_type in ["web", "api"]:
            return random.uniform(30, 60)
        elif vm_type == "cache":
            return random.uniform(20, 40)
        elif vm_type in ["test", "dev"]:
            return random.uniform(10, 30)
        else:
            return random.uniform(15, 50)
    
    def _generate_memory_usage(self, vm_type: str) -> float:
        if vm_type == "db":
            return random.uniform(75, 90)
        elif vm_type == "cache":
            return random.uniform(40, 60)
        elif vm_type == "worker":
            return random.uniform(65, 85)
        elif vm_type in ["web", "api"]:
            return random.uniform(45, 70)
        else:
            return random.uniform(25, 55)
    
    def _generate_memory_capacity(self, vm_type: str) -> int:
        if vm_type == "db":
            return random.choice([32768, 65536])
        elif vm_type in ["worker", "log"]:
            return random.choice([16384, 32768])
        elif vm_type in ["web", "api", "cache"]:
            return random.choice([8192, 16384])
        else:
            return random.choice([4096, 8192])
    
    def _generate_disk_capacity(self, vm_type: str) -> int:
        if vm_type == "backup":
            return random.choice([2000, 5000, 10000])
        elif vm_type in ["db", "log"]:
            return random.choice([1000, 2000])
        elif vm_type in ["web", "api", "worker"]:
            return random.choice([250, 500])
        else:
            return random.choice([128, 250])
    
    def _generate_vulnerabilities(self, last_patch_days_ago: int) -> tuple:
        if last_patch_days_ago <= 7:
            open_vulns = random.randint(0, 2)
            critical_vulns = 0
        elif last_patch_days_ago <= 30:
            open_vulns = random.randint(2, 5)
            critical_vulns = random.randint(0, 1)
        else:
            open_vulns = random.randint(5, 10)
            critical_vulns = random.randint(1, 3)
        return open_vulns, critical_vulns
    
    def _generate_compliance_score(self, security_score: int) -> str:
        if security_score >= 90:
            passed = random.randint(5, 6)
        elif security_score >= 75:
            passed = random.randint(4, 5)
        else:
            passed = random.randint(2, 4)
        return f"{passed}/6"
    
    def _should_have_encryption(self, vm_type: str) -> bool:
        if vm_type in ["db", "firewall", "backup"]:
            return random.random() > 0.2
        elif vm_type in ["test", "dev"]:
            return random.random() > 0.8
        else:
            return random.random() > 0.5
    
    def _generate_alerts(self, health_score: int, cpu: float, memory: float) -> int:
        alert_count = 0
        if health_score < 70:
            alert_count += random.randint(1, 3)
        if cpu > 85:
            alert_count += random.randint(1, 2)
        if memory > 85:
            alert_count += random.randint(1, 2)
        return alert_count
    
    def _detect_anomaly(self, health_score: int, alert_count: int) -> bool:
        if health_score < 70 or alert_count >= 2:
            return random.random() > 0.6
        return False
    
    def generate_vm(self, index: int) -> dict:
        """Generate a single VM with realistic parameters."""
        vm_id = f"vm-{index+1:03d}"
        vm_type = self._get_vm_type(index)
        
        status = "offline" if random.random() < 0.05 else "online"
        name = self._generate_vm_name(vm_type)
        host = random.choice(self.HOSTS)
        os_version = random.choice(self.OS_VERSIONS)
        
        uptime_hours = self._generate_uptime_hours(vm_type) if status == "online" else 0
        last_patch_days_ago = random.randint(1, 45)
        last_patch_date = (datetime.now(UTC) - timedelta(days=last_patch_days_ago)).isoformat()
        
        memory_total_mb = self._generate_memory_capacity(vm_type)
        disk_total_gb = self._generate_disk_capacity(vm_type)
        
        if status == "online":
            current_cpu = round(self._generate_cpu_usage(vm_type), 1)
            current_memory = round(self._generate_memory_usage(vm_type), 1)
            current_disk = round(random.uniform(20, 85), 1)
            memory_used_mb = int(memory_total_mb * current_memory / 100)
            disk_used_gb = int(disk_total_gb * current_disk / 100)
            network_in_mbps = round(random.uniform(0.5, 10.0), 1)
            network_out_mbps = round(random.uniform(0.3, 8.0), 1)
        else:
            current_cpu = None
            current_memory = None
            current_disk = None
            memory_used_mb = None
            network_in_mbps = None
            network_out_mbps = None
            disk_used_gb = int(disk_total_gb * random.uniform(0.3, 0.7))
        
        health_score = self._generate_health_score(vm_type) if status == "online" else None
        security_score = self._generate_security_score(vm_type, last_patch_days_ago)
        
        open_vulnerabilities, critical_vulnerabilities = self._generate_vulnerabilities(last_patch_days_ago)
        compliance_score = self._generate_compliance_score(security_score)
        
        firewall_enabled = vm_type not in ["test", "dev"] or random.random() > 0.3
        ssh_key_auth = True
        disk_encryption = self._should_have_encryption(vm_type)
        
        if status == "online":
            alert_count = self._generate_alerts(health_score, current_cpu, current_memory)
            anomaly_detected = self._detect_anomaly(health_score, alert_count)
        else:
            alert_count = 0
            anomaly_detected = False
        
        return {
            "vm_id": vm_id, "name": name, "host": host, "os_version": os_version,
            "status": status, "uptime_hours": uptime_hours if status == "online" else 0,
            "health_score": health_score, "security_score": security_score,
            "current_cpu": current_cpu, "current_memory": current_memory, "current_disk": current_disk,
            "memory_total_mb": memory_total_mb, "memory_used_mb": memory_used_mb,
            "disk_total_gb": disk_total_gb, "disk_used_gb": disk_used_gb,
            "network_in_mbps": network_in_mbps, "network_out_mbps": network_out_mbps,
            "last_patch_date": last_patch_date,
            "open_vulnerabilities": open_vulnerabilities,
            "critical_vulnerabilities": critical_vulnerabilities,
            "compliance_score": compliance_score,
            "firewall_enabled": firewall_enabled,
            "ssh_key_auth": ssh_key_auth,
            "disk_encryption": disk_encryption,
            "alert_count": alert_count,
            "anomaly_detected": anomaly_detected
        }
    
    def generate_all_vms(self) -> list:
        return [self.generate_vm(i) for i in range(self.num_vms)]


# ============================================================================
# DATABASE SEEDING FUNCTIONS
# ============================================================================

def load_vm_fixtures():
    """Generate dynamic VM fixtures."""
    print("Generating VM data dynamically...")
    generator = VMDataGenerator(num_vms=20, seed=42)
    return generator.generate_all_vms()


def parse_datetime(date_str):
    """Parse datetime string to datetime object."""
    if date_str:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return None


def calculate_uptime_fields(uptime_hours):
    """Calculate last_boot_time from uptime_hours."""
    if uptime_hours is not None and uptime_hours > 0:
        return datetime.now(UTC) - timedelta(hours=uptime_hours)
    return None


def generate_cpu_metrics(vm_id: str, days: int = 7, vm_data: dict = None):
    """Generate realistic CPU metrics for a VM with enhanced patterns."""
    metrics = []
    
    if vm_data and vm_data.get("status") == "offline":
        print(f"  Skipping metrics for offline VM: {vm_id}")
        return metrics
    
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=days)
    current_time = start_time
    interval = timedelta(minutes=1)
    
    if vm_data and vm_data.get("current_cpu") is not None:
        base_cpu = vm_data["current_cpu"]
    else:
        base_cpu = 50.0
    
    if vm_data and vm_data.get("health_score") is not None:
        health_score = vm_data["health_score"]
        if health_score >= 90:
            variance = 10.0
        elif health_score >= 70:
            variance = 20.0
        else:
            variance = 30.0
    else:
        variance = 20.0
    
    while current_time <= end_time:
        hour = current_time.hour
        if 9 <= hour <= 17:
            time_factor = 1.2
        elif 0 <= hour <= 6:
            time_factor = 0.7
        else:
            time_factor = 1.0
        
        cpu_percent = base_cpu * time_factor + random.uniform(-variance, variance)
        cpu_percent = max(0.0, min(100.0, cpu_percent))
        
        if vm_data and vm_data.get("anomaly_detected"):
            if random.random() < 0.08:
                cpu_percent = min(100.0, cpu_percent + random.uniform(20, 40))
        elif random.random() < 0.03:
            cpu_percent = min(100.0, cpu_percent + random.uniform(10, 25))
        
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


def calculate_24h_aggregates(vm, db):
    """Calculate 24-hour aggregate metrics for a VM from CPU metrics."""
    cutoff_time = datetime.now(UTC) - timedelta(hours=24)
    
    recent_metrics = db.query(CPUMetric).filter(
        CPUMetric.vm_id == vm.vm_id,
        CPUMetric.timestamp >= cutoff_time
    ).all()
    
    if recent_metrics:
        cpu_values = [m.cpu_percent for m in recent_metrics]
        vm.avg_cpu_24h = round(sum(cpu_values) / len(cpu_values), 2)
        vm.peak_cpu_24h = round(max(cpu_values), 2)
        vm.metric_count_24h = len(recent_metrics)
        
        latest_metric = max(recent_metrics, key=lambda m: m.timestamp)
        vm.current_cpu = latest_metric.cpu_percent
    else:
        vm.avg_cpu_24h = None
        vm.peak_cpu_24h = None
        vm.metric_count_24h = 0


def seed_database():
    """Main seeding function with enhanced VM parameters."""
    db = SessionLocal()
    
    try:
        print("Starting database seeding with dynamically generated parameters...")
        
        vm_fixtures = load_vm_fixtures()
        print(f"Generated {len(vm_fixtures)} VMs with enhanced parameters")
        
        print("Clearing existing data...")
        db.query(CPUMetric).delete()
        db.query(VirtualMachine).delete()
        db.commit()
        
        print("Inserting VMs with enhanced parameters...")
        vms_created = 0
        
        for vm_data in vm_fixtures:
            last_boot_time = calculate_uptime_fields(vm_data.get("uptime_hours"))
            last_patch_date = parse_datetime(vm_data.get("last_patch_date"))
            last_anomaly_time = parse_datetime(vm_data.get("last_anomaly_time")) if vm_data.get("anomaly_detected") else None
            
            vm = VirtualMachine(
                vm_id=vm_data["vm_id"],
                name=vm_data["name"],
                host=vm_data.get("host"),
                os_version=vm_data.get("os_version"),
                status=vm_data.get("status", "online"),
                uptime_hours=vm_data.get("uptime_hours"),
                last_boot_time=last_boot_time,
                health_score=vm_data.get("health_score"),
                security_score=vm_data.get("security_score"),
                current_cpu=vm_data.get("current_cpu"),
                current_memory=vm_data.get("current_memory"),
                current_disk=vm_data.get("current_disk"),
                memory_total_mb=vm_data.get("memory_total_mb"),
                memory_used_mb=vm_data.get("memory_used_mb"),
                disk_total_gb=vm_data.get("disk_total_gb"),
                disk_used_gb=vm_data.get("disk_used_gb"),
                network_in_mbps=vm_data.get("network_in_mbps"),
                network_out_mbps=vm_data.get("network_out_mbps"),
                last_patch_date=last_patch_date,
                open_vulnerabilities=vm_data.get("open_vulnerabilities", 0),
                critical_vulnerabilities=vm_data.get("critical_vulnerabilities", 0),
                compliance_score=vm_data.get("compliance_score"),
                firewall_enabled=vm_data.get("firewall_enabled", True),
                ssh_key_auth=vm_data.get("ssh_key_auth", True),
                disk_encryption=vm_data.get("disk_encryption", False),
                alert_count=vm_data.get("alert_count", 0),
                anomaly_detected=vm_data.get("anomaly_detected", False),
                last_anomaly_time=last_anomaly_time
            )
            
            db.add(vm)
            vms_created += 1
        
        db.commit()
        print(f"✓ Created {vms_created} VMs with enhanced parameters")
        
        print("\nGenerating CPU metrics (this may take a moment)...")
        total_metrics = 0
        
        for vm_data in vm_fixtures:
            vm_id = vm_data["vm_id"]
            metrics = generate_cpu_metrics(vm_id, days=7, vm_data=vm_data)
            
            if metrics:
                for i in range(0, len(metrics), 1000):
                    batch = metrics[i:i+1000]
                    db.bulk_save_objects(batch)
                    db.commit()
                
                total_metrics += len(metrics)
                print(f"  ✓ Generated {len(metrics)} metrics for {vm_id}")
        
        print("\nCalculating 24-hour aggregate metrics...")
        vms = db.query(VirtualMachine).all()
        for vm in vms:
            if vm.status == "online":
                calculate_24h_aggregates(vm, db)
        db.commit()
        print(f"✓ Updated 24-hour aggregates for {len([v for v in vms if v.status == 'online'])} online VMs")
        
        print(f"\n{'='*60}")
        print(f"Seeding complete!")
        print(f"{'='*60}")
        print(f"Total VMs created:        {vms_created}")
        print(f"  - Online VMs:           {sum(1 for v in vm_fixtures if v.get('status') == 'online')}")
        print(f"  - Offline VMs:          {sum(1 for v in vm_fixtures if v.get('status') == 'offline')}")
        print(f"Total CPU metrics:        {total_metrics}")
        online_vms = [v for v in vm_fixtures if v.get('status') == 'online']
        if online_vms:
            print(f"Average health score:     {sum(v.get('health_score', 0) or 0 for v in online_vms) // len(online_vms)}")
        print(f"Total vulnerabilities:    {sum(v.get('open_vulnerabilities', 0) for v in vm_fixtures)}")
        print(f"Critical vulnerabilities: {sum(v.get('critical_vulnerabilities', 0) for v in vm_fixtures)}")
        print(f"Total alerts:             {sum(v.get('alert_count', 0) for v in vm_fixtures)}")
        print(f"VMs with anomalies:       {sum(1 for v in vm_fixtures if v.get('anomaly_detected'))}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()