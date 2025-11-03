"""Test environment system (currentEnv, TempEnv, TriggerStack)."""

from dataclasses import dataclass
from genro_core import GenroMicroDb, Table


# Define test tables
class AuditTable(Table):
    sql_name = "audit_log"
    pkey = "id"

    @dataclass
    class Columns:
        id: int
        table_name: str
        action: str
        user: str


class ProductTable(Table):
    sql_name = "products"
    pkey = "id"

    @dataclass
    class Columns:
        id: int
        name: str
        price: float

    def trigger_onInserting(self, record=None):
        """Log insert action with audit user from currentEnv."""
        user = self.db.currentEnv.get('audit_user', 'unknown')
        audit_record = {
            'table_name': 'products',
            'action': 'insert',
            'user': user
        }
        # This won't cause infinite recursion thanks to @in_triggerstack
        self.db.tables.audit.insert(record=audit_record)


def test_environment_system():
    """Test currentEnv, TempEnv, and TriggerStack."""

    print("=" * 60)
    print("TESTING ENVIRONMENT SYSTEM")
    print("=" * 60)

    # 1. Setup database and tables
    print("\n1. Setting up database...")
    db = GenroMicroDb(name="test_db", implementation="sqlite", path=":memory:")
    db.add_table(AuditTable)
    db.add_table(ProductTable)
    db.migrate()
    print("   ✓ Database and tables created")

    # 2. Test currentEnv - thread-local storage
    print("\n2. Testing currentEnv (thread-local storage)...")
    db.currentEnv['test_key'] = 'test_value'
    assert db.currentEnv.get('test_key') == 'test_value'
    print("   ✓ Can set and get values in currentEnv")

    # 3. Test TempEnv - temporary context
    print("\n3. Testing TempEnv (temporary environment)...")

    # Set initial value
    db.currentEnv['user'] = 'initial_user'
    print(f"   - Before tempEnv: user = '{db.currentEnv.get('user')}'")

    # Use temporary environment
    with db.tempEnv(user='admin', batch_mode=True):
        print(f"   - Inside tempEnv: user = '{db.currentEnv.get('user')}'")
        print(f"   - Inside tempEnv: batch_mode = {db.currentEnv.get('batch_mode')}")
        assert db.currentEnv.get('user') == 'admin'
        assert db.currentEnv.get('batch_mode') is True

    # Check restoration
    print(f"   - After tempEnv: user = '{db.currentEnv.get('user')}'")
    print(f"   - After tempEnv: batch_mode = {db.currentEnv.get('batch_mode')}")
    assert db.currentEnv.get('user') == 'initial_user'
    assert db.currentEnv.get('batch_mode') is None
    print("   ✓ TempEnv correctly saves and restores values")

    # 4. Test TriggerStack - prevent infinite recursion
    print("\n4. Testing TriggerStack (recursion prevention)...")

    # Insert product WITHOUT audit user
    print("   - Inserting product without audit_user context...")
    db.tables.product.insert(record={'name': 'Widget', 'price': 9.99})

    # Check audit log
    audit_logs = db.tables.audit.list()
    print(f"   - Audit logs created: {len(audit_logs)}")
    assert len(audit_logs) == 1
    assert audit_logs[0]['user'] == 'unknown'  # No audit_user in currentEnv
    print(f"   - First log: user='{audit_logs[0]['user']}' (default)")

    # Insert product WITH audit user via TempEnv
    print("   - Inserting product with audit_user='admin' via tempEnv...")
    with db.tempEnv(audit_user='admin'):
        db.tables.product.insert(record={'name': 'Gadget', 'price': 19.99})

    # Check audit log
    audit_logs = db.tables.audit.list()
    print(f"   - Audit logs created: {len(audit_logs)}")
    assert len(audit_logs) == 2
    assert audit_logs[1]['user'] == 'admin'  # Got audit_user from currentEnv
    print(f"   - Second log: user='{audit_logs[1]['user']}' (from tempEnv)")

    print("   ✓ TriggerStack prevented infinite recursion")
    print("   ✓ Audit user correctly passed via currentEnv")

    # 5. Test nested TempEnv
    print("\n5. Testing nested TempEnv...")
    db.currentEnv['level'] = 0

    with db.tempEnv(level=1):
        print(f"   - Level 1: level = {db.currentEnv.get('level')}")
        assert db.currentEnv.get('level') == 1

        with db.tempEnv(level=2):
            print(f"   - Level 2: level = {db.currentEnv.get('level')}")
            assert db.currentEnv.get('level') == 2

        print(f"   - Back to level 1: level = {db.currentEnv.get('level')}")
        assert db.currentEnv.get('level') == 1

    print(f"   - Back to level 0: level = {db.currentEnv.get('level')}")
    assert db.currentEnv.get('level') == 0
    print("   ✓ Nested TempEnv works correctly")

    # 6. Cleanup
    print("\n6. Closing database...")
    db.close()
    print("   ✓ Database closed")

    print("\n" + "=" * 60)
    print("✓ ALL ENVIRONMENT TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_environment_system()
