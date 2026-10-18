"""Offline notebook regressions; no Fabric credentials or Spark required."""

import ast
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = json.loads((ROOT / "setup" / "Setup-InventoryDataAgent.ipynb").read_text(encoding="utf-8"))
CELLS = {cell["id"]: "".join(cell["source"]) for cell in NOTEBOOK["cells"]}
SETUP = ast.parse(CELLS["88b3cac5"])


def setup_namespace():
    names = {"AGENT_INSTRUCTIONS", "DATA_SOURCE_INSTRUCTIONS", "EXAMPLE_QUERIES", "EXPECTED_TABLES"}
    nodes = [
        node for node in SETUP.body
        if isinstance(node, ast.FunctionDef)
        or isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in names for target in node.targets)
    ]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<setup-definitions>", "exec"), namespace)
    return namespace


class DataSource:
    def __init__(self, tables):
        self.tables = tables
        self.selected = set()
        self.instructions = None
        self.examples = {}

    def get_elements(self, root_id=None, **kwargs):
        if root_id is None:
            return [{"id": "dbo", "type": "schema", "hasSubElements": True}]
        return [
            {"id": name, "name": name, "type": "table", "hasSubElements": False}
            for name in self.tables
        ]

    def update_element(self, element_id, is_selected):
        if not is_selected:
            raise AssertionError("Expected selected table")
        self.selected.add(element_id)

    def update_configuration(self, instructions):
        self.instructions = instructions

    def get_fewshots(self):
        records = [
            {"id": question, "question": question, "query": query}
            for question, query in self.examples.items()
        ]
        return SimpleNamespace(to_dict=lambda orient: records)

    def add_fewshot(self, question, query):
        if question in self.examples:
            raise AssertionError("Duplicate example")
        self.examples[question] = query

    def update_fewshot(self, fewshot_id, query):
        self.examples[fewshot_id] = query


class Agent:
    def __init__(self, sources):
        self.sources = sources
        self.reads = 0
        self.published = False

    def update_settings(self, **kwargs):
        self.settings = kwargs

    def add_staging_datasource(self, **kwargs):
        self.datasource_settings = kwargs

    def list_datasources(self):
        source = self.sources[min(self.reads, len(self.sources) - 1)]
        self.reads += 1
        return [source]

    def publish_staging(self, **kwargs):
        self.published = True


def configure(agent):
    namespace = setup_namespace()
    namespace.update(
        agent=agent, lakehouse_id="lakehouse", workspace_id="workspace",
        time=SimpleNamespace(sleep=lambda seconds: None),
    )
    start = next(
        index for index, node in enumerate(SETUP.body)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "update_settings"
    )
    exec(compile(ast.Module(body=SETUP.body[start:], type_ignores=[]), "<configure>", "exec"), namespace)


class NotebookTests(unittest.TestCase):
    def test_code_cells_compile(self):
        for cell in NOTEBOOK["cells"]:
            if cell["cell_type"] == "code":
                source = "".join(cell["source"])
                source = "\n".join(line for line in source.splitlines() if not line.startswith("%"))
                compile(source, f"<cell {cell['id']}>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

    def test_seed_and_case_sensitive_example_results(self):
        namespace = {}
        exec(CELLS["c1783b44"], namespace)
        exec(CELLS["babc0dba"], namespace)
        self.assertEqual(len(namespace["inventory"]), 72)
        self.assertEqual(len(namespace["demand"]), 288)
        self.assertEqual({row["type"] for row in namespace["stores"]}, {"retail", "warehouse"})
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("ATTACH DATABASE ':memory:' AS dbo")
        for name, rows in (("Stores", namespace["stores"]), ("Products", namespace["products"]),
                           ("Inventory", namespace["inventory"])):
            columns = list(rows[0])
            definitions = ", ".join(
                f"[{key}] {'INTEGER' if isinstance(rows[0][key], int) else 'TEXT COLLATE BINARY'}"
                for key in columns
            )
            connection.execute(f"CREATE TABLE dbo.{name} ({definitions})")
            connection.executemany(
                f"INSERT INTO dbo.{name} VALUES ({','.join('?' for _ in columns)})",
                [tuple(row[key] for key in columns) for row in rows],
            )
        results = [connection.execute(sql).fetchall() for sql in setup_namespace()["EXAMPLE_QUERIES"].values()]
        self.assertEqual(results[0], [(4,)])
        self.assertEqual(results[1], [
            ("P004", "ST03", "Portland", 8, 30, "CRITICAL"),
            ("P004", "ST04", "Seattle", 6, 30, "CRITICAL"),
        ])
        self.assertEqual(results[2], [(232,)])
        self.assertEqual(results[3], [])
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM dbo.Stores WHERE type = 'Retail'").fetchone(), (0,))

    def test_publishes_only_after_all_named_tables_and_grounding(self):
        expected = setup_namespace()["EXPECTED_TABLES"]
        partial = DataSource(sorted(expected)[:6])
        complete = DataSource(sorted(expected))
        agent = Agent([partial, complete])
        configure(agent)
        self.assertEqual(agent.reads, 2)
        self.assertTrue(agent.published)
        self.assertIn("Stores.type is 'retail' or 'warehouse'", complete.instructions)
        self.assertEqual(len(complete.examples), 4)
        configure(agent)
        self.assertEqual(len(complete.examples), 4)

    def test_extra_table_does_not_hide_missing_expected_table(self):
        expected = sorted(setup_namespace()["EXPECTED_TABLES"])
        agent = Agent([DataSource(expected[:6] + ["unrelated"])])
        with self.assertRaisesRegex(RuntimeError, "Missing tables"):
            configure(agent)
        self.assertFalse(agent.published)

    def test_zero_tables_never_publish(self):
        agent = Agent([DataSource([])])
        with self.assertRaisesRegex(RuntimeError, "Missing tables"):
            configure(agent)
        self.assertFalse(agent.published)

    def test_configuration_failure_never_publishes(self):
        class BrokenSource(DataSource):
            def update_configuration(self, instructions):
                raise RuntimeError("configuration denied")
        agent = Agent([BrokenSource(sorted(setup_namespace()["EXPECTED_TABLES"]))])
        with self.assertRaisesRegex(RuntimeError, "configuration denied"):
            configure(agent)
        self.assertFalse(agent.published)

    def test_schema_access_failure_is_not_hidden_as_sync_delay(self):
        class BrokenSource(DataSource):
            def get_elements(self, **kwargs):
                raise PermissionError("schema access denied")
        agent = Agent([BrokenSource([])])
        with self.assertRaisesRegex(PermissionError, "schema access denied"):
            configure(agent)
        self.assertFalse(agent.published)

    def test_manual_and_notebook_grounding_match(self):
        text = (ROOT / "challenges" / "challenge-01.md").read_text(encoding="utf-8")
        block = text.split("Use exact stored values in case-sensitive filters.", 1)[1].split("```", 1)[0]
        manual = "Use exact stored values in case-sensitive filters." + block
        expected = setup_namespace()["DATA_SOURCE_INSTRUCTIONS"]
        self.assertEqual(" ".join(manual.split()), " ".join(expected.split()))

    def test_local_markdown_file_links_resolve(self):
        import re
        from urllib.parse import unquote
        for path in ROOT.rglob("*.md"):
            if ".github" in path.parts:
                continue
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if target.startswith(("https:", "http:", "#", "mailto:")):
                    continue
                target = unquote(target.split("#", 1)[0].strip("<>"))
                self.assertTrue((path.parent / target).exists(), f"{path}: broken link {target}")


if __name__ == "__main__":
    unittest.main()
