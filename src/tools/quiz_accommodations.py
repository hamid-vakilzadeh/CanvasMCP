"""Student quiz time accommodations, verified against Canvas docs 2026-09-16."""

from decimal import Decimal, ROUND_CEILING
import math
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, StrictInt, StrictStr

from action_plans import Mutation, Precondition, fingerprint, plan_store
from canvas_client import AsyncCanvasClient, decode_cursor
from tools.assistant import PLAN_ONLY, _assistant_tool, _compact


def numeric_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isascii() or not str(value).isdigit() or int(value) <= 0:
        raise ValueError('Use a positive Canvas numeric ID, resolved from the course roster or quiz inventory')
    return str(int(value))


def not_boolean(value):
    # FastMCP's default lax mode overrides Pydantic strict field metadata.
    # Check the raw value before integer/float coercion; other tools keep their
    # existing flexible conversion behavior.
    if isinstance(value, bool):
        raise ValueError('Provide a number, not a boolean')
    return value


CanvasID = Annotated[StrictStr | StrictInt, BeforeValidator(numeric_id)]
ExtraMinutes = Annotated[int, Field(ge=0, le=10080), BeforeValidator(not_boolean)]
TimeMultiplier = Annotated[float, Field(ge=1, allow_inf_nan=False), BeforeValidator(not_boolean)]


def unique_ids(values, label):
    if not isinstance(values, list) or not values:
        raise ValueError(f'{label} must be a non-empty list')
    ids = [numeric_id(v) for v in values]
    if len(ids) != len(set(ids)):
        raise ValueError(f'{label} must not contain duplicate IDs')
    return ids


async def pages(client, endpoint, *, params=None, wrapped=None, guards=None):
    """Follow every page; failed/incomplete inventories never become write plans."""
    items, cursor, seen = [], None, set()
    while True:
        page = await client.page(endpoint, params=params, cursor=cursor, limit=100)
        raw = page['items']
        if wrapped:
            if len(raw) != 1 or not isinstance(raw[0].get(wrapped), list):
                raise ValueError('Canvas returned an unexpected quiz-submission response')
            payload, rows = raw[0], raw[0][wrapped]
        else:
            payload, rows = raw, raw
        if guards is not None:
            guards.append(Precondition(
                endpoint=decode_cursor(cursor) if cursor else endpoint,
                params=None if cursor else {**(params or {}), 'per_page': 100},
                fingerprint=fingerprint(payload),
            ))
        items.extend(rows)
        cursor = page.get('next_cursor')
        if not cursor:
            return items
        if cursor in seen:
            raise ValueError('Canvas repeated a pagination cursor; no accommodation plan was created')
        seen.add(cursor)


def base_minutes(quiz, engine):
    if engine == 'classic':
        if quiz.get('is_new_quiz') or quiz.get('quiz_type') == 'quizzes.next':
            raise ValueError('This is a New Quiz; use engine=new and its assignment ID')
        value = quiz.get('time_limit')
    else:
        settings = quiz.get('quiz_settings') or {}
        value = settings.get('session_time_limit_in_seconds') if settings.get('has_time_limit') else None
        if value is not None:
            value = float(value) / 60
    if value is None or value == 0:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Canvas returned an invalid quiz time limit')
    return value


def accommodation_result(mutation, value):
    """HTTP 200 can contain per-student failures or omit a requested student."""
    is_classic = isinstance(mutation.json_data, dict)
    requested = mutation.json_data['quiz_extensions'] if is_classic else mutation.json_data
    value = value if isinstance(value, dict) else {}
    successful = value.get('quiz_extensions' if is_classic else 'successful', [])
    failed = [] if is_classic else value.get('failed', [])
    successful = successful if isinstance(successful, list) else []
    failed = failed if isinstance(failed, list) else []
    results = []
    for change in requested:
        user_id = str(change['user_id'])
        errors = [r for r in failed if isinstance(r, dict) and str(r.get('user_id')) == user_id]
        matches = [r for r in successful if isinstance(r, dict) and str(r.get('user_id')) == user_id
                   and (not is_classic or str(r.get('quiz_id')) == mutation.endpoint.split('/')[-2])]
        status = 'failed' if errors else 'applied' if len(matches) == 1 else 'uncertain'
        if status == 'applied' and is_classic and matches[0].get('extra_time') != change['extra_time']:
            status = 'uncertain'
        results.append({'student_id': user_id, 'status': status,
                        **({'error': 'Canvas reported an accommodation failure', 'details': errors} if errors else {})})
    statuses = {r['status'] for r in results}
    status = next(iter(statuses)) if len(statuses) == 1 else 'partial'
    return {'status': status, 'student_results': results, 'result': value}


