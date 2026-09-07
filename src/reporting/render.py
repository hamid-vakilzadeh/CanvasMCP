"""Deterministic, escaped faculty reports with complete evidence inventories."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path

from reporting.common import now, safe_url
from reporting.reviews import Reviews


REPORT_CSS = """
:root{color-scheme:light;--ink:#19333c;--muted:#586a70;--line:#dbe4e4;--accent:#006d77;--paper:#fff;--wash:#f4f8f7}
*{box-sizing:border-box}body{font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:#edf3f2;margin:0}main{max-width:1050px;margin:36px auto;background:var(--paper);padding:56px 64px;border-top:7px solid var(--accent)}header{padding-bottom:28px;border-bottom:1px solid var(--line)}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:12px;font-weight:700;color:var(--accent)}h1{font-size:36px;line-height:1.15;letter-spacing:-.035em;margin:12px 0}h2{font-size:22px;line-height:1.3;margin:32px 0 14px}h3{font-size:17px;margin:0 0 6px}p{margin:8px 0}.muted,.source{color:var(--muted);font-size:13px}.meta{display:flex;flex-wrap:wrap;gap:8px 24px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;margin:28px 0}.metric strong{display:block;font-size:28px;font-weight:650;letter-spacing:-.03em}.metric span{color:var(--muted);font-size:12px}.finding{margin:16px 0;padding:16px 20px;border-left:3px solid var(--line);background:var(--wash);break-inside:avoid}.finding.strength{border-color:var(--accent)}.finding.learning_gap{border-color:#a05a14}.tag{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}.notice{padding:14px 18px;background:#fff5e7;border-left:3px solid #a05a14}.sources a{font-size:12px;margin-right:12px}a{color:#00616a;text-underline-offset:3px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}th{background:var(--wash)}.appendix td:first-child{width:17%}.appendix td:nth-child(2){width:33%}footer{margin-top:32px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}button{font:inherit;padding:9px 16px;background:var(--accent);color:#fff;border:0;border-radius:6px;cursor:pointer}.actions{text-align:right;margin-bottom:12px}
@media(max-width:700px){main{margin:0;padding:28px 20px}h1{font-size:28px}.metrics{grid-template-columns:repeat(2,1fr)}table{font-size:12px}th,td{padding:6px}.meta{display:block}}
@page{size:A4;margin:16mm}
@media print{body{background:white;font-size:10pt}main{max-width:none;margin:0;padding:0;border-top:4px solid var(--accent)}h1{font-size:25pt}h2{font-size:15pt;break-after:avoid}h3{break-after:avoid}.actions{display:none}.metrics{gap:12px}a{color:inherit}.appendix{break-before:page}thead{display:table-header-group}tr{break-inside:avoid}.finding{padding:10px 14px}footer{font-size:9pt}}
"""


def _text(value) -> str:
    return escape(str(value if value is not None else 'Unavailable'), quote=True)


def validate_findings(findings: list[dict], evidence: dict) -> None:
    for finding in findings:
        if finding.get('category') not in {'strength', 'learning_gap', 'submission_pattern', 'participation', 'support'}:
            raise ValueError('Unsupported finding category')
        if finding.get('interpretation') not in {'observation', 'interpretation', 'recommendation'}:
            raise ValueError('Findings must distinguish observations, interpretations, and recommendations')
        refs = finding.get('evidence_ids') or []
        if not finding.get('text') or not refs or any(ref not in evidence or evidence[ref].get('status') != 'reviewed' for ref in refs):
            raise ValueError('Every finding must cite reviewed evidence from this report')


def render_review(store, job_id: str, *, overview: str, findings: list[dict] | None = None,
                  follow_up_questions: list[str] | None = None, allow_incomplete: bool = False) -> dict:
    reviews = Reviews(store)
    job = store.get('report', job_id)
    state = reviews.status(job_id)
    coverage = state['coverage']
    if job.get('evidence_expired'):
        raise ValueError('Evidence expired; generate a fresh review before rendering')
    incomplete = not job.get('collection_complete') or coverage['pending'] > 0
    if incomplete and not allow_incomplete:
        raise ValueError('Review all pending evidence before claiming the report is complete')
    evidence = {e['id']: e for e in reviews.evidence(job_id)}
    analyses = [a for a in store.all('analysis') if a['job_id'] == job_id]
    findings = findings if findings is not None else [f for a in analyses for f in a['findings']]
    validate_findings(findings, evidence)
    if not overview.strip():
        raise ValueError('Provide a concise faculty overview')
    snapshot = job.get('snapshot') or {}
    student = snapshot.get('student', {}).get('name', f"Student {job['student_id']}")
    course = snapshot.get('course', {}).get('name', f"Course {job['course_id']}")
    status = 'incomplete' if incomplete else 'completed_with_gaps' if coverage['gaps'] else 'completed'
    status_label = {'incomplete': 'Incomplete review', 'completed_with_gaps': 'Review complete with documented evidence gaps',
                    'completed': 'All collected accessible evidence reviewed'}[status]
    generated = now()
    grade = snapshot.get('grades', {}).get('current_score')
    counts = snapshot.get('counts') or {}
    metrics = [('Canvas current grade', f'{grade:g}%' if isinstance(grade, (int, float)) else 'Unavailable'),
               ('Missing assignments' + ('' if snapshot.get('counts_complete') else ' · partial count'), counts.get('missing')),
               ('Evidence chunks reviewed', f"{coverage['reviewed']} / {coverage['evidence_chunks']}"),
               ('Documented evidence gaps', coverage['gaps'])]
    parts = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_text(student)} — Learning review</title><style>{REPORT_CSS}</style></head><body><main>',
             '<div class="actions"><button onclick="window.print()">Print or save as PDF</button></div>',
             f'<header><div class="eyebrow">CanvasMCP · Faculty learning review</div><h1>{_text(student)}</h1><p>{_text(course)}</p>',
             f'<div class="meta muted"><span>Generated {_text(generated)}</span><span>Course {_text(job["course_id"])}</span><span>Faculty use · Private local report</span></div></header>',
             f'<p class="notice">{_text(status_label)}. {_text(job["scope"])}. Source data retrieved {_text(snapshot.get("retrieved_at"))}.</p>',
             '<div class="metrics">' + ''.join(f'<div class="metric"><strong>{_text(value)}</strong><span>{_text(label)}</span></div>' for label, value in metrics) + '</div>',
             f'<section><h2>Performance overview</h2><p>{_text(overview)}</p></section>']
    categories = [('strength', 'Demonstrated strengths'), ('learning_gap', 'Learning gaps supported by the work'),
                  ('submission_pattern', 'Submission patterns'), ('participation', 'Recorded participation'),
                  ('support', 'Prioritized support recommendations')]
    for category, heading in categories:
        rows = [f for f in findings if f['category'] == category]
        parts.append(f'<section><h2>{heading}</h2>')
        if not rows:
            parts.append('<p class="muted">No supported finding was recorded for this section.</p>')
        for finding in rows:
            links = ' '.join(f'<a href="#e-{key}">Evidence {key[:8]}</a>' for key in finding['evidence_ids'])
            parts.append(f'<article class="finding {category}"><div class="tag">{_text(finding["interpretation"])}</div><p>{_text(finding["text"])}</p><div class="sources">{links}</div></article>')
        parts.append('</section>')
    parts.append('<section><h2>Follow-up questions</h2><ul>')
    for question in follow_up_questions or ['Which part of the work would the student like to revisit with the instructor?']:
        parts.append(f'<li>{_text(question)}</li>')
    parts.append('</ul></section><section class="appendix"><h2>Evidence and coverage appendix</h2><p class="muted">The inventory includes every collected evidence chunk. Text below is a labeled excerpt; the analysis used the complete retrieved chunks. Source locations preserve assignment and revision associations.</p><table><thead><tr><th scope="col">Evidence</th><th scope="col">Source and location</th><th scope="col">Excerpt / coverage gap</th></tr></thead><tbody>')
    for key, item in evidence.items():
        sources = []
        for source in item['sources']:
            labels = [str(source[k]) for k in ('title', 'filename', 'location') if source.get(k) is not None]
            labels.extend(f'{label} {source[key]}' for key, label in (('attempt','attempt'),('entry_id','entry'),('submitted_at','submitted')) if source.get(key) is not None)
            label = ' · '.join(labels)
            url = safe_url(source.get('url'))
            sources.append(f'<a href="{_text(url)}" rel="noreferrer">{_text(label)}</a>' if url else _text(label))
        excerpt = item['text'][:400] + ('… [excerpt]' if len(item['text']) > 400 else '')
        parts.append(f'<tr id="e-{key}"><td><strong>{key[:8]}</strong><br>{_text(item["kind"])}<br>{_text(item["status"])}</td><td>{"<br>".join(sources)}</td><td>{_text(excerpt)}</td></tr>')
    parts.append('</tbody></table></section>')
    parts.append(f'<footer>AI-assisted interpretation for faculty review. Canvas activity is not a measure of attendance, effort, understanding, or academic integrity. No grades or messages were changed. Analysis batches: {len(analyses)}. Model usage: {_text(job.get("model_usage") or "not supplied by the AI client")}.</footer></main></body></html>')
    document = ''.join(parts)
    path = store.directory / f'report-{job_id}.html'
    path.write_text(document, encoding='utf-8')
    path.chmod(0o600)
    store.update('report', job_id, {'status': status, 'rendered_at': generated, 'report_path': str(path),
         'report_summary': overview, 'findings': findings, 'coverage_at_render': coverage,
         'metrics': {'output_characters': len(document), 'analysis_batches': len(analyses), 'evidence_characters': coverage['characters']}})
    return {'job_id': job_id, 'status': status, 'report_path': str(path), 'coverage': coverage,
            'metrics': {'output_characters': len(document), 'analysis_batches': len(analyses)}, 'model_usage': job.get('model_usage')}
