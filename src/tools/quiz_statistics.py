"""Aggregate Classic Quiz survey reads; no individual responses or identities.

Verified 2026-10-03 against Canvas Quiz Statistics API and StudentAnalysis source:
https://developerdocs.instructure.com/services/canvas/resources/quiz_statistics
https://github.com/instructure/canvas-lms/blob/master/app/models/quizzes/quiz_statistics/student_analysis.rb
all_versions=false uses Canvas's kept completed attempts, not necessarily latest.
"""

import re
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BeforeValidator, Field

from canvas_client import AsyncCanvasClient, _origin
from tools.assistant import READ_ONLY, _assistant_tool, _plain_text
from tools.quiz_accommodations import CanvasID, not_boolean, numeric_id, pages

CHOICE_TYPES = {'multiple_choice_question', 'true_false_question', 'multiple_answers_question'}
AGREEMENT_SCALE = {'strongly disagree': 1, 'disagree': 2, 'neither agree nor disagree': 3,
                   'neutral': 3, 'agree': 4, 'strongly agree': 5}
ScaleValue = Annotated[int, Field(ge=1, le=5), BeforeValidator(not_boolean)]


def count(value):
    return value if type(value) is int and value >= 0 else None


def label(answer):
    value = answer.get('text') or answer.get('html') or ''
    return _plain_text(value) if isinstance(value, str) else ''


def scale_value(text):
    normalized = text.casefold().strip().rstrip('.')
    if re.match(r'^(?:not applicable\b|n\s*/\s*a\b)', normalized):
        return None, 'not_applicable'
    if normalized in AGREEMENT_SCALE:
        return AGREEMENT_SCALE[normalized], 'agreement_label'
    match = re.fullmatch(r'([1-5])(?:\s*[:.\-–—]\s*\D.*)?', normalized)
    if match:
        return int(match[1]), 'numeric_label'
    return None, 'unmapped'


def mappings_for(questions, answer_values):
    if answer_values is None:
        return {}
    if not isinstance(answer_values, dict):
        raise ValueError('answer_values must map question IDs to answer IDs and integers 1–5 or null')
    definitions = {str(q['id']): q for q in questions}
    result = {}
    for question_id, values in answer_values.items():
        question_id = numeric_id(question_id)
        if question_id not in definitions or not isinstance(values, dict):
            raise ValueError('answer_values contains an unknown question or invalid answer map')
        choices = {str(a['id']): a for a in definitions[question_id].get('answers', [])}
        result[question_id] = {}
        for answer_id, value in values.items():
            answer_id = numeric_id(answer_id)
            if answer_id not in choices or value is not None and (type(value) is not int or not 1 <= value <= 5):
                raise ValueError('Map existing answer IDs to integer ratings 1–5 or null to exclude them')
            if value is not None and scale_value(label(choices[answer_id]))[1] == 'not_applicable':
                raise ValueError('Not applicable answers must remain excluded from averages')
            result[question_id][answer_id] = value
    return result


