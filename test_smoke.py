"""Базовые проверки ChatList (этап 8 PLAN.md)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import export
import models
import network


class ChatListSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._original_db_path = db.DB_PATH
        db.DB_PATH = Path(self._tmpdir.name) / "test_chatlist.db"
        db.init_db()

    def tearDown(self) -> None:
        db.DB_PATH = self._original_db_path
        self._tmpdir.cleanup()

    def test_init_db_creates_tables(self) -> None:
        with db.get_connection() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertTrue(
            {"prompts", "models", "results", "settings"}.issubset(tables)
        )

    def test_seed_openrouter_models(self) -> None:
        all_models = models.get_all_models()
        self.assertGreaterEqual(len(all_models), 3)
        for model in all_models:
            self.assertIn("openrouter.ai", model.api_url)
            self.assertTrue(network.is_free_openrouter_model(model.api_id))

    def test_prompt_crud_and_search(self) -> None:
        models.save_prompt("Тестовый промт", "test")
        rows = models.load_prompts("Тестовый")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].tags, "test")

    def test_save_selected_results(self) -> None:
        session = models.ChatSession()
        session.set_current_prompt("Промт для сохранения", tags="demo")
        active = models.get_active_models()
        self.assertGreater(len(active), 0)
        model = active[0]
        session.add_temp_result(model.name, model.id, "Ответ 1", selected=True)
        count = models.save_selected_results(session)
        self.assertEqual(count, 1)
        saved = models.load_results()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].response, "Ответ 1")

    def test_export_formats(self) -> None:
        item = models.TempResult(
            model_name="Test Model",
            model_id=1,
            prompt_id=None,
            prompt_text="Hello",
            response="World",
            selected=True,
        )
        md = export.temp_results_to_markdown("Hello", [item])
        js = export.temp_results_to_json("Hello", [item])
        self.assertIn("Test Model", md)
        self.assertIn('"model_name": "Test Model"', js)

    def test_send_prompt_without_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            model = models.get_active_models()[0]
            response = network.send_prompt(model, "ping", timeout=5, env_file=".env.missing")
            self.assertTrue(response.startswith("Ошибка:"))

    def test_migration_keeps_openrouter_models(self) -> None:
        db.init_db()
        names = {model.name for model in models.get_all_models()}
        self.assertIn("OpenRouter Free", names)

    def test_ui_settings_defaults(self) -> None:
        self.assertEqual(models.get_ui_theme(), "light")
        self.assertEqual(models.get_ui_font_size(), 10)
        models.save_settings({"theme": "dark", "ui_font_size": "14"})
        self.assertEqual(models.get_ui_theme(), "dark")
        self.assertEqual(models.get_ui_font_size(), 14)


if __name__ == "__main__":
    unittest.main()
