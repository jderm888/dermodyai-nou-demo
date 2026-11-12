"""Preserve source-backed compliance findings and gate unsupported drafting."""
from datetime import datetime
from zoneinfo import ZoneInfo


def validate_extraction(result, source):
    if not isinstance(result, dict):
        raise ValueError('Analysis must be an object.')
    rows = result.get('compliance_matrix')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Analysis omitted the compliance matrix. Retry analysis.')
    for key in ('bid_blockers', 'missing_information', 'amendment_resolution'):
        if not isinstance(result.get(key), list):
            raise ValueError(f'Analysis omitted {key}.')
    normalized_source = ' '.join(source.split())
    for row in rows:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip() for k in ('id', 'category', 'requirement', 'source_ref', 'source_quote', 'status', 'action')):
            raise ValueError('Incomplete compliance row. Retry analysis.')
        if ' '.join(row['source_quote'].split()) not in normalized_source:
            row['status'] = 'blocked'
            row['action'] += ' Source quote could not be verified; review original packet.'
            result['bid_blockers'].append(f"{row['id']}: unverified source quotation")
    result['_source_text'] = source
    result['analyzed_at'] = datetime.now(ZoneInfo('America/Chicago')).isoformat()
    return result


def blocked(requirements):
    rows = requirements.get('compliance_matrix')
    return (not rows or not requirements.get('_source_text')
            or bool(requirements.get('bid_blockers'))
            or bool(requirements.get('missing_information'))
            or any(row.get('status') not in ('requires_review', 'superseded') for row in rows))


def compliance_report(requirements, matched):
    gate = 'NO SUBMIT — unresolved compliance or evidence gaps' if blocked(requirements) else 'INTERNAL REVIEW ONLY — compliance not certified'
    lines = ['# RFP Compliance Report', '', f"Program: {requirements.get('program_name') or 'Not supplied'}", f"Solicitation: {requirements.get('solicitation_number') or 'Not supplied'}", f"Analyzed: {requirements.get('analyzed_at') or 'Unknown'}", '', f'## Decision\n{gate}', '', 'This report is an analysis of the supplied packet. Capability profiles and matches are illustrative, not proof of qualifications.', '', '## Deadline Assessment', requirements.get('deadline_assessment') or 'Not assessed — manual review required.']
    for key, title in [('bid_blockers','Bid Blockers'), ('missing_information','Missing Information'), ('amendment_resolution','Amendment Resolution')]:
        lines += ['', '## ' + title]
        lines += ['- ' + str(item) for item in requirements.get(key, [])] or ['- None identified by the analysis; verify against the source.']
    lines += ['', '## Compliance Matrix']
    for row in requirements.get('compliance_matrix', []):
        lines += ['', f"### {row['id']} — {row['category']}", row['requirement'], f"Status: {row['status']}", f"Source: {row['source_ref']}", f"Source quotation: {row['source_quote']}", f"Action: {row['action']}"]
    lines += ['', '## Capability Gaps (unverified matching analysis)']
    lines += ['- ' + str(item) for item in matched.get('coverage_gaps', [])]
    return '\n'.join(lines) + '\n'
