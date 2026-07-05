from __future__ import annotations

import unittest
from unittest import mock

from long_memory_test.llm import DEFAULT_DEEPSEEK_MODEL, get_llm_config


class LLMConfigTests(unittest.TestCase):
    def test_default_provider_is_deepseek_when_unset(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "DEEPSEEK_API_KEY": "test-deepseek-key",
            },
            clear=True,
        ), mock.patch("long_memory_test.llm.load_dotenv_local"):
            config = get_llm_config()

        self.assertEqual(config.provider, "deepseek")
        self.assertEqual(config.base_url, "https://api.deepseek.com")
        self.assertEqual(config.model, DEFAULT_DEEPSEEK_MODEL)
        self.assertEqual(config.api_key, "test-deepseek-key")


if __name__ == "__main__":
    unittest.main()
