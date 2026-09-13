import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from contextlib import nullcontext
from ui import job_evaluation_area as area


class EvaluationAreaTest(unittest.TestCase):
    def test_idle_does_not_read_database_and_changed_result_is_refreshed(self):
        fake=Mock(); fake.session_state={}; fake.container.return_value=nullcontext()
        functions=[]
        def fragment(**kwargs):
            def decorate(function):
                functions.append(function)
                return function
            return decorate
        fake.fragment.side_effect=lambda function: (functions.append(function) or function)
        completed=SimpleNamespace(evaluation_status='completed',is_stale=False)
        ready=SimpleNamespace(evaluation_status='ready',is_stale=True)
        running=SimpleNamespace(evaluation_status='running',is_stale=False)
        initial=dict(job=object(),evaluations={10:completed})
        score=Mock(); detail=Mock()
        with patch.object(area,'st',fake), patch.object(area,'_poll'), patch.object(area,'load_area_updates') as load, patch.object(area,'enqueue_job_evaluation') as enqueue:
            area.render_evaluation_area(10,initial,score,detail)
            functions[0]()
            load.assert_not_called()
            fake.session_state['confirmation_refresh_10']=True
            load.return_value={'evaluations':{10:ready}}
            functions[0]()
            enqueue.assert_called_once_with(10)
            load.return_value={'evaluations':{10:running}}
            functions[0]()
            load.return_value={'evaluations':{10:completed}}
            functions[0]()
            self.assertIs(score.call_args.kwargs['evaluations'][10],completed)
            count=load.call_count
            functions[0]()
            self.assertEqual(load.call_count,count)
            fake.rerun.assert_not_called()
            detail.assert_called_once()  # AIのポーリングでフォームを再描画しない。

    def test_confirmation_refresh_requests_local_scope(self):
        with patch.object(area.st,'session_state',{}), patch.object(area,'rerun_current_page') as rerun:
            area.refresh_confirmation_area(10)
            self.assertTrue(area.st.session_state['confirmation_refresh_10'])
            rerun.assert_called_once()

    def test_saved_confirmation_refreshes_only_detail_and_clears_actions(self):
        fake=Mock(); fake.session_state={}; fake.container.return_value=nullcontext()
        functions=[]
        fake.fragment.side_effect=lambda fn:(functions.append(fn) or fn)
        completed=SimpleNamespace(evaluation_status='completed',is_stale=False)
        detail=Mock(); score=Mock()
        rows=[dict(item_key='a',status='not_required')]
        with patch.object(area,'st',fake), patch.object(area,'_poll'), patch.object(area,'load_confirmation_records',return_value=rows) as load, patch.object(area,'notify_evaluation_saved') as notify:
            area.render_evaluation_area(10,dict(job=object(),evaluations={10:completed},confirmation_records=[]),score,detail)
            fake.session_state.update(confirmation_detail_saved_10=1,batch_10_a_action=True,batch_10_b_notes='保持する入力')
            functions[1]()
            self.assertEqual(detail.call_args.kwargs['snapshot']['resolutions'],{'a':'not_required'})
            self.assertNotIn('batch_10_a_action',fake.session_state)
            self.assertEqual(fake.session_state['batch_10_b_notes'],'保持する入力')
            score.assert_called_once()
            load.assert_called_once_with(10)
            notify.assert_called_once_with(10)
