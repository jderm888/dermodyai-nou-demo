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
