"""Course student groups and group sets (Canvas group categories)."""

from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from action_plans import Mutation, Precondition, fingerprint, plan_store
from canvas_client import AsyncCanvasClient, CanvasAPIError, decode_cursor
from tools.assistant import PLAN_ONLY, READ_ONLY, _assistant_tool
from tools.quiz_accommodations import CanvasID, numeric_id, not_boolean, pages, unique_ids


class GroupSetChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    self_signup: Literal['enabled', 'restricted'] | None = None
    auto_leader: Literal['first', 'random'] | None = None
    group_limit: Annotated[int, Field(ge=1), BeforeValidator(not_boolean)] | None = None


class GroupChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    description: str | None = None


def validate_changes(changes, model, operation):
    if isinstance(changes, dict):
        changes = model.model_validate(changes)
    payload = changes.model_dump(exclude_unset=True)
    if not payload:
        raise ValueError('Provide at least one group change')
    if operation == 'create' or 'name' in payload:
        if not isinstance(payload.get('name'), str) or not payload['name'].strip():
            raise ValueError('A non-empty name is required')
    if operation not in {'create', 'update'}:
        raise ValueError('Choose create or update')
    return payload


async def course_object(client, endpoint, course_id, *, object_id=None, write=False):
    item = await client.get(endpoint)
    if not isinstance(item, dict) or str(item.get('course_id')) != course_id or item.get('context_type') != 'Course':
        raise ValueError('The group or group set does not belong to the requested course')
    if object_id is not None and str(item.get('id')) != object_id:
        raise ValueError('Canvas returned a mismatched group or group-set ID')
    if item.get('non_collaborative'):
        raise ValueError('These tools manage collaborative student groups, not differentiation tags')
    if write and (item.get('protected') or item.get('role') in {'communities', 'student_organized'}):
        raise ValueError('Use a course project group set for this operation')
    if write and endpoint.startswith('/api/v1/group_categories/'):
        # Some Canvas versions omit non_collaborative from category JSON.
        # Confirm membership in the collaborative-only collection before updates.
        categories = await pages(client, f'/api/v1/courses/{course_id}/group_categories',
                                 params={'collaboration_state': 'collaborative'})
        if not any(str(category.get('id')) == str(item['id']) for category in categories):
            raise ValueError('This is not a visible collaborative course group set')
    return item, Precondition(endpoint, fingerprint(item))


async def scoped_page(client, endpoint, *, cursor=None, limit=50, params=None):
    if cursor and urlsplit(decode_cursor(cursor)).path != endpoint:
        raise ValueError('This pagination cursor belongs to a different group collection')
    return await client.page(endpoint, cursor=cursor, limit=limit, params=params)


async def snapshot_collection(client, endpoint, guards):
    # Compare the entire current collection at apply time, not only the pages
    # that existed at planning time. An added last page must invalidate the plan.
    items = await pages(client, endpoint)
    guards.append(Precondition(endpoint, fingerprint(items), paginated=True))
    return items


