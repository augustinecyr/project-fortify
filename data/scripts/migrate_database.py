"""
Database migration script for Project Fortify.
Adds enhanced VM parameters to existing virtual_machines table.

Run this ONCE to upgrade your existing database.
"""
import sys
from pathlib import Path

# Add parent directories to path
project_root = Path(__file__).resolve().parents[2]
api_path = project_root / "api"
sys.path.insert(0, str(api_path))

from sqlalchemy import text
from app.db.database import engine, SessionLocal


def check_column_exists(table_name: str, column_name: str, db) -> bool:
    """Check if a column exists in a table."""
    result = db.execute(text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='{table_name}' 
        AND column_name='{column_name}'
    """))
    return result.fetchone() is not None


def migrate_database():
    """Add new columns to virtual_machines table."""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("PROJECT FORTIFY - DATABASE MIGRATION")
        print("=" * 70)
        print("\nAdding enhanced parameters to virtual_machines table...\n")
        
        table_name = "virtual_machines"
        columns_added = 0
        columns_skipped = 0
        
        # List of columns to add with their SQL definitions
        new_columns = [
            # Infrastructure & Host Information
            ("host", "VARCHAR"),
            ("os_version", "VARCHAR"),
            ("status", "VARCHAR DEFAULT 'online'"),
            
            # Uptime & Boot Information
            ("uptime_hours", "FLOAT"),
            ("last_boot_time", "TIMESTAMP"),
            
            # Health & Security Scores
            ("health_score", "INTEGER"),
            ("security_score", "INTEGER"),
            
            # Current Resource Utilization
            ("current_cpu", "FLOAT"),
            ("current_memory", "FLOAT"),
            ("current_disk", "FLOAT"),
            
            # Memory Metrics
            ("memory_total_mb", "INTEGER"),
            ("memory_used_mb", "INTEGER"),
            
            # Disk Metrics
            ("disk_total_gb", "INTEGER"),
            ("disk_used_gb", "INTEGER"),
            
            # Network Metrics
            ("network_in_mbps", "FLOAT"),
            ("network_out_mbps", "FLOAT"),
            
            # Security & Compliance
            ("last_patch_date", "TIMESTAMP"),
            ("open_vulnerabilities", "INTEGER DEFAULT 0"),
            ("critical_vulnerabilities", "INTEGER DEFAULT 0"),
            ("compliance_score", "VARCHAR"),
            ("firewall_enabled", "BOOLEAN DEFAULT TRUE"),
            ("ssh_key_auth", "BOOLEAN DEFAULT TRUE"),
            ("disk_encryption", "BOOLEAN DEFAULT FALSE"),
            
            # Alerts & Monitoring
            ("alert_count", "INTEGER DEFAULT 0"),
            ("anomaly_detected", "BOOLEAN DEFAULT FALSE"),
            ("last_anomaly_time", "TIMESTAMP"),
            
            # 24-hour Aggregated Metrics
            ("avg_cpu_24h", "FLOAT"),
            ("avg_memory_24h", "FLOAT"),
            ("avg_disk_24h", "FLOAT"),
            ("peak_cpu_24h", "FLOAT"),
            ("metric_count_24h", "INTEGER DEFAULT 0"),
            
            # Metadata
            ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]
        
        for column_name, column_type in new_columns:
            # Check if column already exists
            if check_column_exists(table_name, column_name, db):
                print(f"  ⏭️  {column_name:<25} (already exists)")
                columns_skipped += 1
                continue
            
            # Add the column
            try:
                db.execute(text(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN {column_name} {column_type}
                """))
                db.commit()
                print(f"  ✅ {column_name:<25} ({column_type})")
                columns_added += 1
            except Exception as e:
                print(f"  ❌ {column_name:<25} (ERROR: {str(e)})")
                db.rollback()
        
        # Add indexes for commonly queried columns
        print("\nAdding indexes...")
        indexes = [
            ("idx_vm_host", "host"),
            ("idx_vm_status", "status"),
            ("idx_vm_health_score", "health_score"),
            ("idx_vm_security_score", "security_score"),
        ]
        
        for index_name, column_name in indexes:
            try:
                db.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} ({column_name})
                """))
                db.commit()
                print(f"  ✅ {index_name}")
            except Exception as e:
                print(f"  ⏭️  {index_name} (already exists or error)")
                db.rollback()
        
        print("\n" + "=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print(f"✅ Columns added:   {columns_added}")
        print(f"⏭️  Columns skipped: {columns_skipped}")
        print(f"📊 Total columns:   {columns_added + columns_skipped}")
        print("=" * 70)
        
        if columns_added > 0:
            print("\n⚠️  NEXT STEPS:")
            print("1. Run seed_database.py to populate new fields")
            print("2. Restart your API server")
            print("3. Refresh your dashboard\n")
        else:
            print("\n✅ Database is already up to date!\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will modify your database schema.")
    print("Make sure you have a backup before proceeding.\n")
    
    response = input("Continue with migration? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        migrate_database()
    else:
        print("Migration cancelled.")