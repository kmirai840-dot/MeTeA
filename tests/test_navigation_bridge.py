import unittest
from unittest.mock import patch, Mock
from ui import navigation_bridge as bridge
from ui.page_execution import PENDING_PAGE_KEY

class NavigationBridgeTest(unittest.TestCase):
    def test_preserves_target_parameters(self):
        self.assertEqual(bridge.parse_navigation('?page=job_comparison&job_ids=12%2C34&return_page=job_list'), {'page':'job_comparison','job_ids':'12,34','return_page':'job_list'})
        self.assertEqual(bridge.parse_navigation('?'),{'page':'home'})

    def test_invalid_targets_are_rejected(self):
        for value in (None,{},'https://example.org','?page=unknown','?page=home&x='+'a'*2050):
            with self.subTest(value=type(value)):
                self.assertIsNone(bridge.parse_navigation(value))

    def test_callback_replaces_old_query_without_saving_data(self):
        fake=Mock();fake.session_state={bridge.KEY:{'navigate':'?page=job_detail&job_id=156'}}
        with patch.object(bridge,'st',fake): bridge._on_navigate()
        fake.query_params.from_dict.assert_called_once_with({'page':'job_detail','job_id':'156'})
        self.assertEqual(fake.session_state[PENDING_PAGE_KEY],'job_detail')

    def test_invalid_callback_does_not_change_route(self):
        fake=Mock();fake.session_state={bridge.KEY:{'navigate':'?page=arbitrary'}}
        with patch.object(bridge,'st',fake): bridge._on_navigate()
        fake.query_params.from_dict.assert_not_called()
        self.assertNotIn(PENDING_PAGE_KEY,fake.session_state)
