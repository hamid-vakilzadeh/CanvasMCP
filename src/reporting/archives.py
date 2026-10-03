"""Read ZIP inventories and selected members without extracting paths to disk.

Python zipfile documentation verified 2026-10-03:
https://docs.python.org/3.13/library/zipfile.html
Called inside the credential-free, time-limited document parser process.
"""

import base64
from collections import Counter
import hashlib
import io
import json
from pathlib import PurePosixPath, PureWindowsPath
import stat
import zipfile

from reporting.documents import (
    IMAGE_SUFFIXES, MAX_EXPANDED_BYTES, MAX_FILE_BYTES, MAX_IMAGE_BYTES,
    SUPPORTED, extract_document, inspect_image,
)

MAX_ARCHIVE_ENTRIES = 500
MAX_MEMBER_NAME = 1024


def _member_reason(entry, counts):
    name = entry.filename
    path = PurePosixPath(name)
    if (not name or len(name) > MAX_MEMBER_NAME or name != entry.orig_filename
            or path.is_absolute() or PureWindowsPath(name).drive
            or '\\' in name or '..' in path.parts
            or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        return 'unsafe_archive_path'
    if counts[name] > 1:
        return 'duplicate_archive_member'
    kind = stat.S_IFMT(entry.external_attr >> 16)
    if kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
        return 'archive_special_file_not_supported'
    if entry.is_dir() or kind == stat.S_IFDIR:
        return 'archive_directory'
    if entry.flag_bits & 1:
        return 'encrypted_archive_member'
    if entry.compress_type not in {
        zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA,
    }:
        return 'archive_compression_not_supported'
    if path.suffix.lower() == '.zip':
        return 'nested_archive_not_supported'
    if path.suffix.lower() not in SUPPORTED | IMAGE_SUFFIXES:
        return 'unsupported_format'
    if entry.file_size > MAX_FILE_BYTES:
        return 'file_size_limit'
    if path.suffix.lower() in IMAGE_SUFFIXES and entry.file_size > MAX_IMAGE_BYTES:
        return 'image_size_limit'
    return None


def extract_archive(data: bytes, member: str | None = None) -> dict:
    """List entries, or parse exactly one member with bounded reads and CRC checks."""
    archive_info = {'mode': 'inventory' if member is None else 'member', 'contents_read': False}
    if member is not None:
        archive_info['member'] = member

    def failure(reason):
        return {'segments': [], 'gaps': [{'location': member or 'archive', 'reason': reason}],
                'complete': False, 'archive': archive_info}

    if len(data) > MAX_FILE_BYTES:
        return failure('file_size_limit')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                return failure('archive_entry_limit')
            if any(len(entry.filename) > MAX_MEMBER_NAME for entry in entries):
                return failure('archive_member_name_limit')
            if sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES:
                return failure('archive_expansion_limit')
            counts = Counter(entry.filename for entry in entries)
            archive_info['entry_count'] = len(entries)
            if member is None:
                segments, gaps = [], []
                for entry in entries:
                    reason = _member_reason(entry, counts)
                    record = {'archive_member': entry.filename, 'size': entry.file_size,
                              'readable': reason is None}
                    if reason:
                        record['unavailable_reason'] = reason
                        if reason != 'archive_directory':
                            gaps.append({'location': entry.filename, 'reason': reason})
                    segments.append({'location': 'archive entry', 'text': json.dumps(record)})
                if not entries:
                    gaps.append({'location': 'archive', 'reason': 'empty_archive'})
                else:
                    # Shared report collection consumes coverage gaps, not archive metadata.
                    gaps.append({'location': 'archive', 'reason': 'archive_contents_not_read'})
                archive_info['inventory_complete'] = True
                archive_info['next_step'] = (
                    'This is a file listing, not the contents. Call the same reader with '
                    'archive_member set to an exact listed name; repeat for each relevant file.'
                )
                return {'segments': segments, 'gaps': gaps, 'complete': False, 'archive': archive_info}

            entry = next((entry for entry in entries if entry.filename == member), None)
            if entry is None:
                return failure('archive_member_not_found')
            reason = _member_reason(entry, counts)
            if reason:
                return failure(reason)
            with archive.open(entry) as stream:
                content = stream.read(MAX_FILE_BYTES + 1)
            if len(content) > MAX_FILE_BYTES:
                return failure('file_size_limit')
            if len(content) != entry.file_size:
                return failure('archive_member_size_mismatch')
            archive_info.update(size=len(content), sha256=hashlib.sha256(content).hexdigest())
            if PurePosixPath(member).suffix.lower() in IMAGE_SUFFIXES:
                extracted = inspect_image(content)
                if extracted.get('image'):
                    extracted['image_data'] = base64.b64encode(content).decode('ascii')
            else:
                extracted = extract_document(content, member)
            for item in [*extracted['segments'], *extracted['gaps']]:
                item['location'] = f"{member} / {item['location']}"
            archive_info['contents_read'] = extracted['complete']
            return {**extracted, 'archive': archive_info}
    except Exception:
        # Exceptions can contain private filenames or content; return fixed codes.
        return failure('archive_parse_failed')
