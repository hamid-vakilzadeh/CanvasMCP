"""Consistent discussion snapshots for monitoring and evidence collection."""

from __future__ import annotations

from reporting.common import digest, sid


def flatten_entries(payload: dict) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get('view'), list):
        raise ValueError('Canvas discussion view is incomplete or unavailable')
    entries: dict[str, dict] = {}

    def visit(values, parent=None):
        for value in values:
            if not isinstance(value, dict) or value.get('id') is None:
                raise ValueError('Canvas returned an incomplete discussion entry')
            key = sid(value['id'])
            old = entries.get(key, {})
            explicit_parent = value.get('parent_id', value.get('parent_discussion_entry_id', parent))
            entry = {**old, **{k: value[k] for k in ('message', 'user_id', 'user_name', 'created_at', 'updated_at', 'deleted') if k in value},
                     'id': key, 'parent_id': str(explicit_parent) if explicit_parent is not None else old.get('parent_id')}
            entries[key] = entry
            replies = value.get('replies') or []
            if not isinstance(replies, list):
                raise ValueError('Canvas returned an incomplete discussion thread')
            visit(replies, key)
    visit(payload['view'])
    new = payload.get('new_entries') or []
    if not isinstance(new, list):
        raise ValueError('Canvas returned an incomplete discussion update')
    visit(new)
    return sorted(entries.values(), key=lambda e: e['id'])


def entry_fingerprint(entry: dict) -> str:
    return digest({k: entry.get(k) for k in ('id', 'parent_id', 'message', 'deleted', 'user_id')})


async def read_discussion(client, course_id: str, topic_id: str) -> dict:
    endpoint = f'/api/v1/courses/{sid(course_id)}/discussion_topics/{sid(topic_id)}'
    topic = await client.get(endpoint)
    if topic.get('group_topic_children'):
        raise ValueError('Group discussion roots are not supported; select an ordinary course discussion')
    payload = await client.get(f'{endpoint}/view', {'include_new_entries': 1})
    return {'topic': topic, 'entries': flatten_entries(payload), 'endpoint': endpoint}


def thread_context(snapshot: dict, entry_id: str) -> dict:
    by_id = {e['id']: e for e in snapshot['entries']}
    target = by_id.get(str(entry_id))
    if target is None or target.get('deleted'):
        raise ValueError('The discussion entry is unavailable or deleted')
    root, seen = target, set()
    while root.get('parent_id') in by_id and root['id'] not in seen:
        seen.add(root['id'])
        root = by_id[root['parent_id']]
    included = {root['id']}
    while True:
        children = {e['id'] for e in snapshot['entries'] if e.get('parent_id') in included}
        if children <= included:
            break
        included |= children
    entries = [e for e in snapshot['entries'] if e['id'] in included]
    topic = snapshot['topic']
    context = {'topic': {k: topic.get(k) for k in ('id', 'title', 'message', 'locked', 'published', 'anonymous_state')},
               'target': target, 'entries': entries}
    context['fingerprint'] = digest([context['topic'], [entry_fingerprint(e) for e in entries]])
    return context
