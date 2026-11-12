import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('compliance', Path(__file__).resolve().parents[1] / 'proposal-agent/compliance.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

class ComplianceTests(unittest.TestCase):
    def record(self):
        return dict(compliance_matrix=[dict(id='C001', category='deadline', requirement='Due Nov 6 at 11 AM Eastern', source_ref='Signed amendment', source_quote='Due Nov 6 at 11 AM Eastern', status='requires_review', action='Verify submission')], bid_blockers=[], missing_information=[], amendment_resolution=[], solicitation_number='TEST-017', deadline_assessment='Questions window elapsed')

    def test_source_and_deadline_survive_render(self):
        source='Signed amendment: Due Nov 6 at 11 AM Eastern'
        r=c.validate_extraction(self.record(), source)
        self.assertEqual(r['_source_text'], source)
        report=c.compliance_report(r, {})
        for text in ('TEST-017', 'Due Nov 6 at 11 AM Eastern', 'Questions window elapsed'):
            self.assertIn(text, report)

    def test_unverifiable_quote_blocks(self):
        r=c.validate_extraction(self.record(), 'Different text')
        self.assertTrue(c.blocked(r))
        self.assertIn('NO SUBMIT', c.compliance_report(r, {}))

    def test_missing_evidence_blocks(self):
        r=c.validate_extraction(self.record(), 'Due Nov 6 at 11 AM Eastern')
        r['missing_information']=['No eligible prime supplied']
        self.assertTrue(c.blocked(r))

    def test_missing_matrix_rejected(self):
        with self.assertRaises(ValueError):
            c.validate_extraction({}, 'source')
        self.assertTrue(c.blocked({}))


class DraftGateTests(unittest.TestCase):
    """A NO SUBMIT packet still gets a conditional draft; an unanalyzed one does not."""

    def run_draft(self, requirements):
        import asyncio, os, sys, types
        os.environ.setdefault('ANTHROPIC_API_KEY', 'test')
        folder = Path(__file__).resolve().parents[1] / 'proposal-agent'
        sys.path.insert(0, str(folder))
        # Loaded under its own name: the BD agent also has a module called "agent".
        agent_spec = importlib.util.spec_from_file_location('proposal_agent', folder / 'agent.py')
        agent = importlib.util.module_from_spec(agent_spec)
        agent_spec.loader.exec_module(agent)
        prompts = []

        class Stream:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass
            @property
            def text_stream(self):
                async def gen(): yield 'DRAFT BODY'
                return gen()
            async def get_final_message(self): return types.SimpleNamespace(stop_reason='end_turn')

        def stream(**kw):
            prompts.append(kw['messages'][0]['content'])
            return Stream()

        agent._async_client = types.SimpleNamespace(messages=types.SimpleNamespace(stream=stream))

        async def collect():
            return [e async for e in agent.stream_draft(requirements, {})]
        return asyncio.run(collect()), prompts

    def record(self):
        r = ComplianceTests().record()
        return c.validate_extraction(r, 'Due Nov 6 at 11 AM Eastern')

    def test_no_submit_still_drafts(self):
        r = self.record()
        r['missing_information'] = ['Release date not stated']
        events, prompts = self.run_draft(r)
        text = ''.join(e.get('text', '') for e in events)
        self.assertIn({'gate': 'no_submit'}, events)
        self.assertIn('Conditional Draft — NO SUBMIT', text)
        self.assertIn('DRAFT BODY', text)
        self.assertIn('[BLOCKER: ...]', prompts[0])
        self.assertEqual(events[-1], {'stop_reason': 'end_turn'})

    def test_clear_packet_drafts_without_gate(self):
        events, prompts = self.run_draft(self.record())
        self.assertNotIn({'gate': 'no_submit'}, events)
        self.assertNotIn('NO SUBMIT. Write the draft anyway', prompts[0])

    def test_unanalyzed_packet_is_not_drafted(self):
        events, prompts = self.run_draft({'program_name': 'X'})
        self.assertEqual(events[-1], {'stop_reason': 'blocked'})
        self.assertEqual(prompts, [])
