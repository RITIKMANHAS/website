from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase

from model_mommy import mommy
from pytz import UTC

from meetups import utils

from meetups.models import Meetup, MeetupUpdate
from meetups.utils import update_not_needed

description = '<p>We will be having a meetup in June. More details to follow.</p> <p>If you are ' \
              'interested in speaking, please submit your details to\xa0<a ' \
              'href="http://bit.ly/pyie-cfp-2015"><a href="http://bit.ly/pyie-cfp-2015" ' \
              'class="linkified">http://bit.ly/pyie-cfp-2015</a></a>.</p> <p>Enquiries? Please ' \
              'contact contact@python.ie.</p>'


class MeetupModelTests(TestCase):
    def test_create_meetup(self):
        meetup = mommy.make(Meetup)
        self.assertIsNotNone(meetup.id)
        self.assertIsNotNone(meetup.name)
        self.assertIsNotNone(meetup.description)
        self.assertIsNotNone(meetup.announced)
        self.assertIsNotNone(meetup.event_url)
        self.assertIsNotNone(meetup.time)
        self.assertIsNotNone(meetup.created)
        self.assertIsNotNone(meetup.updated)
        self.assertIsNotNone(meetup.rsvps)
        self.assertIsNotNone(meetup.maybe_rsvps)
        self.assertIsNotNone(meetup.waitlist_count)
        self.assertIsNotNone(meetup.status)
        self.assertIsNotNone(meetup.visibility)


class UtilsTests(TestCase):
    def _first_result(self):
        return {
            'results': [
                {
                    'maybe_rsvp_count': 7,
                    'id': 'qwfbshytjbnb',
                    'waitlist_count': 11,
                    'yes_rsvp_count': 24,
                    'utc_offset': 3600000,
                    'visibility': 'public',
                    'announced': False,
                    'updated': 1431467590000,
                    'description': description,
                    'name': 'Python Ireland meetup',
                    'event_url': 'http://www.meetup.com/pythonireland/events/221078098/',
                    'headcount': 0,
                    'time': 1433957400000,
                    'created': 1390942022000,
                    'group': {
                        'name': 'Python Ireland',
                        'id': 6943212,
                        'who': 'Pythonista',
                        'join_mode': 'open',
                        'created': 1359572645000,
                        'group_lon': -6.25,
                        'group_lat': 53.33000183105469,
                        'urlname': 'pythonireland'
                    },
                    'status': 'upcoming'
                }
            ]
        }

    def _second_result(self):
        first = self._first_result().copy()
        first['results'][0].update({'updated': 1431467600000})
        first['results'][0].update({'name': "New name"})
        return first

    def _third_result(self):
        first = self._first_result().copy()
        first['results'][0].update({'id': "qwfbshytjbnc"})
        first['results'][0].update({'name': "New entry"})
        return first

    def test_update_not_needed(self):
        result = update_not_needed()
        self.assertEqual(result, False)
        MeetupUpdate.tick()
        result = update_not_needed()
        self.assertEqual(result, True)
        MeetupUpdate._invalidate_meetup_update()
        result = update_not_needed()
        self.assertEqual(result, False)

    @patch('meetups.utils.get_content')
    def test_update_first_run(self, mock_get_content):
        mock_get_content.return_value = self._first_result()
        utils.update()
        meetups = Meetup.objects.all()
        self.assertEqual(len(meetups), 1)

        # Check all values are as expected
        meetup = meetups[0]
        expected_datetime = datetime(
            year=2015, month=6, day=10, hour=17, minute=30, tzinfo=UTC)
        self.assertEqual(meetup.time, expected_datetime)
        expected_datetime = datetime(
            year=2015, month=5, day=12, hour=21, minute=53, second=10, tzinfo=UTC)
        self.assertEqual(meetup.updated, expected_datetime)
        expected_datetime = datetime(
            year=2014, month=1, day=28, hour=20, minute=47, second=2, tzinfo=UTC)
        self.assertEqual(meetup.created, expected_datetime)
        self.assertEqual(meetup.rsvps, 24)
        self.assertEqual(meetup.maybe_rsvps, 7)
        self.assertEqual(meetup.waitlist_count, 11)
        self.assertEqual(meetup.name, 'Python Ireland meetup')
        self.assertEqual(meetup.description, description)
        self.assertEqual(meetup.status, 'upcoming')
        self.assertEqual(meetup.visibility, 'public')
        self.assertEqual(meetup.event_url, 'http://www.meetup.com/pythonireland/events/221078098/')

        # We should have ticked the MeetupUpdate
        meetup_update = MeetupUpdate.objects.filter().get()
        minute_ago = datetime.now(tz=UTC) - timedelta(minutes=1)
        self.assertGreater(meetup_update.updated, minute_ago)

    @patch('meetups.utils.get_content')
    def test_update_second_run(self, mock_get_content):
        mock_get_content.return_value = self._first_result()
        utils.update()
        meetups = Meetup.objects.all()
        expected_datetime = datetime(
            year=2015, month=5, day=12, hour=21, minute=53, second=10, tzinfo=UTC)
        self.assertEqual(meetups[0].updated, expected_datetime)
        mock_get_content.return_value = self._second_result()
        MeetupUpdate._invalidate_meetup_update()  # Allow a another update so soon
        utils.update()
        meetups = Meetup.objects.all()
        self.assertEqual(len(meetups), 1)

        expected_datetime = datetime(
            year=2015, month=5, day=12, hour=21, minute=53, second=20, tzinfo=UTC)
        self.assertEqual(meetups[0].updated, expected_datetime)
        self.assertEqual(meetups[0].name, "New name")

    @patch('meetups.utils.get_content')
    def test_update_second_run_too_soon(self, mock_get_content):
        mock_get_content.return_value = self._first_result()
        utils.update()
        mock_get_content.return_value = self._second_result()
        utils.update()  # Won't update
        meetups = Meetup.objects.all()
        self.assertEqual(len(meetups), 1)

        expected_datetime = datetime(
            year=2015, month=5, day=12, hour=21, minute=53, second=10, tzinfo=UTC)
        self.assertEqual(meetups[0].updated, expected_datetime)
        self.assertEqual(meetups[0].name, "Python Ireland meetup")

    @patch('meetups.utils.get_content')
    def test_update_second_run_no_update(self, mock_get_content):
        mock_get_content.return_value = self._first_result()
        utils.update()
        mock_get_content.return_value = self._first_result()
        utils.update()
        meetups = Meetup.objects.all()
        self.assertEqual(len(meetups), 1)

    @patch('meetups.utils.get_content')
    def test_update_second_run_add_one(self, mock_get_content):
        mock_get_content.return_value = self._first_result()
        utils.update()
        MeetupUpdate._invalidate_meetup_update()  # Allow a another update so soon
        mock_get_content.return_value = self._second_result()
        utils.update()
        MeetupUpdate._invalidate_meetup_update()  # Allow a another update so soon
        mock_get_content.return_value = self._third_result()
        utils.update()
        meetup_one = Meetup.objects.get(id='qwfbshytjbnb')
        meetup_two = Meetup.objects.get(id='qwfbshytjbnc')
        self.assertEqual(meetup_one.name, 'New name')
        self.assertEqual(meetup_two.name, 'New entry')