class QuizAccommodationTools:
    def __init__(self, mcp):
        mcp.tool(_assistant_tool(self.canvas_plan_quiz_accommodations), annotations=PLAN_ONLY,
                 tags={'advanced', 'plan', 'quizzes', 'accommodations'})

    async def canvas_plan_quiz_accommodations(
        self,
        course_id: CanvasID,
        student_ids: Annotated[list[CanvasID], Field(min_length=1, max_length=100)],
        engine: Literal['classic', 'new'] = 'classic',
        scope: Literal['selected', 'all_timed', 'course'] = 'selected',
        quiz_ids: Annotated[list[CanvasID] | None, Field(description='Classic quiz IDs or New Quiz assignment IDs; required for selected scope')] = None,
        extra_time_minutes: ExtraMinutes | None = None,
        time_multiplier: Annotated[TimeMultiplier | None, Field(description='For example 1.5; converted to extra whole minutes per timed quiz, rounded up')] = None,
        apply_to_in_progress_quiz_sessions: bool = False,
    ) -> dict:
        """Plan student-specific quiz extra time, time-and-a-half/1.5x accommodations or Moderate Quiz changes.

        Provide exactly one of extra_time_minutes or time_multiplier. all_timed
        inventories every current timed quiz, including unpublished quizzes; it
        does not cover quizzes created later. course is New Quizzes fixed minutes
        only. Classic extra_time sets the extra-minute allowance for all attempts;
        it does not extend an already running attempt's end_at or change lock dates.
        Inspect the preview, then use canvas_apply_change. No Canvas writes occur here.
        """
        course_id = numeric_id(course_id)
        students = unique_ids(student_ids, 'student_ids')
        if len(students) > 100:
            raise ValueError('Use at most 100 students per plan')
        if engine not in {'classic', 'new'} or scope not in {'selected', 'all_timed', 'course'}:
            raise ValueError('Choose a supported quiz engine and scope')
        if (extra_time_minutes is None) == (time_multiplier is None):
            raise ValueError('Provide exactly one of extra_time_minutes or time_multiplier')
        if extra_time_minutes is not None and (type(extra_time_minutes) is not int or not 0 <= extra_time_minutes <= 10080):
            raise ValueError('extra_time_minutes must be an integer from 0 to 10080')
        if time_multiplier is not None and (isinstance(time_multiplier, bool) or not isinstance(time_multiplier, (int, float)) or not math.isfinite(time_multiplier) or time_multiplier < 1):
            raise ValueError('time_multiplier must be a finite number at least 1')
        if type(apply_to_in_progress_quiz_sessions) is not bool:
            raise ValueError('apply_to_in_progress_quiz_sessions must be a boolean')
        if apply_to_in_progress_quiz_sessions and (engine != 'new' or scope != 'course'):
            raise ValueError('apply_to_in_progress_quiz_sessions is supported only for New Quizzes course scope')
        if scope == 'course' and (engine != 'new' or time_multiplier is not None):
            raise ValueError('Course scope supports New Quizzes fixed extra minutes only; use all_timed for per-quiz multipliers')
        if scope != 'selected' and quiz_ids is not None:
            raise ValueError('quiz_ids is only allowed for selected scope')
        ids = unique_ids(quiz_ids, 'quiz_ids') if scope == 'selected' else []
        root = '/api/v1' if engine == 'classic' else '/api/quiz/v1'
        collection = f'{root}/courses/{course_id}/quizzes'
        guards, preview_quizzes, mutations, roster, skipped = [], [], [], [], []
        warnings = [
            'Extra time does not change availability/Until dates; they can still cut off an extended attempt. Review student/group/section overrides in Canvas.',
            'Preview dates are quiz defaults, not resolved student-specific availability dates.',
        ]
        if scope != 'course':
            warnings.append('Only the listed existing quizzes are targeted. Re-run for quizzes created later; no ongoing accommodation rule is installed.')
        if engine == 'new':
            warnings.append('The public New Quizzes API does not expose existing accommodation values here. Inspect Canvas before replacing a setting or retrying an uncertain write.')
        else:
            warnings.append('Classic extra minutes replace the existing extra_time allowance, rather than adding to it. Running attempts require separate end-time moderation; end_at is unchanged by this plan.')
        async with AsyncCanvasClient.from_environment() as client:
            for student_id in students:
                enrollments = await pages(client, f'/api/v1/courses/{course_id}/enrollments',
                                         params={'user_id': student_id, 'type[]': ['StudentEnrollment']})
                matches = [e for e in enrollments if str(e.get('user_id')) == student_id
                           and e.get('type') == 'StudentEnrollment' and e.get('enrollment_state') not in {'deleted', 'rejected'}]
                if not matches:
                    raise ValueError(f'Student {student_id} is not enrolled as a student in this course')
                roster.append({'student_id': student_id, 'name': (matches[0].get('user') or {}).get('name')})
            if scope == 'course':
                mutations.append(Mutation('POST', f'{root}/courses/{course_id}/accommodations',
                    json_data=[{'user_id': int(s), 'extra_time': extra_time_minutes,
                                'apply_to_in_progress_quiz_sessions': apply_to_in_progress_quiz_sessions} for s in students],
                    label='new-quiz-course-accommodations'))
            else:
                if scope == 'all_timed':
                    inventory = await pages(client, collection, guards=guards)
                    for quiz in inventory:
                        if engine == 'classic' and (quiz.get('is_new_quiz') or quiz.get('quiz_type') == 'quizzes.next'):
                            skipped.append({'quiz_id': str(quiz['id']), 'reason': 'New Quiz requires engine=new'})
                        elif base_minutes(quiz, engine) is None:
                            skipped.append({'quiz_id': str(quiz['id']), 'reason': 'No time limit'})
                        else:
                            ids.append(numeric_id(quiz['id']))
                    if not ids:
                        raise ValueError('No timed quizzes were returned; no plan was created')
                    ids = list(dict.fromkeys(ids))
                for quiz_id in ids:
                    endpoint = f'{collection}/{quiz_id}'
                    quiz = await client.get(endpoint)
                    if str(quiz.get('id')) != quiz_id:
                        raise ValueError('Canvas returned a mismatched quiz ID')
                    minutes = base_minutes(quiz, engine)
                    if minutes is None:
                        raise ValueError(f'Quiz {quiz_id} has no time limit; extra minutes would not be meaningful')
                    guards.append(Precondition(endpoint, fingerprint(quiz)))
                    extra = extra_time_minutes
                    if time_multiplier is not None:
                        extra = int((Decimal(str(minutes)) * (Decimal(str(time_multiplier)) - 1)).to_integral_value(rounding=ROUND_CEILING))
                    if extra > 10080:
                        raise ValueError(f'Quiz {quiz_id} would exceed the Canvas limit of 10080 extra minutes')
                    before = {}
                    if engine == 'classic':
                        submissions = await pages(client, f'{endpoint}/submissions', wrapped='quiz_submissions', guards=guards)
                        before = {str(s['user_id']): s for s in submissions if str(s.get('user_id')) in students}
                    student_preview = []
                    for student_id in students:
                        current = before.get(student_id, {})
                        previous = current.get('extra_time')
                        if isinstance(previous, (float, int)) and previous > extra:
                            warnings.append(f'Quiz {quiz_id}, student {student_id}: this reduces the existing extra-minute allowance.')
                        student_preview.append({'student_id': student_id, 'previous_extra_time_minutes': previous,
                            'previous_setting_available': engine == 'classic' and 'extra_time' in current,
                            'extra_time_minutes': extra, 'total_time_minutes': minutes + extra,
                            'attempt_state': current.get('workflow_state'), 'current_attempt_end_at': current.get('end_at')})
                    preview_quizzes.append({**_compact([quiz], ('id','title','published','unlock_at','due_at','lock_at','all_dates'))[0],
                        'identifier_type': 'quiz_id' if engine == 'classic' else 'assignment_id',
                        'base_time_minutes': minutes, 'students': student_preview})
                    changes = [{'user_id': int(s), 'extra_time': extra} for s in students]
                    mutations.append(Mutation('POST', f'{endpoint}/' + ('extensions' if engine == 'classic' else 'accommodations'),
                        json_data={'quiz_extensions': changes} if engine == 'classic' else changes,
                        label=f'{engine}-quiz:{quiz_id}'))
        return await plan_store.create(action='quiz_accommodations',
            summary=f'Set {engine} quiz extra time for {len(students)} student(s) across {len(mutations)} target(s)',
            preview={'course_id': course_id, 'engine': engine, 'scope': scope, 'students': roster,
                     'extra_time_minutes': extra_time_minutes, 'time_multiplier': time_multiplier,
                     'rounding': 'Multiplier-derived extra minutes round up to the next whole minute',
                     'apply_to_in_progress_quiz_sessions': apply_to_in_progress_quiz_sessions,
                     'quizzes': preview_quizzes, 'skipped': skipped},
            mutations=mutations, preconditions=guards, warnings=warnings)