def question_summary(definition, statistics, overrides, completed):
    question_id = str(definition['id'])
    kind = definition.get('question_type')
    result = {'question_id': question_id, 'question_type': kind,
              'question_text': _plain_text(definition.get('question_text')),
              'response_count': None, 'answers': [], 'not_applicable_count': None,
              'unanswered_count': None, 'rated_response_count': None,
              'weighted_sum': None, 'average_1_to_5': None, 'warnings': []}
    if kind not in CHOICE_TYPES:
        result['average_status'] = 'unsupported_question_type'
        result['warnings'] = ['Only predefined choice counts are returned; free responses are omitted.']
        return result
    raw_answers = (statistics or {}).get('answers')
    raw_answers = raw_answers if isinstance(raw_answers, list) else []
    indexed = {}
    for answer in raw_answers:
        if not isinstance(answer, dict):
            continue
        aid = str(answer.get('id'))
        if aid in indexed:
            raise ValueError('Canvas returned duplicate answer statistics')
        indexed[aid] = answer
    no_responses = statistics is None and completed == 0
    response_count = 0 if no_responses else count((statistics or {}).get('responses'))
    unanswered = 0 if no_responses else count(indexed.get('none', {}).get('responses'))
    if unanswered is None and completed is not None and response_count == completed:
        unanswered = 0
    result.update(response_count=response_count, unanswered_count=unanswered)
    numerator = denominator = na_count = excluded = unmapped = 0
    known = response_count is not None
    for answer in definition.get('answers', []):
        aid, text = str(answer['id']), label(answer)
        raw = indexed.get(aid)
        responses = 0 if no_responses else count((raw or {}).get('responses'))
        value, basis = scale_value(text)
        if aid in overrides:
            value = overrides[aid]
            if basis != 'not_applicable':
                basis = 'explicit_mapping' if value is not None else 'explicit_exclusion'
        if raw is not None and label(raw) != text:
            result['warnings'].append('Answer labels changed since the reported responses; average withheld.')
        result['answers'].append({'answer_id': aid, 'text': text, 'response_count': responses,
                                  'scale_value': value, 'scale_source': basis})
        if responses is None:
            known = False
        elif basis == 'not_applicable':
            na_count += responses
        elif basis == 'explicit_exclusion':
            excluded += responses
        elif value is None:
            unmapped += responses
        else:
            numerator += value * responses
            denominator += responses
    choice_ids = {a['answer_id'] for a in result['answers']}
    if set(indexed) - choice_ids - {'none'}:
        result['warnings'].append('Statistics contain choices absent from the current definition; average withheld.')
    if known and sum(a['response_count'] for a in result['answers']) != response_count:
        result['warnings'].append('Answer counts do not match the question response count; average withheld.')
    if completed is not None and response_count is not None and (
            response_count > completed or unanswered is not None and response_count + unanswered > completed):
        result['warnings'].append('Question counts exceed the completed submission count; average withheld.')
    if known:
        result.update(not_applicable_count=na_count, excluded_response_count=excluded,
                      unmapped_response_count=unmapped, rated_response_count=denominator, weighted_sum=numerator)
    status = ('counts_unavailable' if not known else 'inconsistent_statistics' if result['warnings'] else
              'unsupported_question_type' if kind != 'multiple_choice_question' else
              'mapping_required' if unmapped else 'no_rated_responses' if denominator == 0 else 'available')
    result['average_status'] = status
    if status == 'available':
        result['average_1_to_5'] = numerator / denominator
    return result


