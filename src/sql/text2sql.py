"""
src/sql/text2sql.py
====================
Text-to-SQL engine with schema-aware prompting and self-correction loop.

The self-correction loop:
  1. Generate SQL from natural language
  2. Execute against database
  3. If execution fails, feed the error back to the LLM to fix
  4. Retry up to max_retries times
  5. Return result or explain why it failed

Safety layer: blocks all destructive SQL (DROP, DELETE, TRUNCATE, etc.)
so business users can query safely without DBA supervision.
"""

import re
import json
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class SchemaInfo:
    """Database schema information for prompt context."""
    tables: Dict[str, List[Dict]]   # table_name → [{column, type, nullable, pk}]
    sample_rows: Dict[str, List[Dict]] = field(default_factory=dict)  # table → 3 sample rows

    def to_prompt_string(self) -> str:
        """Format schema as a readable string for the LLM prompt."""
        parts = []
        for table, columns in self.tables.items():
            col_defs = ", ".join(
                f"{c['name']} {c['type']}" + (" PRIMARY KEY" if c.get('pk') else "")
                for c in columns
            )
            parts.append(f"Table: {table} ({col_defs})")
            if table in self.sample_rows and self.sample_rows[table]:
                sample = self.sample_rows[table][0]
                parts.append(f"  Sample: {sample}")
        return "\n".join(parts)


@dataclass
class SQLResult:
    """Result of a text-to-SQL query."""
    question:     str
    sql:          str
    rows:         List[Dict]
    columns:      List[str]
    row_count:    int
    success:      bool
    error:        Optional[str]  = None
    attempts:     int            = 1
    explanation:  Optional[str]  = None  # Plain-English explanation of the result

    def to_dict(self) -> Dict:
        return {
            "question":    self.question,
            "sql":         self.sql,
            "columns":     self.columns,
            "rows":        self.rows[:100],  # cap at 100 rows in response
            "row_count":   self.row_count,
            "success":     self.success,
            "error":       self.error,
            "attempts":    self.attempts,
            "explanation": self.explanation,
        }


# ── Safety Layer ──────────────────────────────────────────────────────────

BLOCKED_PATTERNS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b',
    r'\bALTER\b', r'\bCREATE\b', r'\bINSERT\b',
    r'\bUPDATE\b', r'\bGRANT\b',  r'\bREVOKE\b',
]


def is_safe_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """Check SQL for destructive operations."""
    upper = sql.upper()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, upper):
            op = re.search(pattern, upper).group()
            return False, f"Blocked: {op} statements are not allowed. Only SELECT queries are permitted."
    return True, None


# ── Prompts ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert SQL query generator.
Generate valid, safe SQL SELECT queries from natural language questions.

Rules:
1. Only generate SELECT statements — never INSERT, UPDATE, DELETE, DROP, etc.
2. Use the exact table and column names from the schema
3. Add appropriate WHERE clauses, JOINs, GROUP BY, ORDER BY as needed
4. Use aliases for readability in complex queries
5. Prefer LIMIT 100 for open-ended queries to avoid returning millions of rows

Return ONLY JSON:
{"sql": "<sql query>", "explanation": "<one sentence explaining what this query returns>"}"""


def build_generation_prompt(question: str, schema: SchemaInfo, dialect: str = "sqlite") -> str:
    return f"""Database schema ({dialect}):
{schema.to_prompt_string()}

Question: {question}

Generate a SQL SELECT query. Return JSON only."""


def build_correction_prompt(question: str, sql: str, error: str, schema: SchemaInfo) -> str:
    return f"""This SQL query failed with an error. Fix it.

Original question: {question}

Failed SQL:
{sql}

Error message:
{error}

Schema:
{schema.to_prompt_string()}

