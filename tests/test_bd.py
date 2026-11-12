import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bd-research-agent'))
import httpx
import agent
import main
import sam_client
from source_report import source_items, build_source_report

class BDTests(unittest.TestCase):
    def test_source_run_never_calls_claude(self):
        with patch.object(main.usa, 'fetch_recent_awards', return_value={'results':[{'Award ID':'A1','Award Amount':1000}]}), patch.object(agent, 'score_opportunities', side_effect=AssertionError('Paid call')):
            result=asyncio.run(main.research(main.ResearchRequest()))
        self.assertEqual(result['analysis_mode'], 'source')
        self.assertIsNone(result['scored'][0]['pursuit_score'])
        self.assertEqual(result['scored'][0]['date_type'], 'Ends')

    def test_api_failure_is_not_a_scored_record(self):
        with patch.object(main.usa, 'fetch_recent_awards', return_value={'results':[{'Award ID':'A1'}]}), patch.object(agent, 'score_opportunities', side_effect=RuntimeError('billing unavailable')):
            result=asyncio.run(main.research(main.ResearchRequest(analysis_mode='claude')))
        self.assertEqual(result['scored'], [])
        self.assertIn('billing unavailable', result['errors'][0])

    def test_salvage_preserves_complete_records_with_nested_truncation(self):
        self.assertEqual(agent._salvage_json_array('[{"id":"a","pursuit_score":5}, {"nested": {"x":1}, "broken":'), [{'id':'a','pursuit_score':5}])

    def test_per_code_sam_deduplication(self):
        calls=[]
        def respond(request):
            calls.append(request.url.params['ncode'])
            return httpx.Response(200, json={'opportunitiesData':[{'noticeId':'same'},{'noticeId':calls[-1]}]})
        factory=httpx.Client
        with patch.object(sam_client.httpx,'Client',side_effect=lambda **kw:factory(transport=httpx.MockTransport(respond),**kw)):
            result=sam_client.fetch_opportunities(['541330','541512','334511'], 'test', limit=10)
        self.assertEqual(calls,['541330','541512','334511'])
        self.assertEqual(len(result['opportunitiesData']),4)

    def test_nonoverlapping_focus_does_not_query_other_codes(self):
        with patch.object(main.usa,'fetch_recent_awards',return_value={'results':[]}), patch.object(main.sam,'fetch_opportunities',return_value={'opportunitiesData':[]}) as fetch:
            asyncio.run(main.research(main.ResearchRequest(focus_areas=['aircraft'], sam_api_key='test')))
        self.assertEqual(fetch.call_args.kwargs['naics_codes'],[])

    def test_source_brief_never_calls_claude(self):
        class Request:
            async def json(self):
                return {'analysis_mode':'source','scored':source_items([{'type':'award','award_id':'A1'}])}
        async def run():
            response=await main.brief(Request())
            return ''.join([chunk async for chunk in response.body_iterator])
        with patch.object(main.usa,'fetch_agency_spending_by_naics',return_value={'results':[{'name':'Army','amount':1234}]}), patch.object(agent,'stream_brief',side_effect=AssertionError('Paid call')):
            text=asyncio.run(run())
        self.assertIn('No AI Analysis',text)
        self.assertIn('$1,234',text)
        self.assertIn('[DONE]',text)

if __name__=='__main__': unittest.main()
