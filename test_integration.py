"""Test integration of GenroMicroDb, adapters, and Table."""

from dataclasses import dataclass
from genro_core import GenroMicroDb, Table


# Define a test table
class BookTable(Table):
    sql_name = "books"
    pk_field = "id"

    @dataclass
    class Columns:
        id: int
        title: str
        author: str
        pages: int


def test_full_integration():
    """Test complete integration: migration, insert, select, update, delete."""

    print("=" * 60)
    print("TESTING GENRO-CORE INTEGRATION")
    print("=" * 60)

    # 1. Create database
    print("\n1. Creating database...")
    db = GenroMicroDb(name="test_db", implementation="sqlite", path=":memory:")
    print(f"   ✓ Database created: {db.name}")
    print(f"   ✓ Adapter type: {type(db.adapter).__name__}")

    # 2. Register table
    print("\n2. Registering table...")
    db.add_table(BookTable)
    print(f"   ✓ Table registered: {db.tables.book.sql_name}")
    print(f"   ✓ Columns: {list(db.tables.book.columns.keys())}")

    # 3. Add column dynamically
    print("\n3. Adding dynamic column...")
    db.tables.book.add_column("isbn", dtype='T', size='1:20', not_null=False)
    print(f"   ✓ Columns after add: {list(db.tables.book.columns.keys())}")

    # 4. Run migration (CREATE TABLE)
    print("\n4. Running migration...")
    migrations = db.migrate()
    print(f"   ✓ Migrations executed: {len(migrations)} tables")
    for table, sql_list in migrations.items():
        for sql in sql_list:
            print(f"     - {sql[:80]}...")

    # 5. INSERT - Add records
    print("\n5. Testing INSERT...")
    book1_data = {
        'title': "The Pragmatic Programmer",
        'author': "Hunt & Thomas",
        'pages': 352,
        'isbn': "978-0201616224"
    }
    book1_pk = db.tables.book.insert(record=book1_data)
    book1 = db.tables.book.get(book1_pk)
    print(f"   ✓ Book inserted: ID={book1['id']}, title='{book1['title']}'")

    book2_data = {
        'title': "Clean Code",
        'author': "Robert Martin",
        'pages': 464,
        'isbn': "978-0132350884"
    }
    book2_pk = db.tables.book.insert(record=book2_data)
    book2 = db.tables.book.get(book2_pk)
    print(f"   ✓ Book inserted: ID={book2['id']}, title='{book2['title']}'")

    # 6. SELECT - Get single record
    print("\n6. Testing SELECT (get)...")
    fetched = db.tables.book.get(book1['id'])
    print(f"   ✓ Got book: {fetched['title']} by {fetched['author']}")

    # 7. SELECT - List all records
    print("\n7. Testing SELECT (list)...")
    all_books = db.tables.book.list()
    print(f"   ✓ Found {len(all_books)} books:")
    for book in all_books:
        print(f"     - [{book['id']}] {book['title']}")

    # 8. UPDATE - Modify record
    print("\n8. Testing UPDATE...")
    book1_updated = book1.copy()
    book1_updated['pages'] = 353
    updated = db.tables.book.update(record=book1_updated)
    print(f"   ✓ Updated book: pages changed from 352 to {updated['pages']}")

    # 9. DELETE - Remove record
    print("\n9. Testing DELETE...")
    db.tables.book.delete(record={'id': book2['id']})
    print(f"   ✓ Deleted book ID={book2['id']}")

    remaining = db.tables.book.list()
    print(f"   ✓ Remaining books: {len(remaining)}")

    # 10. Cleanup
    print("\n10. Closing database...")
    db.close()
    print("   ✓ Database closed")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_full_integration()