Return the corrected query as JSON: {{"sql": "<fixed sql>", "explanation": "<what changed>"}}"""


# ── Text2SQL Engine ───────────────────────────────────────────────────────

class Text2SQLEngine:
    """
    Converts natural language to SQL with self-correction.

    Workflow:
      question → generate SQL → execute → [if error: fix + retry] → return result
    """

    def __init__(self, llm, db_path: str, max_retries: int = 3, dialect: str = "sqlite"):
        self.llm         = llm
        self.db_path     = db_path
        self.max_retries = max_retries
        self.dialect     = dialect
        self.schema      = self._extract_schema()

    def query(self, question: str) -> SQLResult:
        """Convert natural language question to SQL and execute it."""
        logger.info(f"Query: {question}")

        # Generate initial SQL
        sql, explanation = self._generate_sql(question)
        if not sql:
            return SQLResult(question=question, sql="", rows=[], columns=[],
                             row_count=0, success=False, error="Failed to generate SQL")

        # Self-correction loop
        for attempt in range(1, self.max_retries + 1):
            # Safety check
            safe, safety_error = is_safe_sql(sql)
            if not safe:
                return SQLResult(question=question, sql=sql, rows=[], columns=[],
                                 row_count=0, success=False, error=safety_error, attempts=attempt)

            # Execute
            rows, columns, error = self._execute_sql(sql)

            if error is None:
                logger.info(f"Query succeeded on attempt {attempt}: {len(rows)} rows")
                return SQLResult(
                    question    = question,
                    sql         = sql,
                    rows        = rows,
                    columns     = columns,
                    row_count   = len(rows),
                    success     = True,
                    attempts    = attempt,
                    explanation = explanation,
                )

            if attempt < self.max_retries:
                logger.warning(f"Attempt {attempt} failed: {error}. Correcting...")
                sql, explanation = self._correct_sql(question, sql, error)
            else:
                return SQLResult(question=question, sql=sql, rows=[], columns=[],
                                 row_count=0, success=False, error=error, attempts=attempt)

        return SQLResult(question=question, sql=sql, rows=[], columns=[],
                         row_count=0, success=False, error="Max retries exceeded")

    def _generate_sql(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        prompt = build_generation_prompt(question, self.schema, self.dialect)
        try:
            raw  = self.llm.generate(SYSTEM_PROMPT, prompt)
            data = self._parse_json(raw)
            return data.get("sql"), data.get("explanation")
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return None, None

    def _correct_sql(self, question: str, sql: str, error: str) -> Tuple[Optional[str], Optional[str]]:
        prompt = build_correction_prompt(question, sql, error, self.schema)
        try:
            raw  = self.llm.generate(SYSTEM_PROMPT, prompt)
            data = self._parse_json(raw)
            return data.get("sql", sql), data.get("explanation")
        except Exception as e:
            logger.error(f"SQL correction failed: {e}")
            return sql, None

    def _execute_sql(self, sql: str) -> Tuple[List[Dict], List[str], Optional[str]]:
        """Execute SQL against the database. Returns (rows, columns, error)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows    = [dict(row) for row in cursor.fetchmany(1000)]  # max 1000 rows
            conn.close()
            return rows, columns, None
        except sqlite3.Error as e:
            return [], [], str(e)

    def _extract_schema(self) -> SchemaInfo:
        """Extract schema from the database."""
        conn   = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {}
        samples = {}

        for (table_name,) in cursor.fetchall():
            cursor.execute(f"PRAGMA table_info({table_name})")
            cols = [{"name": r[1], "type": r[2], "nullable": not r[3], "pk": bool(r[5])}
                    for r in cursor.fetchall()]
            tables[table_name] = cols
            # Get 2 sample rows
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                col_names = [d[0] for d in cursor.description]
                samples[table_name] = [dict(zip(col_names, row)) for row in cursor.fetchall()]
            except:
                pass

        conn.close()
        return SchemaInfo(tables=tables, sample_rows=samples)

    def _parse_json(self, text: str) -> Dict:
        clean = re.sub(r"```(?:json)?|```", "", text).strip()
        try:
            return json.loads(clean)
        except:
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return {}
