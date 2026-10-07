"""Classic Question Bank reads, QTI imports, and bank-backed random draws."""

from io import BytesIO
import hashlib
from typing import Annotated, Literal
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import httpx2
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, model_validator

from action_plans import Mutation, Precondition, fingerprint, plan_store
from canvas_client import AsyncCanvasClient, CanvasAPIError, decode_cursor
from tools.assistant import PLAN_ONLY, READ_ONLY, _assistant_tool
from tools.quiz_accommodations import CanvasID, numeric_id, not_boolean, pages


Nonempty = Annotated[str, Field(min_length=1, max_length=100000)]
Points = Annotated[float, Field(ge=0, allow_inf_nan=False), BeforeValidator(not_boolean)]
Count = Annotated[int, Field(ge=1, le=1000), BeforeValidator(not_boolean)]
QTI_NS = 'http://www.imsglobal.org/xsd/ims_qtiasiv1p2'


class BankAnswer(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: Nonempty
    correct: StrictBool


class BankQuestion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question_name: Annotated[str, Field(min_length=1, max_length=255)]
    question_text: Nonempty
    question_type: Literal['multiple_choice_question', 'true_false_question',
                           'essay_question', 'file_upload_question']
    points_possible: Points = 1
    answers: Annotated[list[BankAnswer], Field(max_length=100)] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid_answers(self):
        for text in (self.question_name, self.question_text, *(a.text for a in self.answers)):
            if not valid_xml_text(text):
                raise ValueError('Question names, text, and answers must contain valid, non-empty XML text')
        if len(self.question_text.encode('utf-8')) > 16000:
            raise ValueError('Question HTML must fit within 16000 UTF-8 bytes to avoid Canvas import truncation')
        if self.question_type in {'essay_question', 'file_upload_question'}:
            if self.answers:
                raise ValueError('Manually graded questions must not include answers')
        else:
            if len(self.answers) < 2 or sum(a.correct for a in self.answers) != 1:
                raise ValueError('Choice questions require at least two answers and exactly one correct answer')
            if len({a.text.strip().casefold() for a in self.answers}) != len(self.answers):
                raise ValueError('Answer choices must be distinct')
            if self.question_type == 'true_false_question' and {a.text.strip().casefold() for a in self.answers} != {'true', 'false'}:
                raise ValueError('True/false questions require exactly the choices True and False')
        return self


def valid_xml_text(text):
    return bool(text.strip()) and all(c in '\t\n\r' or 0x20 <= ord(c) <= 0xD7FF
                                     or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF for c in text)


def qti_archive(questions, bank_title, *, append=False):
    """Use Canvas's bank-only export structure, not loose quiz items.

    For append, the bank identifier matches CCHelper.create_key(title,
    'assessment_question_bank'), which the importer maps to settings[question_bank_id].
    Creation uses a fresh identifier so a previously deleted/renamed bank cannot
    be resurrected or overwritten. Question identifiers are always fresh.
    """
    if not valid_xml_text(bank_title):
        raise ValueError('Bank title must contain valid, non-empty XML text')
    if sum(len(json_text.encode('utf-8')) for q in questions
           for json_text in (q['question_text'], q['question_name'], *(a['text'] for a in q['answers']))) > 5 * 1024 * 1024:
        raise ValueError('Question bank import exceeds the 5 MiB text limit; split it into smaller imports')
    root = ET.Element('questestinterop', xmlns=QTI_NS)
    bank_key = ('i' + hashlib.md5(('assessment_question_bank' + bank_title).encode(), usedforsecurity=False).hexdigest()
                if append else 'bank_' + uuid4().hex)
    bank = ET.SubElement(root, 'objectbank', ident=bank_key)
    metadata = ET.SubElement(bank, 'qtimetadata')
    field = ET.SubElement(metadata, 'qtimetadatafield')
    ET.SubElement(field, 'fieldlabel').text = 'bank_title'
    ET.SubElement(field, 'fieldentry').text = bank_title
    for question in questions:
        item = ET.SubElement(bank, 'item', ident='q_' + uuid4().hex, title=question['question_name'])
        metadata = ET.SubElement(ET.SubElement(item, 'itemmetadata'), 'qtimetadata')
        for key, value in (('question_type', question['question_type']), ('points_possible', question['points_possible'])):
            field = ET.SubElement(metadata, 'qtimetadatafield')
            ET.SubElement(field, 'fieldlabel').text = key
            ET.SubElement(field, 'fieldentry').text = str(value)
        presentation = ET.SubElement(item, 'presentation')
        material = ET.SubElement(presentation, 'material')
        ET.SubElement(material, 'mattext', texttype='text/html').text = question['question_text']
        answers = question['answers']
        if answers:
            response = ET.SubElement(presentation, 'response_lid', ident='response1', rcardinality='Single')
            choices = ET.SubElement(response, 'render_choice')
            for index, answer in enumerate(answers, 1):
                label = ET.SubElement(choices, 'response_label', ident=str(index))
                ET.SubElement(ET.SubElement(label, 'material'), 'mattext', texttype='text/plain').text = answer['text']
        elif question['question_type'] == 'essay_question':
            response = ET.SubElement(presentation, 'response_str', ident='response1', rcardinality='Single')
            ET.SubElement(ET.SubElement(response, 'render_fib'), 'response_label', ident='answer1', rshuffle='No')
        processing = ET.SubElement(item, 'resprocessing')
        ET.SubElement(ET.SubElement(processing, 'outcomes'), 'decvar',
                      maxvalue='100', minvalue='0', varname='SCORE', vartype='Decimal')
        if answers:
            condition = ET.SubElement(processing, 'respcondition', {'continue': 'No'})
            correct = next(i for i, answer in enumerate(answers, 1) if answer['correct'])
            ET.SubElement(ET.SubElement(condition, 'conditionvar'), 'varequal', respident='response1').text = str(correct)
            ET.SubElement(condition, 'setvar', action='Set', varname='SCORE').text = '100'
        elif question['question_type'] == 'essay_question':
            ET.SubElement(ET.SubElement(ET.SubElement(processing, 'respcondition', {'continue': 'Yes'}), 'conditionvar'), 'other')
    xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    if len(xml) > 5 * 1024 * 1024:
        raise ValueError('Question bank import exceeds the 5 MiB XML limit; split it into smaller imports')
    buffer = BytesIO()
    manifest = ET.Element('manifest', identifier='manifest_' + uuid4().hex,
                          xmlns='http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1')
    resource = ET.SubElement(ET.SubElement(manifest, 'resources'), 'resource',
                             identifier=bank_key, type='associatedcontent/imscc_xmlv1p1/learning-application-resource',
                             href='questions.xml')
    ET.SubElement(resource, 'file', href='questions.xml')
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('questions.xml', xml)
        archive.writestr('imsmanifest.xml', ET.tostring(manifest, encoding='utf-8', xml_declaration=True))
    return buffer.getvalue()


def check_bank(bank, course_id, bank_id=None):
    if (not isinstance(bank, dict) or bank.get('context_type') != 'Course'
            or str(bank.get('context_id')) != course_id
            or (bank_id is not None and str(bank.get('id')) != bank_id)
            or bank.get('workflow_state') == 'deleted'):
        raise ValueError('The question bank does not belong to the requested course or is deleted')


async def bank_details(client, course_id, bank_id):
    endpoint = f'/api/v1/question_banks/{bank_id}'
    params = {'include_question_count': 'true'}
    bank = await client.get(endpoint, params)
    check_bank(bank, course_id, bank_id)
    return bank, Precondition(endpoint, fingerprint(bank), params=params)


async def bank_page(client, course_id, cursor=None):
    if cursor:
        url = urlsplit(decode_cursor(cursor))
        query = parse_qs(url.query)
        if url.path != '/api/v1/question_banks' or query.get('context_type') != ['Course'] or query.get('context_id') != [course_id]:
            raise ValueError('This cursor does not belong to the requested course question banks')
    result = await client.page('/api/v1/question_banks', cursor=cursor, limit=100,
        params={'context_type': 'Course', 'context_id': course_id, 'include_question_count': 'true'},
        preserve_overflow=True)
    for bank in result['items']:
        check_bank(bank, course_id)
    return result


async def check_new_bank_name(client, course_id, name):
    cursor, seen = None, set()
    while True:
        result = await bank_page(client, course_id, cursor)
        if any(str(bank.get('title', '')).strip().casefold() == name.casefold() for bank in result['items']):
            raise ValueError('A bank with this name already exists; provide its bank_id to append questions or choose a new name')
        cursor = result.get('next_cursor')
        if not cursor:
            return
        if cursor in seen:
            raise ValueError('Canvas repeated a question-bank cursor; cannot safely check for an existing bank')
        seen.add(cursor)


class QuestionBankTools:
    def __init__(self, mcp):
        for fn in (self.canvas_list_question_banks, self.canvas_get_question_bank, self.canvas_get_question_bank_import):
            mcp.tool(_assistant_tool(fn), annotations=READ_ONLY, tags={'advanced', 'quizzes', 'question-banks', 'read'})
        for fn in (self.canvas_plan_question_bank_import, self.canvas_plan_question_bank_draw):
            mcp.tool(_assistant_tool(fn), annotations=PLAN_ONLY, tags={'advanced', 'quizzes', 'question-banks', 'plan'})

    async def canvas_list_question_banks(self, course_id: CanvasID, cursor: str | None = None) -> dict:
        """Find standalone course Classic Question Banks and their question counts. Follow next_cursor if present; some Canvas versions return all banks at once. These are not New Quizzes item banks."""
        course_id = numeric_id(course_id)
        async with AsyncCanvasClient.from_environment() as client:
            return {'course_id': course_id, **await bank_page(client, course_id, cursor)}

    async def canvas_get_question_bank(
        self, course_id: CanvasID, bank_id: CanvasID, include_questions: bool = False,
        cursor: str | None = None, limit: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict:
        """Read a Classic Question Bank, optionally its question text, answer choices and correct answers. bank_id comes from canvas_list_question_banks. Follow next_cursor for all questions. These are authored questions, not student responses."""
        course_id, bank_id = numeric_id(course_id), numeric_id(bank_id)
        if cursor and not include_questions:
            raise ValueError('A cursor requires include_questions=true')
        async with AsyncCanvasClient.from_environment() as client:
            bank, _ = await bank_details(client, course_id, bank_id)
            result = {'bank': bank}
            if include_questions:
                result.update(await client.page(f'/api/v1/question_banks/{bank_id}/questions', cursor=cursor, limit=limit))
            return result

    async def canvas_plan_question_bank_import(
        self, course_id: CanvasID,
        questions: Annotated[list[BankQuestion], Field(min_length=1, max_length=200)],
        bank_name: Annotated[str, Field(min_length=1, max_length=255)] | None = None,
        bank_id: CanvasID | None = None,
    ) -> dict:
        """Create a populated standalone Classic Question Bank or append questions to an existing bank via QTI import. Supply exactly one of a new bank_name or existing bank_id. Supports multiple choice, true/false, essay and file-upload questions. answers use plain text plus one correct=true for choice questions; omit answers for manual grading. question_text is HTML. No empty banks, editing existing questions, or New Quizzes item banks. Apply returns an asynchronous migration; poll canvas_get_question_bank_import and inspect bank questions before claiming completion."""
        course_id = numeric_id(course_id)
        if (bank_name is None) == (bank_id is None):
            raise ValueError('Supply exactly one of bank_name or bank_id')
        if not 1 <= len(questions) <= 200:
            raise ValueError('Import between 1 and 200 questions')
        normalized = [BankQuestion.model_validate(q).model_dump() for q in questions]
        guards = []
        async with AsyncCanvasClient.from_environment() as client:
            if bank_id is not None:
                bank_id = numeric_id(bank_id)
                bank, guard = await bank_details(client, course_id, bank_id)
                guards.append(guard)
                title = bank['title']
            else:
                bank_name = bank_name.strip()
                if not bank_name:
                    raise ValueError('bank_name must not be blank')
                await check_new_bank_name(client, course_id, bank_name)
                title = bank_name
        # Validate size and XML before creating a plan; bytes stay in memory.
        archive = qti_archive(normalized, title, append=bank_id is not None)
        return await plan_store.create(action='question_bank_import',
            summary=f"{'Append to' if bank_id else 'Create'} Classic Question Bank: {title}",
            preview={'course_id': course_id, 'bank_id': bank_id, 'bank_name': bank_name,
                     'question_count': len(normalized), 'questions': normalized},
            mutations=[Mutation('QTI_IMPORT', f'/api/v1/courses/{course_id}/content_migrations',
                                data={'archive': archive}, label='Import bank questions')],
            preconditions=guards, warnings=[
                'Canvas imports asynchronously. Accepted upload does not mean questions are available.',
                'This appends questions; retrying an uncertain import can create duplicates. Inspect migration status and the bank first.',
                'Linked media is not bundled in this text-only QTI package. Verify any referenced files are accessible in the destination course.',
            ])

    async def canvas_get_question_bank_import(self, course_id: CanvasID, migration_id: CanvasID) -> dict:
        """Check a Classic bank QTI import's workflow state and all migration issues. Completed describes Canvas processing only: inspect the target bank and question count before reporting successful authoring. Do not retry an uncertain or partially successful import blindly."""
        course_id, migration_id = numeric_id(course_id), numeric_id(migration_id)
        endpoint = f'/api/v1/courses/{course_id}/content_migrations/{migration_id}'
        async with AsyncCanvasClient.from_environment() as client:
            migration = await client.get(endpoint)
            if str(migration.get('id')) != migration_id or migration.get('migration_type') != 'qti_converter':
                raise ValueError('This is not the requested QTI content migration')
            issues = await pages(client, endpoint + '/migration_issues')
        return {'course_id': course_id, 'migration_id': migration_id,
                'workflow_state': migration.get('workflow_state'),
                'started_at': migration.get('started_at'), 'finished_at': migration.get('finished_at'),
                'issues': [{k: issue[k] for k in ('id', 'issue_type', 'workflow_state', 'description') if k in issue}
                           for issue in issues],
                'bank_verified': False,
                'next_step': 'When processing completes, list/read the target bank to verify its questions. Resolve issues and inspect partial imports before retrying.'}

    async def canvas_plan_question_bank_draw(
        self, course_id: CanvasID, quiz_id: CanvasID, bank_id: CanvasID,
        name: Annotated[str, Field(min_length=1, max_length=255)],
        pick_count: Count, question_points: Points,
    ) -> dict:
        """Add a random-draw question group linked to a course Classic Question Bank. quiz_id must be a Classic quiz ID, not a New Quiz assignment ID. pick_count cannot exceed bank size; question_points overrides each drawn question's points. Creates a new group, not an edit to an existing group."""
        course_id, quiz_id, bank_id = map(numeric_id, (course_id, quiz_id, bank_id))
        if not name.strip() or isinstance(pick_count, bool) or not isinstance(pick_count, int) or pick_count < 1:
            raise ValueError('Provide a group name and a positive integer pick_count')
        quiz_endpoint = f'/api/v1/courses/{course_id}/quizzes/{quiz_id}'
        async with AsyncCanvasClient.from_environment() as client:
            bank, guard = await bank_details(client, course_id, bank_id)
            count = bank.get('assessment_question_count')
            if isinstance(count, bool) or not isinstance(count, int) or count < pick_count:
                raise ValueError('Bank question count is unavailable or smaller than pick_count')
            quiz = await client.get(quiz_endpoint)
            if str(quiz.get('id')) != quiz_id or quiz.get('quiz_type') not in {'practice_quiz', 'assignment', 'survey', 'graded_survey'} or quiz.get('quiz_engine') == 'new_quizzes':
                raise ValueError('The target must be a Classic Quiz')
        group = {'name': name.strip(), 'pick_count': pick_count, 'question_points': question_points,
                 'assessment_question_bank_id': bank_id}
        return await plan_store.create(action='question_bank_draw', summary='Add a bank-backed random question draw',
            preview={'course_id': course_id, 'quiz_id': quiz_id, 'bank': bank, 'group': group},
            mutations=[Mutation('POST', quiz_endpoint + '/groups', json_data={'quiz_groups': [group]})],
            preconditions=[guard, Precondition(quiz_endpoint, fingerprint(quiz))],
            warnings=['Changes to a published quiz can affect future attempts. Existing attempts are not regraded.'] if quiz.get('published') else [])


async def upload_qti(upload, archive):
    url = upload.get('upload_url')
    parsed = urlsplit(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Canvas did not provide a valid HTTPS upload URL')
    # A separate client prevents the Canvas bearer token reaching storage hosts.
    async with httpx2.AsyncClient(timeout=httpx2.Timeout(60, connect=5), follow_redirects=True) as uploader:
        response = await uploader.post(url, data=upload.get('upload_params', {}),
            files={'file': ('question-bank.zip', archive, 'application/zip')})
        if not 200 <= response.status_code < 300:
            raise ValueError('Canvas did not confirm the QTI upload')


async def apply_question_bank_plan(client, plan, progress):
    mutation = plan.mutations[0]
    await progress.set_message('Applying Classic Question Bank change')
    if plan.action == 'question_bank_draw':
        try:
            value = await client.post(mutation.endpoint, json_data=mutation.json_data)
            groups = value.get('quiz_groups', []) if isinstance(value, dict) else []
            expected = mutation.json_data['quiz_groups'][0]
            verified = len(groups) == 1 and all(
                groups[0].get(k) == v if k in {'name', 'pick_count', 'question_points'}
                else str(groups[0].get(k)) == str(v) for k, v in expected.items())
            result = {'action': plan.action, 'status': 'completed' if verified else 'uncertain',
                      'result': value, 'next_step': 'Inspect the returned group and its bank link before retrying; Canvas may silently reject invalid bank links.'}
        except Exception as exc:
            result = {'action': plan.action, 'status': write_failure_status(exc),
                      'next_step': 'Inspect quiz question groups before retrying; the write may have been accepted.'}
    else:
        target = plan.preview
        if target['bank_name'] is not None:
            # Repeat just before creating the migration so an intervening bank
            # creation does not quietly turn "create" into an append operation.
            await check_new_bank_name(client, target['course_id'], target['bank_name'])
        data = {'migration_type': 'qti_converter', 'pre_attachment[name]': 'question-bank.zip',
                'pre_attachment[size]': len(mutation.data['archive']),
                'settings[overwrite_quizzes]': 'false'}
        key = 'question_bank_id' if target['bank_id'] is not None else 'question_bank_name'
        data[f'settings[{key}]'] = target['bank_id'] if target['bank_id'] is not None else target['bank_name']
        result = {'action': plan.action, 'course_id': target['course_id'], 'bank_id': target['bank_id'],
                  'bank_name': target['bank_name'], 'expected_added_questions': target['question_count'],
                  'next_step': 'Poll canvas_get_question_bank_import, then inspect bank questions. Do not create another import until uncertain or partial results are resolved.'}
        try:
            migration = await client.post(mutation.endpoint, data=data)
            result['migration_id'] = numeric_id(migration.get('id'))
            result['status'] = 'uncertain'
            await upload_qti(migration.get('pre_attachment') or {}, mutation.data['archive'])
            result['status'] = 'accepted'
        except Exception as exc:
            result['status'] = 'uncertain' if result.get('migration_id') else write_failure_status(exc)
            # Exceptions can contain signed URLs. Return no raw upload response,
            # credentials, or exception text to the model or server logs.
            result['error'] = 'Canvas did not confirm the complete import upload workflow.'
            if not result.get('migration_id'):
                result['next_step'] = 'Inspect list_content_migrations before retrying; a migration may have been created without a returned ID.'
    await progress.increment()
    return result


def write_failure_status(exc):
    return 'failed' if isinstance(exc, CanvasAPIError) and 400 <= exc.status < 500 else 'uncertain'
