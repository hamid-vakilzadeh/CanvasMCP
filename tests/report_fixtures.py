"""Entirely synthetic Canvas responses shared by backend and browser checks."""

import asyncio
import copy


class SyntheticCanvas:
    base_url = 'https://canvas.example.invalid'
    access_token = 'synthetic-token-not-a-credential'
    calls = []
    delay = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    @staticmethod
    def assignments():
        return [{'id': str(i), 'name': title, 'points_possible': 10,
                 'description': '<p>Explain the control, identify its owner, and evaluate its limitations.</p>',
                 'html_url': f'https://canvas.example.invalid/courses/42/assignments/{i}',
                 **extra} for i, title, extra in [
                   (11, 'Control analysis', {}), (12, 'Module 5 reflection', {'quiz_id': '22'}),
                   (13, 'Applied quiz', {'is_quiz_lti_assignment': True}), (14, 'Anonymous peer exercise', {'anonymous_grading': True})]]

    async def get(self, endpoint, params=None):
        self.calls.append(('GET', endpoint))
        if self.delay:
            await asyncio.sleep(self.delay)
        if endpoint == '/api/v1/users/self':
            return {'id': '99'}
        if endpoint.endswith('/enrollments'):
            student = str((params or {}).get('user_id', '7'))
            return [{'user_id': student, 'user': {'id': student, 'name': f'Synthetic Student {student}'},
                     'enrollment_state': 'active', 'grades': {'current_score': 81.25 if student == '7' else 67.5, 'final_score': 64}}]
        if endpoint.endswith('/progress'):
            return {'requirement_count': 5, 'requirement_completed_count': 3}
        if endpoint.endswith('/activity'):
            return {'page_views': {'2026-09-01T00:00:00Z': 3}, 'participations': [{'created_at': '2026-09-02T14:00:00Z'}]}
        if endpoint == '/api/v1/courses/42':
            return {'id': '42', 'name': 'Synthetic · Accounting information systems', 'syllabus_body': '<p>Evaluate internal controls using evidence and limitations.</p>'}
        if endpoint.endswith('/pages/control-guide'):
            return {'published': True, 'body': '<p>Segregation of duties separates authorization, custody, and recording. No control prevents every possible error.</p>'}
        if '/submissions/' in endpoint and '/assignments/' in endpoint:
            assignment_id = endpoint.split('/assignments/')[1].split('/')[0]
            if assignment_id == '14':
                return {'anonymous_id': 'hidden-identity', 'body': 'Must not be associated with a student.'}
            return {'id': '91', 'user_id': endpoint.rsplit('/', 1)[-1], 'assignment_id': assignment_id,
                    'attempt': 2, 'body': '<p>Separating custody from recording reduces the opportunity to conceal errors, but collusion remains possible.</p>',
                    'score': 8, 'submitted_at': '2026-09-02T12:00:00Z',
                    'submission_history': [{'attempt': 1, 'body': '<p>Segregation of duties prevents all fraud.</p>', 'submitted_at': '2026-09-01T12:00:00Z'},
                                           {'attempt': 2, 'body': '<p>Separating custody from recording reduces the opportunity to conceal errors, but collusion remains possible.</p>', 'submitted_at': '2026-09-02T12:00:00Z'}],
                    'submission_comments': [{'id': '33', 'comment': 'Explain why collusion can bypass the control.'}],
                    'rubric_assessment': {'criterion-a': {'points': 3, 'comments': 'Mechanism identified; explanation of limitations needs more detail.'}}}
        if '/assignments/' in endpoint:
            result = next(copy.deepcopy(a) for a in self.assignments() if a['id'] == endpoint.rsplit('/', 1)[-1])
            result['rubric'] = [{'id': 'criterion-a', 'description': 'Reasoning about control limitations', 'points': 5}]
            return result
        if endpoint.endswith('/discussion_topics/31'):
            return {'id': '31', 'title': 'Control design discussion', 'message': '<p>Explain a control and its limitation.</p>', 'published': True, 'locked': False}
        if endpoint.endswith('/discussion_topics/31/view'):
            return {'view': [{'id': '100', 'user_id': '8', 'message': 'Can one person approve and record a transaction?',
                             'replies': [{'id': str(101+i), 'user_id': '7' if i == 11 else '8',
                                          'message': 'Separate the responsibilities, but account for collusion.' if i == 11 else 'Synthetic peer context.'}
                                         for i in range(15)]}], 'new_entries': []}
        raise AssertionError('Unexpected synthetic endpoint: ' + endpoint)

    async def page(self, endpoint, *, params=None, cursor=None, limit=100):
        self.calls.append(('PAGE', endpoint))
        items = []
        if endpoint == '/api/v1/courses':
            items = [await self.get('/api/v1/courses/42')]
        elif endpoint.endswith('/enrollments'):
            items = await self.get(endpoint, params)
        elif endpoint.endswith('/courses/42/users'):
            items = [{'id': '7', 'name': 'Synthetic Student 7'}, {'id': '8', 'name': 'Synthetic Student 8'}]
        elif endpoint.endswith('/students/submissions'):
            items = [{'id': str(90+i), 'assignment_id': a['id'], 'assignment': a,
                      'score': 8 if i < 2 else None, 'workflow_state': 'graded' if i < 2 else 'unsubmitted',
                      'missing': i == 2, 'late': i == 1, 'excused': i == 3,
                      'submitted_at': f'2026-09-0{i+1}T12:00:00Z' if i < 2 else None} for i,a in enumerate(self.assignments())]
        elif endpoint.endswith('/modules'):
            items = [{'id': '51', 'name': 'Module 5 · Control evaluation', 'state': 'started', 'items_count': 1,
                      'items': [{'id': '61', 'type': 'Page', 'page_url': 'control-guide', 'title': 'Control guide'}]}]
        elif endpoint.endswith('/outcome_results'):
            items = [{'outcome_results': [{'id':'71','score':3,'possible':5,'mastery':False,'links':{'learning_outcome':'81'}}]}]
        elif endpoint.endswith('/outcome_rollups'):
            items = [{'rollups': [], 'linked': {'outcomes': [{'id':'81','title':'Evaluate control limitations'}]}}]
        elif endpoint.endswith('/assignments'):
            items = self.assignments()
        elif endpoint.endswith('/quizzes/22/submissions'):
            items = [{'quiz_submissions': [{'id': '23', 'user_id': '7', 'attempt': 2, 'workflow_state': 'complete'}]}]
        elif endpoint.endswith('/quizzes/22/questions'):
            items = [{'id': '24', 'question_type': 'essay_question', 'question_text': '<p>Explain a limitation of segregation of duties.</p>'},
                     {'id': '25', 'question_type': 'multiple_choice_question', 'question_text': 'AUTOGRADED CONTENT MUST NOT BE REVIEWED'}]
        elif endpoint.endswith('/quiz_submissions/23/questions'):
            items = [{'quiz_submission_questions': [{'id': '24', 'answer': None}, {'id': '25', 'answer': 'AUTO ANSWER MUST NOT BE REVIEWED'}]}]
        elif endpoint.endswith('/discussion_topics'):
            items = [{'id': '31', 'html_url': 'https://canvas.example.invalid/courses/42/discussion_topics/31'}]
        else:
            raise AssertionError('Unexpected synthetic pagination endpoint: ' + endpoint)
        return {'items': items, 'next_cursor': None}
