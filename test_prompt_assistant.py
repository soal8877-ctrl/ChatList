"""Тесты AI-ассистента для улучшения промтов."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import models
import prompt_assistant


class PromptAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._original_db_path = db.DB_PATH
        db.DB_PATH = Path(self._tmpdir.name) / "test_chatlist.db"
        db.init_db()

    def tearDown(self) -> None:
        db.DB_PATH = self._original_db_path
        self._tmpdir.cleanup()

    def test_parse_valid_json(self) -> None:
        payload = {
            "improved": "Улучшенный промт",
            "alternatives": ["Вариант 1", "Вариант 2"],
            "adaptations": {
                "code": "Кодовый промт",
                "analysis": "Аналитический промт",
                "creative": "Креативный промт",
            },
        }
        result = prompt_assistant.parse_assistant_response(
            json.dumps(payload, ensure_ascii=False),
            "Исходный",
        )
        self.assertEqual(result.improved, "Улучшенный промт")
        self.assertEqual(len(result.alternatives), 2)
        self.assertEqual(len(result.adaptations), 3)

    def test_parse_json_in_code_block(self) -> None:
        raw = """```json
{"improved": "Better", "alternatives": ["A", "B"], "adaptations": {}}
```"""
        result = prompt_assistant.parse_assistant_response(raw, "Original")
        self.assertEqual(result.improved, "Better")
        self.assertEqual(len(result.alternatives), 2)

    def test_parse_invalid_json_fallback(self) -> None:
        result = prompt_assistant.parse_assistant_response(
            "Просто текст без JSON",
            "Исходный",
        )
        self.assertEqual(result.improved, "Просто текст без JSON")
        self.assertEqual(result.original, "Исходный")

    def test_improve_prompt_empty(self) -> None:
        model = models.get_assistant_model()
        assert model is not None
        result = prompt_assistant.improve_prompt("   ", model)
        self.assertIsInstance(result, str)
        self.assertIn("пуст", result.lower())

    def test_improve_prompt_with_mock(self) -> None:
        model = models.get_assistant_model()
        assert model is not None
        payload = {
            "improved": "Explain median clearly",
            "alternatives": ["Define median", "What is median?"],
            "adaptations": {"code": "", "analysis": "Analyze median", "creative": ""},
        }

        with patch(
            "prompt_assistant.network.send_chat",
            return_value=json.dumps(payload),
        ):
            result = prompt_assistant.improve_prompt("median?", model)

        self.assertIsInstance(result, prompt_assistant.PromptImprovementResult)
        assert isinstance(result, prompt_assistant.PromptImprovementResult)
        self.assertEqual(result.improved, "Explain median clearly")
        self.assertEqual(len(result.alternatives), 2)

    def test_get_assistant_model_default(self) -> None:
        model = models.get_assistant_model()
        self.assertIsNotNone(model)
        assert model is not None
        self.assertTrue(model.is_active or model.name)

    def test_assistant_disabled(self) -> None:
        models.save_settings({"assistant_enabled": "0"})
        self.assertIsNone(models.get_assistant_model())


if __name__ == "__main__":
    unittest.main()
