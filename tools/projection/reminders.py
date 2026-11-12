"""P-02 reminder read-model projection; no publication side effects."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime

DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$')


class ReminderError(ValueError):
    pass


def parse_when(value):
    if not isinstance(value, str):
        raise ReminderError('when must be a quoted date or offset-qualified timestamp')
    if DATE.fullmatch(value):
        try:
            return date.fromisoformat(value), False, None
        except ValueError as exc:
            raise ReminderError('invalid Gregorian date') from exc
    if TIMESTAMP.fullmatch(value):
        try:
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ReminderError('invalid timestamp') from exc
        offset = value[-6:] if value[-1] != 'Z' else 'Z'
        return stamp, True, offset
    raise ReminderError('invalid date or timestamp format')


def month_range(start: date, end: date):
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield f'{year:04d}-{month:02d}'
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def project_reminders(records):
    """Return month-keyed P-02 payloads; preserve written offsets and inclusive dates."""
    grouped = defaultdict(list)
    for record in records:
        seen = set()
        for reminder in record.get('reminders', []):
            if not isinstance(reminder, list) or len(reminder) != 2:
                raise ReminderError('reminder must be [when, text]')
            when, text = reminder
            if not isinstance(text, str) or not (1 <= len(text.strip()) <= 240) or text != text.strip():
                raise ReminderError('invalid reminder text')
            if isinstance(when, list):
                if len(when) != 2:
                    raise ReminderError('range must have two endpoints')
                start, end = when
            else:
                start = end = when
            first, timed, offset = parse_when(start)
            last, end_timed, end_offset = parse_when(end)
            if timed != end_timed or (timed and offset != end_offset):
                raise ReminderError('mixed endpoint types or offsets')
            if first > last:
                raise ReminderError('reversed reminder range')
            canonical = json.dumps(reminder, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            if canonical in seen:
                raise ReminderError('duplicate reminder')
            seen.add(canonical)
            rid = hashlib.sha256((record['id'] + '\n' + canonical).encode('utf-8')).hexdigest()
            start_date, end_date = start[:10], end[:10]
            item = {'id': rid, 'record_id': record['id'], 'title': record['title'],
                    'status': record['status'], 'when': when, 'text': text,
                    'start_date': start_date, 'end_date': end_date}
            for month in month_range(date.fromisoformat(start_date), date.fromisoformat(end_date)):
                grouped[month].append(item)
    for month, items in grouped.items():
        items.sort(key=lambda x: (x['start_date'],
                   0 if (isinstance(x['when'], str) and len(x['when']) == 10 or
                         isinstance(x['when'], list) and len(x['when'][0]) == 10) else 1,
                   x['title'].casefold(), x['id']))
    return {month: {'schema_version': 1, 'month': month, 'items': grouped[month]}
            for month in sorted(grouped)}
