"""Tests for the opt-in free-model -> credit-sibling fallback (6004)."""
import inspect
import os
import tempfile
import unittest

import wb_proxy
import wb_settings


class FreeModelCreditFallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="credit-fb-")
        self.orig_dir = wb_proxy.ACCOUNTS_DIR
        wb_proxy.ACCOUNTS_DIR = self.tmp
        self._saved_env = os.environ.pop("WB_ENABLE_FREE_MODEL_CREDIT_FALLBACK", None)

    def tearDown(self):
        wb_proxy.ACCOUNTS_DIR = self.orig_dir
        if self._saved_env is None:
            os.environ.pop("WB_ENABLE_FREE_MODEL_CREDIT_FALLBACK", None)
        else:
            os.environ["WB_ENABLE_FREE_MODEL_CREDIT_FALLBACK"] = self._saved_env

    def test_mapping_is_realm_model_pair(self):
        # The map is keyed by (realm, base model id) and points at the paid sibling.
        self.assertIn(("intl", "deepseek-v4.1-flash"), wb_proxy._FREE_MODEL_CREDIT_FALLBACKS)
        paid = wb_proxy._FREE_MODEL_CREDIT_FALLBACKS[("intl", "deepseek-v4.1-flash")]
        self.assertNotEqual(paid, "deepseek-v4.1-flash")
        self.assertTrue(paid.startswith("deepseek-v4.1-flash"))

    def test_settings_roundtrip_defaults_off(self):
        # Default must be off: the retry can incur real charges.
        self.assertFalse(wb_settings.free_model_credit_fallback(self.tmp))
        self.assertTrue(wb_settings.set_free_model_credit_fallback(self.tmp, True))
        self.assertTrue(wb_settings.free_model_credit_fallback(self.tmp))
        self.assertFalse(wb_settings.set_free_model_credit_fallback(self.tmp, False))
        self.assertFalse(wb_settings.free_model_credit_fallback(self.tmp))

    def test_enabled_flag_defaults_off_and_honours_both_switches(self):
        self.assertFalse(wb_proxy._free_model_credit_fallback_enabled())

        os.environ["WB_ENABLE_FREE_MODEL_CREDIT_FALLBACK"] = "1"
        self.assertTrue(wb_proxy._free_model_credit_fallback_enabled())
        del os.environ["WB_ENABLE_FREE_MODEL_CREDIT_FALLBACK"]

        wb_settings.set_free_model_credit_fallback(self.tmp, True)
        self.assertTrue(wb_proxy._free_model_credit_fallback_enabled())
        wb_settings.set_free_model_credit_fallback(self.tmp, False)
        self.assertFalse(wb_proxy._free_model_credit_fallback_enabled())

    def test_open_upstream_exposes_opt_out_parameter(self):
        # The recursive retry passes allow_credit_fallback=False to prevent a
        # second hop; the parameter has to exist and default to True so existing
        # callers are unaffected.
        sig = inspect.signature(wb_proxy.open_upstream)
        self.assertIn("allow_credit_fallback", sig.parameters)
        self.assertIs(sig.parameters["allow_credit_fallback"].default, True)

    def test_settings_persist_boolean(self):
        # The setter coerces to bool, so whatever the route accepts is stored
        # as a real boolean and read back consistently.
        self.assertFalse(wb_settings.free_model_credit_fallback(self.tmp))
        wb_settings.set_free_model_credit_fallback(self.tmp, "yes")
        self.assertTrue(wb_settings.free_model_credit_fallback(self.tmp))


if __name__ == "__main__":
    unittest.main()
