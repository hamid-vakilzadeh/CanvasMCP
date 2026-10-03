"""Attempt-bound Classic Quiz answers exposed by assignment submission history.

Canvas Submissions API and its quiz_submission_attempt_json serializer verified
2026-09-19. Never substitute the current attempt's answers for an older attempt.
"""


def attempt_answers(submission, attempt):
    for version in [submission, *(submission.get('submission_history') or [])]:
        if not isinstance(version, dict) or str(version.get('attempt')) != str(attempt):
            continue
        for key in ('user_id', 'assignment_id'):
            if key in version and str(version[key]) != str(submission.get(key)):
                raise ValueError('Canvas returned mismatched quiz submission history')
        data = version.get('submission_data')
        if isinstance(data, list):
            return {str(item['question_id']): item for item in data
                    if isinstance(item, dict) and item.get('question_id') is not None}
    return {}


def answer_files(record, *, canvas_url=None, course_id=None, user_id=None):
    """Read attachment fields and scoped Canvas file links in submitted answer HTML.

    Question prompts, feedback and arbitrary numbers in prose do not establish
    membership. Links establish IDs and optional file-scoped verifiers; downloads
    still use authorized Files API metadata, never the authored URL.
    """
    ids = record.get('attachment_ids')
    values = list(ids) if isinstance(ids, list) else []
    values.extend(a.get('id') for a in record.get('attachments') or [] if isinstance(a, dict))
    ids = dict.fromkeys(str(v) for v in values
                        if not isinstance(v, bool) and str(v).isascii() and str(v).isdigit() and int(v) > 0)
    verifiers = {}
    if canvas_url and course_id is not None:
        from canvas_file_links import CanvasFileLinks
        links = CanvasFileLinks(canvas_url, course_id, user_id)
        for key in ('text', 'answer'):
            if isinstance(record.get(key), str):
                links.feed(record[key])
        ids.update(links.ids)
        verifiers = links.verifiers
    return [{'id': fid, **({'verifier': verifiers[fid]} if fid in verifiers else {})} for fid in ids]


def answer_file_ids(record, **context):
    """Public review metadata contains identifiers, never file access verifiers."""
    return [item['id'] for item in answer_files(record, **context)]


async def assignment_quiz_answers(client, course_id, quiz_id, quiz_submission, attempt=None):
    if str(quiz_submission.get('quiz_id')) != str(quiz_id):
        raise ValueError('The quiz submission does not belong to the requested quiz')
    user_id, submission_id = quiz_submission.get('user_id'), quiz_submission.get('submission_id')
    if user_id is None or submission_id is None:
        raise ValueError('Canvas did not expose the assignment submission association for this quiz attempt')
    quiz = await client.get(f'/api/v1/courses/{course_id}/quizzes/{quiz_id}')
    if str(quiz.get('id')) != str(quiz_id) or not quiz.get('assignment_id'):
        raise ValueError('Canvas did not return the requested Classic Quiz assignment')
    assignment_id = str(quiz['assignment_id'])
    endpoint = f'/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}'
    params = {'include[]': ['submission_history']}
    submission = await client.get(endpoint, params)
    if (str(submission.get('id')) != str(submission_id)
            or str(submission.get('user_id')) != str(user_id)
            or str(submission.get('assignment_id')) != assignment_id):
        raise ValueError('Canvas returned a mismatched assignment submission for this quiz')
    attempt = quiz_submission.get('attempt') if attempt is None else attempt
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ValueError('Use a positive Classic Quiz attempt number')
    return {'assignment_id': assignment_id, 'attempt': attempt,
            'answers': attempt_answers(submission, attempt),
            'endpoint': endpoint, 'params': params, 'submission': submission}
