import unittest
from datetime import date
from models import ApplicationRecord, ApplicationMilestone, Job
from ui.schedule_responsive import mobile_schedule_html

class ResponsiveScheduleTest(unittest.TestCase):
    def test_all_dates_states_order_and_safe_actions(self):
        rows = [ApplicationMilestone(id=1,title='完了済み',status='completed',scheduled_date='2026-09-10',completed_at='2026-09-11T10:00:00'),
                ApplicationMilestone(id=2,title='未定',scheduled_date=None),
                ApplicationMilestone(id=3,title='<未完了>',scheduled_date='2026-09-16'),
                ApplicationMilestone(id=4,title='超過',scheduled_date='2026-09-12')]
        view = dict(application=ApplicationRecord(id=9,job_id=7),job=Job(company_name='<会社>'),milestones=rows)
        html = mobile_schedule_html([view], date(2026,9,13))
        for text in ('日程未定','完了日：2026/9/11（金）','2026/9/16（水）','あと3日','期限超過・1日経過','完了','&lt;会社&gt;','&lt;未完了&gt;', 'data-calendar-application="9"'):
            self.assertIn(text, html)
        self.assertLess(html.index('超過</strong>'),html.index('&lt;未完了&gt;'))
        self.assertIn('mobile-calendar-undated',html)
        self.assertNotIn('<会社>',html)

    def test_empty_company_keeps_action_and_missing_date_does_not_crash(self):
        view = dict(application=ApplicationRecord(id=9,job_id=7),job=Job(company_name='会社'),milestones=[])
        self.assertIn('この日の予定はありません',mobile_schedule_html([view]))
        self.assertIn('日程未定の予定はありません',mobile_schedule_html([view]))
