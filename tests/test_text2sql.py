"""
tests/test_text2sql.py — Unit tests for Text-to-SQL engine
"""
import sys, os, sqlite3, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sql.text2sql import is_safe_sql, Text2SQLEngine, SchemaInfo


# ── Safety tests ──────────────────────────────────────────────────────────

def test_safe_select():
    safe, err = is_safe_sql("SELECT * FROM users WHERE id = 1")
    assert safe is True and err is None
    print("✅ SELECT is safe")

def test_block_drop():
    safe, err = is_safe_sql("DROP TABLE users")
    assert safe is False
    assert "DROP" in err
    print("✅ DROP is blocked")

def test_block_delete():
    safe, err = is_safe_sql("DELETE FROM orders WHERE id = 1")
    assert safe is False
    print("✅ DELETE is blocked")

def test_block_insert():
    safe, err = is_safe_sql("INSERT INTO users VALUES (1, 'hacked')")
    assert safe is False
    print("✅ INSERT is blocked")

def test_block_update():
    safe, err = is_safe_sql("UPDATE users SET admin=1 WHERE id=1")
    assert safe is False
    print("✅ UPDATE is blocked")

def test_case_insensitive_block():
    safe, err = is_safe_sql("drop table users")
    assert safe is False
    print("✅ lowercase DROP is blocked")

def test_select_with_join_is_safe():
    sql = "SELECT o.id, c.name FROM orders o JOIN customers c ON o.customer_id = c.id"
    safe, err = is_safe_sql(sql)
    assert safe is True
    print("✅ SELECT with JOIN is safe")


# ── Schema extraction tests ───────────────────────────────────────────────

def make_test_db():
    """Create an in-memory SQLite DB for testing."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.executescript("""
        CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, stock INTEGER);
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT, country TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL, status TEXT);
        INSERT INTO products VALUES (1,'Widget',9.99,100),(2,'Gadget',49.99,50);
        INSERT INTO customers VALUES (1,'Alice','alice@test.com','USA'),(2,'Bob','bob@test.com','UK');
        INSERT INTO orders VALUES (1,1,9.99,'delivered'),(2,2,49.99,'shipped');
    """)
    conn.commit()
    conn.close()
    return tmp.name

class MockLLM:
    def __init__(self, sql, explanation="Test query"):
        self._sql  = sql
        self._expl = explanation
    def generate(self, system, user):
        import json
        return json.dumps({"sql": self._sql, "explanation": self._expl})

def test_schema_extraction():
    db = make_test_db()
    engine = Text2SQLEngine(MockLLM("SELECT 1"), db)
    schema = engine.schema
    assert "products"  in schema.tables
    assert "customers" in schema.tables
    assert "orders"    in schema.tables
    assert any(c["name"] == "name" for c in schema.tables["products"])
    print("✅ schema extraction correct")
    os.unlink(db)

def test_successful_query():
    db     = make_test_db()
    engine = Text2SQLEngine(MockLLM("SELECT * FROM products"), db)
    result = engine.query("Show me all products")
    assert result.success is True
    assert result.row_count == 2
    assert "name" in result.columns
    print(f"✅ successful query: {result.row_count} rows")
    os.unlink(db)

def test_self_correction():
    """Engine should fix broken SQL on retry."""
    call_count = [0]
    class RetryLLM:
        def generate(self, system, user):
            import json
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({"sql": "SELECT * FROM nonexistent_table", "explanation": "bad"})
            return json.dumps({"sql": "SELECT * FROM products", "explanation": "fixed"})
    db     = make_test_db()
    engine = Text2SQLEngine(RetryLLM(), db, max_retries=3)
    result = engine.query("Show me products")
    assert result.success is True
    assert result.attempts == 2
    print(f"✅ self-correction works: fixed on attempt {result.attempts}")
    os.unlink(db)

def test_blocked_sql_from_llm():
    """If LLM generates a destructive query, it should be blocked."""
    db     = make_test_db()
    engine = Text2SQLEngine(MockLLM("DROP TABLE products"), db)
    result = engine.query("Delete all products")
    assert result.success is False
    assert "Blocked" in result.error
    print("✅ destructive LLM output blocked by safety layer")
    os.unlink(db)

def test_schema_to_prompt_string():
    schema = SchemaInfo(tables={"users": [
        {"name": "id",    "type": "INTEGER", "pk": True, "nullable": False},
        {"name": "email", "type": "TEXT",    "pk": False,"nullable": True},
    ]})
    s = schema.to_prompt_string()
    assert "users" in s
    assert "id" in s
    assert "email" in s
    print("✅ schema formats correctly for prompt")


if __name__ == "__main__":
    tests = [
        test_safe_select, test_block_drop, test_block_delete,
        test_block_insert, test_block_update, test_case_insensitive_block,
        test_select_with_join_is_safe, test_schema_extraction,
        test_successful_query, test_self_correction,
        test_blocked_sql_from_llm, test_schema_to_prompt_string,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