class GroupTools:
    def __init__(self, mcp):
        for fn in (self.canvas_list_group_sets, self.canvas_list_groups, self.canvas_get_group):
            mcp.tool(_assistant_tool(fn), annotations=READ_ONLY, tags={'advanced', 'groups', 'read'})
        for fn in (self.canvas_plan_group_set_change, self.canvas_plan_group_change,
                   self.canvas_plan_group_membership_change):
            mcp.tool(_assistant_tool(fn), annotations=PLAN_ONLY, tags={'advanced', 'groups', 'plan'})

    async def canvas_list_group_sets(
        self, course_id: CanvasID, cursor: str | None = None,
        limit: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict:
        """View course student group sets (Canvas group categories), with signup/leader settings and pagination. These are not assignment grade-weight groups."""
        course_id = numeric_id(course_id)
        async with AsyncCanvasClient.from_environment() as client:
            result = await scoped_page(client, f'/api/v1/courses/{course_id}/group_categories',
                cursor=cursor, limit=limit, params={'collaboration_state': 'collaborative'})
        return {'course_id': course_id, **result}

    async def canvas_list_groups(
        self, course_id: CanvasID, group_set_id: CanvasID | None = None,
        cursor: str | None = None, limit: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict:
        """View student project groups across a course or inside one group set. Follow next_cursor for more groups; group_set_id is Canvas group_category_id."""
        course_id = numeric_id(course_id)
        async with AsyncCanvasClient.from_environment() as client:
            category = None
            if group_set_id is not None:
                group_set_id = numeric_id(group_set_id)
                category, _ = await course_object(client, f'/api/v1/group_categories/{group_set_id}', course_id, object_id=group_set_id)
                endpoint = f'/api/v1/group_categories/{group_set_id}/groups'
                params = None
            else:
                endpoint = f'/api/v1/courses/{course_id}/groups'
                params = {'collaboration_state': 'collaborative'}
            result = await scoped_page(client, endpoint, cursor=cursor, limit=limit, params=params)
        return {'course_id': course_id, 'group_set': category, **result}

    async def canvas_get_group(
        self, course_id: CanvasID, group_id: CanvasID,
        view: Literal['details', 'members', 'memberships'] = 'members',
        cursor: str | None = None, limit: Annotated[int, Field(ge=1, le=100)] = 50,
    ) -> dict:
        """View a student group and its paginated members. members returns user names; memberships returns membership IDs and accepted/invited/requested states. details skips roster loading."""
        course_id, group_id = numeric_id(course_id), numeric_id(group_id)
        if view not in {'details', 'members', 'memberships'}:
            raise ValueError('Choose details, members or memberships')
        if view == 'details' and cursor is not None:
            raise ValueError('A cursor is only valid for members or memberships')
        async with AsyncCanvasClient.from_environment() as client:
            group, _ = await course_object(client, f'/api/v1/groups/{group_id}', course_id, object_id=group_id)
            result = {'group': group, 'view': view}
            if view != 'details':
                endpoint = f'/api/v1/groups/{group_id}/' + ('users' if view == 'members' else 'memberships')
                result.update(await scoped_page(client, endpoint, cursor=cursor, limit=limit))
        return result

    async def canvas_plan_group_set_change(
        self, course_id: CanvasID, operation: Literal['create', 'update'],
        changes: GroupSetChanges, group_set_id: CanvasID | None = None,
    ) -> dict:
        """Create or edit course student group sets (Canvas group categories). Preview changes before applying. Null clears signup/leader/size settings; omitted settings are preserved. A group size limit requires self signup."""
        course_id = numeric_id(course_id)
        payload = validate_changes(changes, GroupSetChanges, operation)
        guards, before = [], {}
        if operation == 'create':
            if group_set_id is not None:
                raise ValueError('group_set_id is only allowed for update')
            endpoint = f'/api/v1/courses/{course_id}/group_categories'
        else:
            group_set_id = numeric_id(group_set_id)
            endpoint = f'/api/v1/group_categories/{group_set_id}'
            async with AsyncCanvasClient.from_environment() as client:
                before, guard = await course_object(client, endpoint, course_id, object_id=group_set_id, write=True)
                guards.append(guard)
        effective = {**before, **payload}
        if effective.get('group_limit') is not None and effective.get('self_signup') not in {'enabled', 'restricted'}:
            raise ValueError('group_limit requires self_signup=enabled or restricted; use group_limit=null when disabling signup')
        # Canvas's category update resets omitted settings. Preserve the values
        # we read, including newer self-signup deadlines, when only renaming.
        preserved = ('self_signup', 'auto_leader', 'group_limit', 'self_signup_end_at')
        if operation == 'update' and not all(key in before for key in preserved[:3]):
            raise ValueError('Canvas omitted existing group-set settings; cannot safely preserve them during update')
        wire = {**{key: before[key] for key in preserved if key in before}, **payload}
        if 'self_signup_end_at' in wire and wire.get('self_signup') != 'enabled':
            wire['self_signup_end_at'] = None
        return await plan_store.create(action='group_set_change',
            summary=f'{operation.title()} course {course_id} group set',
            preview={'course_id': course_id, 'before': before, 'changes': payload, 'settings_sent': wire},
            mutations=[Mutation('POST' if operation == 'create' else 'PUT', endpoint, json_data=wire)],
            preconditions=guards, warnings=['Group-set settings affect its groups. Creating a set does not create groups or assign students.'])

    async def canvas_plan_group_change(
        self, course_id: CanvasID, operation: Literal['create', 'update'], changes: GroupChanges,
        group_set_id: CanvasID | None = None, group_id: CanvasID | None = None,
    ) -> dict:
        """Create or edit student project groups: name and plain-text description. Create requires group_set_id (Canvas group_category_id); update requires group_id. Use the membership planner to assign, move or remove students."""
        course_id = numeric_id(course_id)
        payload = validate_changes(changes, GroupChanges, operation)
        async with AsyncCanvasClient.from_environment() as client:
            if operation == 'create':
                if group_id is not None:
                    raise ValueError('group_id is only allowed for update')
                group_set_id = numeric_id(group_set_id)
                category, guard = await course_object(client, f'/api/v1/group_categories/{group_set_id}', course_id, object_id=group_set_id, write=True)
                endpoint, before = f'/api/v1/group_categories/{group_set_id}/groups', None
            else:
                if group_set_id is not None:
                    raise ValueError('Changing an existing group set is not supported; omit group_set_id for update')
                group_id = numeric_id(group_id)
                endpoint = f'/api/v1/groups/{group_id}'
                before, guard = await course_object(client, endpoint, course_id, object_id=group_id, write=True)
                category = None
        return await plan_store.create(action='group_change',
            summary=f'{operation.title()} course {course_id} student group',
            preview={'course_id': course_id, 'group_set': category, 'before': before, 'changes': payload},
            mutations=[Mutation('POST' if operation == 'create' else 'PUT', endpoint, json_data=payload)],
            preconditions=[guard], warnings=['This changes group details only. Use the membership planner after creation to assign students.'])

    async def canvas_plan_group_membership_change(
        self, course_id: CanvasID, group_id: CanvasID, operation: Literal['add', 'remove'],
        student_ids: Annotated[list[CanvasID], Field(min_length=1, max_length=100)],
        allow_moves: bool = False,
    ) -> dict:
        """Plan adding/removing students in a course project group. Adding can move a student out of another group in the same set; such moves require allow_moves=true and appear in the preview. Memberships are read across every page before planning. Existing accepted members/absent removals are skipped."""
        course_id, group_id = numeric_id(course_id), numeric_id(group_id)
        students = unique_ids(student_ids, 'student_ids')
        if operation not in {'add', 'remove'} or len(students) > 100:
            raise ValueError('Choose add/remove with at most 100 students')
        if operation == 'remove' and allow_moves:
            raise ValueError('allow_moves is only valid for add')
        guards, mutations, changes, skipped = [], [], [], []
        async with AsyncCanvasClient.from_environment() as client:
            group, guard = await course_object(client, f'/api/v1/groups/{group_id}', course_id, object_id=group_id, write=True)
            guards.append(guard)
            category_id = numeric_id(group.get('group_category_id'))
            category, guard = await course_object(client, f'/api/v1/group_categories/{category_id}', course_id, object_id=category_id, write=True)
            guards.append(guard)
            target_members = await snapshot_collection(client, f'/api/v1/groups/{group_id}/memberships', guards)
            members = {str(m['user_id']): m for m in target_members}
            other_groups = {s: [] for s in students}
            if operation == 'add':
                inventory = await snapshot_collection(client, f'/api/v1/group_categories/{category_id}/groups', guards)
                for peer in inventory:
                    peer_id = numeric_id(peer['id'])
                    if peer_id == group_id:
                        continue
                    if str(peer.get('group_category_id')) != category_id or str(peer.get('course_id')) != course_id:
                        raise ValueError('Canvas returned a group outside the requested group set')
                    memberships = await snapshot_collection(client, f'/api/v1/groups/{peer_id}/memberships', guards)
                    for member in memberships:
                        student = str(member.get('user_id'))
                        if student in other_groups and member.get('workflow_state') == 'accepted':
                            other_groups[student].append({'group_id': peer_id, 'group_name': peer.get('name')})
            for student in students:
                previous = members.get(student)
                if operation == 'add' and previous and previous.get('workflow_state') == 'accepted':
                    skipped.append({'student_id': student, 'reason': 'already_member'})
                    continue
                if operation == 'remove' and not previous:
                    skipped.append({'student_id': student, 'reason': 'not_a_member'})
                    continue
                if operation == 'add':
                    enrollments = await pages(client, f'/api/v1/courses/{course_id}/enrollments',
                        params={'user_id': student, 'type[]': ['StudentEnrollment']})
                    if not any(str(e.get('user_id')) == student and e.get('type') == 'StudentEnrollment'
                               and e.get('enrollment_state') == 'active' for e in enrollments):
                        raise ValueError(f'Student {student} is not actively enrolled in this course')
                    if other_groups[student] and not allow_moves:
                        raise ValueError(f'Student {student} is already in another group in this set: {other_groups[student]}. Set allow_moves=true to preview that move.')
                    # Existing invitations/requests require explicit acceptance.
                    method = 'PUT' if previous else 'POST'
                    endpoint = (f'/api/v1/groups/{group_id}/users/{student}' if previous
                                else f'/api/v1/groups/{group_id}/memberships')
                    payload = {'workflow_state': 'accepted'} if previous else {'user_id': student}
                else:
                    method, endpoint, payload = 'DELETE', f'/api/v1/groups/{group_id}/users/{student}', None
                mutations.append(Mutation(method, endpoint, json_data=payload, label=f'{operation}:{student}'))
                changes.append({'student_id': student, 'operation': operation,
                    'previous_membership': previous, 'moves_from': other_groups[student]})
        if not mutations:
            raise ValueError('All requested memberships already match; no plan is needed')
        return await plan_store.create(action='group_membership_change',
            summary=f'{operation.title()} {len(mutations)} student(s) in group {group_id}',
            preview={'course_id': course_id, 'group': group, 'group_set': category,
                     'changes': changes, 'skipped': skipped}, mutations=mutations, preconditions=guards,
            warnings=['Membership changes can affect access to group work, submissions, and group-assignment grading.',
                      'Moves remove accepted membership in another group of the same set. Canvas may notify students.',
                      'Each student is updated separately; inspect partial or uncertain results before retrying.'])


async def apply_group_plan(client, plan, progress):
    """Keep lost-response uncertainty separate from definite group write failures."""
    results = []
    for index, mutation in enumerate(plan.mutations):
        await progress.set_message('Applying Canvas group change')
        try:
            if mutation.method == 'DELETE':
                value = await client.delete(mutation.endpoint)
                confirmed = isinstance(value, dict) and value.get('ok') is True
            else:
                send = client.post if mutation.method == 'POST' else client.put
                value = await send(mutation.endpoint, json_data=mutation.json_data)
                confirmed = isinstance(value, dict) and value.get('id') is not None
                if confirmed and plan.action == 'group_membership_change':
                    confirmed = (str(value.get('user_id')) == mutation.label.split(':')[1]
                                 and str(value.get('group_id')) == str(plan.preview['group']['id'])
                                 and value.get('workflow_state') == 'accepted')
            results.append({'label': mutation.label or f'mutation:{index + 1}',
                            'status': 'applied' if confirmed else 'uncertain', 'result': value})
        except Exception as exc:
            definite = isinstance(exc, CanvasAPIError) and 400 <= exc.status < 500
            results.append({'label': mutation.label or f'mutation:{index + 1}',
                            'status': 'failed' if definite else 'uncertain', 'error': str(exc)})
        await progress.increment()
    counts = {s: sum(r['status'] == s for r in results) for s in ('applied', 'failed', 'uncertain')}
    status = ('completed' if counts['applied'] == len(results) else 'partial' if counts['applied']
              else 'uncertain' if counts['uncertain'] else 'failed')
    return {'action': plan.action, 'status': status, **counts, 'results': results,
            'next_step': 'Use group reads to inspect results. An invited/requested membership is not confirmed enrollment. Verify uncertain writes before retrying; do not repeat successful creates or membership changes.'}
