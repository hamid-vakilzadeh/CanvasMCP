"""Recognize Canvas file references in API-returned HTML; never fetch authored URLs."""

from html.parser import HTMLParser
import re
from urllib.parse import parse_qs, urljoin, urlsplit

from canvas_client import _origin


class CanvasFileLinks(HTMLParser):
    """Collect file IDs from the same Canvas origin and the selected course/user."""

    def __init__(self, canvas_url, course_id, user_id=None):
        super().__init__(convert_charrefs=True)
        self.canvas_url = canvas_url
        self.course_id = str(course_id)
        self.user_id = str(user_id) if user_id is not None else None
        self.ids = {}
        self.verifiers = {}

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key not in {'href', 'src', 'data-api-endpoint'} or not value:
                continue
            try:
                url = urljoin(self.canvas_url + '/', value)
                parsed = urlsplit(url)
                if parsed.username or parsed.password or _origin(url) != _origin(self.canvas_url):
                    continue
                match = re.fullmatch(
                    r'/(?:api/v1/)?(?:(courses|users)/([0-9]+)/)?files/([0-9]+)(?:/(?:download|preview))?/?',
                    parsed.path,
                )
                if not match or int(match[3]) < 1:
                    continue
                context, owner = match[1], str(int(match[2])) if match[2] else None
                if context == 'courses' and owner != self.course_id:
                    continue
                if context == 'users' and owner != self.user_id:
                    continue
                file_id = str(int(match[3]))
                self.ids[file_id] = None
                # Canvas may retain a file access verifier inside a submitted
                # rich-text answer. Only this bounded value can be forwarded to
                # the canonical Files API, which validates it for that file.
                verifier = parse_qs(parsed.query).get('verifier', [])
                if len(verifier) == 1 and re.fullmatch(r'[A-Za-z0-9_.-]{1,4096}', verifier[0]):
                    self.verifiers[file_id] = verifier[0]
            except ValueError:
                continue
