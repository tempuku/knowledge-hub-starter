"""P-02 reminder projection regressions."""
import unittest
from reminders import project_reminders, ReminderError


class ReminderTests(unittest.TestCase):
    def record(self, reminders):
        return {'id': '123e4567-e89b-42d3-a456-426614174000', 'title': 'Example',
                'status': 'completed', 'reminders': reminders}

    def test_year_crossing_inclusive_written_dates(self):
        result = project_reminders([self.record([[['2026-12-31', '2027-01-02'], 'Review']])])
        self.assertEqual(list(result), ['2026-12', '2027-01'])
        self.assertEqual(result['2027-01']['items'][0]['end_date'], '2027-01-02')

    def test_offset_preserved(self):
        when = ['2026-12-31T23:00:00+03:00', '2027-01-01T00:00:00+03:00']
        result = project_reminders([self.record([[when, 'Check']])])
        self.assertEqual(result['2026-12']['items'][0]['when'], when)

    def test_duplicate_and_mixed_offset_rejected(self):
        for entries in [
            [['2026-12-01', 'Same'], ['2026-12-01', 'Same']],
            [[['2026-12-01T10:00:00+01:00', '2026-12-01T11:00:00+02:00'], 'Different offsets']],
            [[['2026-12-01', '2026-12-01T11:00:00+01:00'], 'Mixed']],
        ]:
            with self.assertRaises(ReminderError):
                project_reminders([self.record(entries)])

    def test_invalid_dates_and_reversed_range(self):
        for when in ['2026-02-30', ['2026-12-03', '2026-12-01'], '2026-12-01T12:00:00']:
            with self.assertRaises(ReminderError):
                project_reminders([self.record([[when, 'Bad']])])


if __name__ == '__main__':
    unittest.main()