class QuizStatisticsTools:
    def __init__(self, mcp):
        mcp.tool(_assistant_tool(self.canvas_get_quiz_statistics), annotations=READ_ONLY,
                 tags={'advanced', 'read', 'quizzes', 'surveys', 'statistics'})

    async def canvas_get_quiz_statistics(
        self, course_id: CanvasID, quiz_id: CanvasID,
        answer_values: Annotated[dict[str, dict[str, ScaleValue | None]] | None, Field(description=(
            'Optional question-ID -> answer-ID -> integer 1–5 (or null to exclude) mapping. '
            'Use returned question/answer IDs for custom scales. Never use answer order or Canvas correctness weights.'
        ))] = None,
    ) -> dict:
        """Read anonymous Classic Quiz survey statistics: completed submission count, per-answer response counts and 1–5 averages, without student identities or individual answers.

        Uses course_id and Classic quiz_id, not New Quiz assignment IDs. Canvas's
        kept completed attempts are counted once (all_versions=false); unfinished
        or pending-review attempts are not counted. Standard agreement labels map
        Strongly disagree=1 through Strongly agree=5; numeric labels 1–5 also work.
        Not applicable/N/A and unanswered choices are always excluded from averages.
        For custom labels, inspect the returned IDs and supply answer_values.
        Missing statistics return null/unavailable, never invented zeros. Includes
        generated_at and averaging denominators; quiz scores are not survey ratings.
        Only aggregate choice counts are returned, even for non-anonymous quizzes.
        FERPA=true is required. No student lookup, CSV export, or Canvas writes.
        """
        course_id, quiz_id = numeric_id(course_id), numeric_id(quiz_id)
        base = f'/api/v1/courses/{course_id}/quizzes/{quiz_id}'
        async with AsyncCanvasClient.from_environment() as client:
            quiz = await client.get(base)
            if not isinstance(quiz, dict) or str(quiz.get('id')) != quiz_id:
                raise ValueError('Canvas returned a mismatched Classic Quiz')
            if quiz.get('is_new_quiz') or quiz.get('quiz_type') == 'quizzes.next':
                raise ValueError('Statistics require a Classic Quiz ID; New Quizzes are not supported')
            questions = await pages(client, f'{base}/questions')
            questions = [q for q in questions if q.get('question_type') != 'text_only_question']
            mappings = mappings_for(questions, answer_values)
            payload = await client.get(f'{base}/statistics', params={'all_versions': 'false'})
        records = payload.get('quiz_statistics') if isinstance(payload, dict) else None
        result = {'course_id': course_id, 'quiz_id': quiz_id, 'title': _plain_text(quiz.get('title')),
                  'quiz_type': quiz.get('quiz_type'), 'anonymous_survey': bool(quiz.get('anonymous_submissions')),
                  'status': 'unavailable', 'completed_submission_count': None, 'generated_at': None,
                  'attempt_scope': 'Canvas kept completed attempts; all_versions=false',
                  'count_source': 'submission_statistics.unique_count',
                  'average_method': 'Sum(rating × answer count) / rated response count. Excludes N/A, unanswered and explicitly excluded choices. Overall average is response-weighted across questions, not a quiz score or an average of student scores.',
                  'questions': [], 'overall_average_1_to_5': None, 'warnings': []}
        if not isinstance(records, list) or not records:
            result['warnings'] = ['Canvas statistics are unavailable; this does not establish zero completed submissions.']
            return result
        if len(records) != 1 or not isinstance(records[0], dict):
            raise ValueError('Canvas returned ambiguous quiz statistics; no versions were combined')
        record = records[0]
        quiz_ref = record.get('quiz_id')
        quiz_link = (record.get('links') or {}).get('quiz')
        # Canvas JSON-API responses identify the quiz through links.quiz.
        # Validate the course and origin too; never follow this returned URL.
        valid_link = (isinstance(quiz_link, str) and _origin(quiz_link) == _origin(client.base_url)
                      and urlsplit(quiz_link).path.rstrip('/') == base)
        if (quiz_ref is not None and str(quiz_ref) != quiz_id
                or quiz_link is not None and not valid_link
                or quiz_ref is None and not valid_link):
            raise ValueError('Canvas returned statistics for a different quiz')
        if record.get('includes_all_versions') is not False:
            result['warnings'] = ['Canvas did not confirm single-attempt statistics; counts and averages withheld.']
            return result
        completed = count((record.get('submission_statistics') or {}).get('unique_count'))
        stats = record.get('question_statistics') or []
        if not isinstance(stats, list) or any(not isinstance(q, dict) for q in stats):
            raise ValueError('Canvas returned invalid question statistics')
        indexed = {str(q.get('id')): q for q in stats}
        if len(indexed) != len(stats):
            raise ValueError('Canvas returned duplicate question statistics')
        result.update(completed_submission_count=completed, generated_at=record.get('generated_at'),
                      questions=[question_summary(q, indexed.get(str(q['id'])), mappings.get(str(q['id']), {}), completed)
                                 for q in questions])
        if completed is None:
            result['warnings'].append('Canvas did not provide a valid completed submission count.')
        if set(indexed) - {str(q['id']) for q in questions}:
            result['warnings'].append('Statistics include questions absent from the current quiz definition.')
        valid = all(q['average_status'] in {'available', 'no_rated_responses'} for q in result['questions'])
        result['status'] = 'available' if completed is not None and valid and not result['warnings'] else 'partial'
        if result['status'] == 'available' and result['questions']:
            total = sum(q['rated_response_count'] for q in result['questions'])
            weighted = sum(q['weighted_sum'] for q in result['questions'])
            result.update(overall_rated_response_count=total, overall_weighted_sum=weighted,
                          overall_average_1_to_5=weighted / total if total else None)
        return result
