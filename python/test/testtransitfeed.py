#!/usr/bin/python2.5

# Copyright (C) 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Unit tests for the transitfeed module.

import datetime
from datetime import date
import dircache
import os.path
import re
import sys
import tempfile
import time
import transitfeed
import types
import unittest
import util
from util import RecordingProblemAccumulator
from StringIO import StringIO
import zipfile
import zlib


def DataPath(path):
  here = os.path.dirname(__file__)
  return os.path.join(here, 'data', path)

def GetDataPathContents():
  here = os.path.dirname(__file__)
  return dircache.listdir(os.path.join(here, 'data'))


class ExceptionProblemReporterNoExpiration(transitfeed.ProblemReporter):
  """Ignores feed expiration problems.

  Use TestFailureProblemReporter in new code because it fails more cleanly, is
  easier to extend and does more thorough checking.
  """

  def __init__(self):
    accumulator = transitfeed.ExceptionProblemAccumulator(raise_warnings=True)
    transitfeed.ProblemReporter.__init__(self, accumulator)

  def ExpirationDate(self, expiration, context=None):
    pass  # We don't want to give errors about our test data


def GetTestFailureProblemReporter(test_case,
                                  ignore_types=("ExpirationDate",)):
  accumulator = TestFailureProblemAccumulator(test_case, ignore_types)
  problems = transitfeed.ProblemReporter(accumulator)
  return problems


class TestFailureProblemAccumulator(transitfeed.ProblemAccumulatorInterface):
  """Causes a test failure immediately on any problem."""
  def __init__(self, test_case, ignore_types=("ExpirationDate",)):
    self.test_case = test_case
    self._ignore_types = ignore_types or set()

  def _Report(self, e):
    # These should never crash
    formatted_problem = e.FormatProblem()
    formatted_context = e.FormatContext()
    exception_class = e.__class__.__name__
    if exception_class in self._ignore_types:
      return
    self.test_case.fail(
        "%s: %s\n%s" % (exception_class, formatted_problem, formatted_context))


class UnrecognizedColumnRecorder(transitfeed.ProblemReporter):
  """Keeps track of unrecognized column errors."""
  def __init__(self, test_case):
    self.accumulator = RecordingProblemAccumulator(test_case,
        ignore_types=("ExpirationDate",))
    self.column_errors = []

  def UnrecognizedColumn(self, file_name, column_name, context=None):
    self.column_errors.append((file_name, column_name))


class RedirectStdOutTestCaseBase(util.TestCase):
  """Save stdout to the StringIO buffer self.this_stdout"""
  def setUp(self):
    self.saved_stdout = sys.stdout
    self.this_stdout = StringIO()
    sys.stdout = self.this_stdout

  def tearDown(self):
    sys.stdout = self.saved_stdout
    self.this_stdout.close()


# ensure that there are no exceptions when attempting to load
# (so that the validator won't crash)
class NoExceptionTestCase(RedirectStdOutTestCaseBase):
  def runTest(self):
    for feed in GetDataPathContents():
      loader = transitfeed.Loader(DataPath(feed),
                                  problems=transitfeed.ProblemReporter(),
                                  extra_validation=True)
      schedule = loader.Load()
      schedule.Validate()


class EndOfLineCheckerTestCase(util.TestCase):
  def setUp(self):
    self.accumulator = RecordingProblemAccumulator(self, ("ExpirationDate",))
    self.problems = transitfeed.ProblemReporter(self.accumulator)

  def RunEndOfLineChecker(self, end_of_line_checker):
    # Iterating using for calls end_of_line_checker.next() until a
    # StopIteration is raised. EndOfLineChecker does the final check for a mix
    # of CR LF and LF ends just before raising StopIteration.
    for line in end_of_line_checker:
      pass

  def testInvalidLineEnd(self):
    f = transitfeed.EndOfLineChecker(StringIO("line1\r\r\nline2"),
                                     "<StringIO>",
                                     self.problems)
    self.RunEndOfLineChecker(f)
    e = self.accumulator.PopException("InvalidLineEnd")
    self.assertEqual(e.file_name, "<StringIO>")
    self.assertEqual(e.row_num, 1)
    self.assertEqual(e.bad_line_end, r"\r\r\n")
    self.accumulator.AssertNoMoreExceptions()

  def testInvalidLineEndToo(self):
    f = transitfeed.EndOfLineChecker(
        StringIO("line1\nline2\r\nline3\r\r\r\n"),
        "<StringIO>", self.problems)
    self.RunEndOfLineChecker(f)
    e = self.accumulator.PopException("InvalidLineEnd")
    self.assertEqual(e.file_name, "<StringIO>")
    self.assertEqual(e.row_num, 3)
    self.assertEqual(e.bad_line_end, r"\r\r\r\n")
    e = self.accumulator.PopException("OtherProblem")
    self.assertEqual(e.file_name, "<StringIO>")
    self.assertTrue(e.description.find("consistent line end") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testEmbeddedCr(self):
    f = transitfeed.EndOfLineChecker(
        StringIO("line1\rline1b"),
        "<StringIO>", self.problems)
    self.RunEndOfLineChecker(f)
    e = self.accumulator.PopException("OtherProblem")
    self.assertEqual(e.file_name, "<StringIO>")
    self.assertEqual(e.row_num, 1)
    self.assertEqual(e.FormatProblem(),
                     "Line contains ASCII Carriage Return 0x0D, \\r")
    self.accumulator.AssertNoMoreExceptions()

  def testEmbeddedUtf8NextLine(self):
    f = transitfeed.EndOfLineChecker(
        StringIO("line1b\xc2\x85"),
        "<StringIO>", self.problems)
    self.RunEndOfLineChecker(f)
    e = self.accumulator.PopException("OtherProblem")
    self.assertEqual(e.file_name, "<StringIO>")
    self.assertEqual(e.row_num, 1)
    self.assertEqual(e.FormatProblem(),
                     "Line contains Unicode NEXT LINE SEPARATOR U+0085")
    self.accumulator.AssertNoMoreExceptions()

  def testEndOfLineMix(self):
    f = transitfeed.EndOfLineChecker(
        StringIO("line1\nline2\r\nline3\nline4"),
        "<StringIO>", self.problems)
    self.RunEndOfLineChecker(f)
    e = self.accumulator.PopException("OtherProblem")
    self.assertEqual(e.file_name, "<StringIO>")
    self.assertEqual(e.FormatProblem(),
                     "Found 1 CR LF \"\\r\\n\" line end (line 2) and "
                     "2 LF \"\\n\" line ends (lines 1, 3). A file must use a "
                     "consistent line end.")
    self.accumulator.AssertNoMoreExceptions()

  def testEndOfLineManyMix(self):
    f = transitfeed.EndOfLineChecker(
        StringIO("1\n2\n3\n4\n5\n6\n7\r\n8\r\n9\r\n10\r\n11\r\n"),
        "<StringIO>", self.problems)
    self.RunEndOfLineChecker(f)
    e = self.accumulator.PopException("OtherProblem")
    self.assertEqual(e.file_name, "<StringIO>")
    self.assertEqual(e.FormatProblem(),
                     "Found 5 CR LF \"\\r\\n\" line ends (lines 7, 8, 9, 10, "
                     "11) and 6 LF \"\\n\" line ends (lines 1, 2, 3, 4, 5, "
                     "...). A file must use a consistent line end.")
    self.accumulator.AssertNoMoreExceptions()

  def testLoad(self):
    loader = transitfeed.Loader(
      DataPath("bad_eol.zip"), problems=self.problems, extra_validation=True)
    loader.Load()

    e = self.accumulator.PopException("OtherProblem")
    self.assertEqual(e.file_name, "calendar.txt")
    self.assertTrue(re.search(
      r"Found 1 CR LF.* \(line 2\) and 2 LF .*\(lines 1, 3\)",
      e.FormatProblem()))

    e = self.accumulator.PopException("InvalidLineEnd")
    self.assertEqual(e.file_name, "routes.txt")
    self.assertEqual(e.row_num, 5)
    self.assertTrue(e.FormatProblem().find(r"\r\r\n") != -1)

    e = self.accumulator.PopException("OtherProblem")
    self.assertEqual(e.file_name, "trips.txt")
    self.assertEqual(e.row_num, 1)
    self.assertTrue(re.search(
      r"contains ASCII Form Feed",
      e.FormatProblem()))
    # TODO(Tom): avoid this duplicate error for the same issue
    e = self.accumulator.PopException("CsvSyntax")
    self.assertEqual(e.row_num, 1)
    self.assertTrue(re.search(
      r"header row should not contain any space char",
      e.FormatProblem()))

    self.accumulator.AssertNoMoreExceptions()


class LoadTestCase(util.TestCase):
  def setUp(self):
    self.accumulator = RecordingProblemAccumulator(self, ("ExpirationDate",))
    self.problems = transitfeed.ProblemReporter(self.accumulator)

  def Load(self, feed_name):
    loader = transitfeed.Loader(
      DataPath(feed_name), problems=self.problems, extra_validation=True)
    loader.Load()

  def ExpectInvalidValue(self, feed_name, column_name):
    self.Load(feed_name)
    self.accumulator.PopInvalidValue(column_name)
    self.accumulator.AssertNoMoreExceptions()

  def ExpectMissingFile(self, feed_name, file_name):
    self.Load(feed_name)
    e = self.accumulator.PopException("MissingFile")
    self.assertEqual(file_name, e.file_name)
    # Don't call AssertNoMoreExceptions() because a missing file causes
    # many errors.


class LoadFromZipTestCase(util.TestCase):
  def runTest(self):
    loader = transitfeed.Loader(
      DataPath('good_feed.zip'),
      problems=GetTestFailureProblemReporter(self),
      extra_validation=True)
    loader.Load()

    # now try using Schedule.Load
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    schedule.Load(DataPath('good_feed.zip'), extra_validation=True)


class LoadAndRewriteFromZipTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    schedule.Load(DataPath('good_feed.zip'), extra_validation=True)

    # Finally see if write crashes
    schedule.WriteGoogleTransitFeed(tempfile.TemporaryFile())


class LoadFromDirectoryTestCase(util.TestCase):
  def runTest(self):
    loader = transitfeed.Loader(
      DataPath('good_feed'),
      problems=GetTestFailureProblemReporter(self),
      extra_validation=True)
    loader.Load()


class LoadUnknownFeedTestCase(util.TestCase):
  def runTest(self):
    feed_name = DataPath('unknown_feed')
    loader = transitfeed.Loader(
      feed_name,
      problems=ExceptionProblemReporterNoExpiration(),
      extra_validation=True)
    try:
      loader.Load()
      self.fail('FeedNotFound exception expected')
    except transitfeed.FeedNotFound, e:
      self.assertEqual(feed_name, e.feed_name)

class LoadUnknownFormatTestCase(util.TestCase):
  def runTest(self):
    feed_name = DataPath('unknown_format.zip')
    loader = transitfeed.Loader(
      feed_name,
      problems=ExceptionProblemReporterNoExpiration(),
      extra_validation=True)
    try:
      loader.Load()
      self.fail('UnknownFormat exception expected')
    except transitfeed.UnknownFormat, e:
      self.assertEqual(feed_name, e.feed_name)

class LoadUnrecognizedColumnsTestCase(util.TestCase):
  def runTest(self):
    problems = UnrecognizedColumnRecorder(self)
    loader = transitfeed.Loader(DataPath('unrecognized_columns'),
                                problems=problems)
    loader.Load()
    found_errors = set(problems.column_errors)
    expected_errors = set([
      ('agency.txt', 'agency_lange'),
      ('stops.txt', 'stop_uri'),
      ('routes.txt', 'Route_Text_Color'),
      ('calendar.txt', 'leap_day'),
      ('calendar_dates.txt', 'leap_day'),
      ('trips.txt', 'sharpe_id'),
      ('stop_times.txt', 'shapedisttraveled'),
      ('stop_times.txt', 'drop_off_time'),
      ('fare_attributes.txt', 'transfer_time'),
      ('fare_rules.txt', 'source_id'),
      ('frequencies.txt', 'superfluous'),
      ('transfers.txt', 'to_stop')
    ])

    # Now make sure we got the unrecognized column errors that we expected.
    not_expected = found_errors.difference(expected_errors)
    self.failIf(not_expected, 'unexpected errors: %s' % str(not_expected))
    not_found = expected_errors.difference(found_errors)
    self.failIf(not_found, 'expected but not found: %s' % str(not_found))

class LoadExtraCellValidationTestCase(LoadTestCase):
  """Check that the validation detects too many cells in a row."""
  def runTest(self):
    self.Load('extra_row_cells')
    e = self.accumulator.PopException("OtherProblem")
    self.assertEquals("routes.txt", e.file_name)
    self.assertEquals(4, e.row_num)
    self.accumulator.AssertNoMoreExceptions()


class LoadMissingCellValidationTestCase(LoadTestCase):
  """Check that the validation detects missing cells in a row."""
  def runTest(self):
    self.Load('missing_row_cells')
    e = self.accumulator.PopException("OtherProblem")
    self.assertEquals("routes.txt", e.file_name)
    self.assertEquals(4, e.row_num)
    self.accumulator.AssertNoMoreExceptions()

class LoadUnknownFileTestCase(util.TestCase):
  """Check that the validation detects unknown files."""
  def runTest(self):
    feed_name = DataPath('unknown_file')
    self.accumulator = RecordingProblemAccumulator(self, ("ExpirationDate",))
    self.problems = transitfeed.ProblemReporter(self.accumulator)
    loader = transitfeed.Loader(
      feed_name,
      problems=self.problems,
      extra_validation=True)
    loader.Load()
    e = self.accumulator.PopException('UnknownFile')
    self.assertEqual('frecuencias.txt', e.file_name)
    self.accumulator.AssertNoMoreExceptions()

class LoadUTF8BOMTestCase(util.TestCase):
  def runTest(self):
    loader = transitfeed.Loader(
      DataPath('utf8bom'),
      problems=GetTestFailureProblemReporter(self),
      extra_validation=True)
    loader.Load()


class LoadUTF16TestCase(util.TestCase):
  def runTest(self):
    # utf16 generated by `recode utf8..utf16 *'
    accumulator = transitfeed.ExceptionProblemAccumulator()
    problem_reporter = transitfeed.ProblemReporter(accumulator)
    loader = transitfeed.Loader(
      DataPath('utf16'),
      problems=problem_reporter,
      extra_validation=True)
    try:
      loader.Load()
      # TODO: make sure processing proceeds beyond the problem
      self.fail('FileFormat exception expected')
    except transitfeed.FileFormat, e:
      # make sure these don't raise an exception
      self.assertTrue(re.search(r'encoded in utf-16', e.FormatProblem()))
      e.FormatContext()


class LoadNullTestCase(util.TestCase):
  def runTest(self):
    accumulator = transitfeed.ExceptionProblemAccumulator()
    problem_reporter = transitfeed.ProblemReporter(accumulator)
    loader = transitfeed.Loader(
      DataPath('contains_null'),
      problems=problem_reporter,
      extra_validation=True)
    try:
      loader.Load()
      self.fail('FileFormat exception expected')
    except transitfeed.FileFormat, e:
      self.assertTrue(re.search(r'contains a null', e.FormatProblem()))
      # make sure these don't raise an exception
      e.FormatContext()


class ProblemReporterTestCase(RedirectStdOutTestCaseBase):
  # Unittest for problem reporter
  def testContextWithBadUnicodeProblem(self):
    pr = transitfeed.ProblemReporter()
    # Context has valid unicode values
    pr.SetFileContext('filename.foo', 23,
                      [u'Andr\202', u'Person \uc720 foo', None],
                      [u'1\202', u'2\202', u'3\202'])
    pr.OtherProblem('test string')
    pr.OtherProblem(u'\xff\xfe\x80\x88')
    # Invalid ascii and utf-8. encode('utf-8') and decode('utf-8') will fail
    # for this value
    pr.OtherProblem('\xff\xfe\x80\x88')
    self.assertTrue(re.search(r"test string", self.this_stdout.getvalue()))
    self.assertTrue(re.search(r"filename.foo:23", self.this_stdout.getvalue()))

  def testNoContextWithBadUnicode(self):
    pr = transitfeed.ProblemReporter()
    pr.OtherProblem('test string')
    pr.OtherProblem(u'\xff\xfe\x80\x88')
    # Invalid ascii and utf-8. encode('utf-8') and decode('utf-8') will fail
    # for this value
    pr.OtherProblem('\xff\xfe\x80\x88')
    self.assertTrue(re.search(r"test string", self.this_stdout.getvalue()))

  def testBadUnicodeContext(self):
    pr = transitfeed.ProblemReporter()
    pr.SetFileContext('filename.foo', 23,
                      [u'Andr\202', 'Person \xff\xfe\x80\x88 foo', None],
                      [u'1\202', u'2\202', u'3\202'])
    pr.OtherProblem("help, my context isn't utf-8!")
    self.assertTrue(re.search(r"help, my context", self.this_stdout.getvalue()))
    self.assertTrue(re.search(r"filename.foo:23", self.this_stdout.getvalue()))

  def testLongWord(self):
    # Make sure LineWrap doesn't puke
    pr = transitfeed.ProblemReporter()
    pr.OtherProblem('1111untheontuhoenuthoentuhntoehuontehuntoehuntoehunto'
                    '2222oheuntheounthoeunthoeunthoeuntheontuheontuhoue')
    self.assertTrue(re.search(r"1111.+2222", self.this_stdout.getvalue()))


class BadProblemReporterTestCase(RedirectStdOutTestCaseBase):
  """Make sure ProblemReporter doesn't crash when given bad unicode data and
  does find some error"""
  # tom.brown.code-utf8_weaknesses fixed a bug with problem reporter and bad
  # utf-8 strings
  def runTest(self):
    loader = transitfeed.Loader(
      DataPath('bad_utf8'),
      problems=transitfeed.ProblemReporter(),
      extra_validation=True)
    loader.Load()
    # raises exception if not found
    self.this_stdout.getvalue().index('Invalid value')


class BadUtf8TestCase(LoadTestCase):
  def runTest(self):
    self.Load('bad_utf8')
    self.accumulator.PopException("UnrecognizedColumn")
    self.accumulator.PopInvalidValue("agency_name", "agency.txt")
    self.accumulator.PopInvalidValue("stop_name", "stops.txt")
    self.accumulator.PopInvalidValue("route_short_name", "routes.txt")
    self.accumulator.PopInvalidValue("route_long_name", "routes.txt")
    self.accumulator.PopInvalidValue("trip_headsign", "trips.txt")
    self.accumulator.PopInvalidValue("stop_headsign", "stop_times.txt")
    self.accumulator.AssertNoMoreExceptions()


class LoadMissingAgencyTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectMissingFile('missing_agency', 'agency.txt')


class LoadMissingStopsTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectMissingFile('missing_stops', 'stops.txt')


class LoadMissingRoutesTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectMissingFile('missing_routes', 'routes.txt')


class LoadMissingTripsTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectMissingFile('missing_trips', 'trips.txt')


class LoadMissingStopTimesTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectMissingFile('missing_stop_times', 'stop_times.txt')


class LoadMissingCalendarTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectMissingFile('missing_calendar', 'calendar.txt')


class EmptyFileTestCase(util.TestCase):
  def runTest(self):
    loader = transitfeed.Loader(
      DataPath('empty_file'),
      problems=ExceptionProblemReporterNoExpiration(),
      extra_validation = True)
    try:
      loader.Load()
      self.fail('EmptyFile exception expected')
    except transitfeed.EmptyFile, e:
      self.assertEqual('agency.txt', e.file_name)


class MissingColumnTestCase(util.TestCase):
  def runTest(self):
    loader = transitfeed.Loader(
      DataPath('missing_column'),
      problems=ExceptionProblemReporterNoExpiration(),
      extra_validation = True)
    try:
      loader.Load()
      self.fail('MissingColumn exception expected')
    except transitfeed.MissingColumn, e:
      self.assertEqual('agency.txt', e.file_name)
      self.assertEqual('agency_name', e.column_name)


class ZeroBasedStopSequenceTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectInvalidValue('negative_stop_sequence', 'stop_sequence')


class DuplicateStopTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    try:
      schedule.Load(DataPath('duplicate_stop'), extra_validation=True)
      self.fail('OtherProblem exception expected')
    except transitfeed.OtherProblem:
      pass

class DuplicateStopSequenceTestCase(util.TestCase):
  def runTest(self):
    accumulator = RecordingProblemAccumulator(self, ("ExpirationDate",
                                                     "NoServiceExceptions"))
    problems = transitfeed.ProblemReporter(accumulator)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    schedule.Load(DataPath('duplicate_stop_sequence'), extra_validation=True)
    e = accumulator.PopException('InvalidValue')
    self.assertEqual('stop_sequence', e.column_name)
    self.assertEqual(10, e.value)
    accumulator.AssertNoMoreExceptions()


class MissingEndpointTimesTestCase(util.TestCase):
  def runTest(self):
    problems = ExceptionProblemReporterNoExpiration()
    schedule = transitfeed.Schedule(problem_reporter=problems)
    try:
      schedule.Load(DataPath('missing_endpoint_times'), extra_validation=True)
      self.fail('InvalidValue exception expected')
    except transitfeed.InvalidValue, e:
      self.assertEqual('departure_time', e.column_name)
      self.assertEqual('', e.value)


class DuplicateScheduleIDTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    try:
      schedule.Load(DataPath('duplicate_schedule_id'), extra_validation=True)
      self.fail('DuplicateID exception expected')
    except transitfeed.DuplicateID:
      pass

class OverlappingBlockSchedule(transitfeed.Schedule):
  """Special Schedule subclass that counts the number of calls to
  GetServicePeriod() so we can verify service period overlap calculation
  caching"""

  _get_service_period_call_count = 0

  def GetServicePeriod(self, service_id):
    self._get_service_period_call_count += 1
    return transitfeed.Schedule.GetServicePeriod(self, service_id)

  def GetServicePeriodCallCount(self):
    return self._get_service_period_call_count

class OverlappingBlockTripsTestCase(util.TestCase):
  """Builds a simple schedule for testing of overlapping block trips"""

  def setUp(self):
    self.accumulator = RecordingProblemAccumulator(
        self, ("ExpirationDate", "NoServiceExceptions"))
    self.problems = transitfeed.ProblemReporter(self.accumulator)

    schedule = OverlappingBlockSchedule(problem_reporter=self.problems)
    schedule.AddAgency("Demo Transit Authority", "http://dta.org",
                       "America/Los_Angeles")

    sp1 = transitfeed.ServicePeriod("SID1")
    sp1.SetWeekdayService(True)
    sp1.SetStartDate("20070605")
    sp1.SetEndDate("20080605")
    schedule.AddServicePeriodObject(sp1)

    sp2 = transitfeed.ServicePeriod("SID2")
    sp2.SetDayOfWeekHasService(0)
    sp2.SetDayOfWeekHasService(2)
    sp2.SetDayOfWeekHasService(4)
    sp2.SetStartDate("20070605")
    sp2.SetEndDate("20080605")
    schedule.AddServicePeriodObject(sp2)

    sp3 = transitfeed.ServicePeriod("SID3")
    sp3.SetWeekendService(True)
    sp3.SetStartDate("20070605")
    sp3.SetEndDate("20080605")
    schedule.AddServicePeriodObject(sp3)

    self.stop1 = schedule.AddStop(lng=-116.75167,
                                  lat=36.915682,
                                  name="Stagecoach Hotel & Casino",
                                  stop_id="S1")

    self.stop2 = schedule.AddStop(lng=-116.76218,
                                  lat=36.905697,
                                  name="E Main St / S Irving St",
                                  stop_id="S2")

    self.route = schedule.AddRoute("", "City", "Bus", route_id="CITY")

    self.schedule = schedule
    self.sp1 = sp1
    self.sp2 = sp2
    self.sp3 = sp3

  def testNoOverlap(self):

    schedule, route, sp1 = self.schedule, self.route, self.sp1

    trip1 = route.AddTrip(schedule, service_period=sp1, trip_id="CITY1")
    trip1.block_id = "BLOCK"
    trip1.AddStopTime(self.stop1, stop_time="6:00:00")
    trip1.AddStopTime(self.stop2, stop_time="6:30:00")

    trip2 = route.AddTrip(schedule, service_period=sp1, trip_id="CITY2")
    trip2.block_id = "BLOCK"
    trip2.AddStopTime(self.stop2, stop_time="6:30:00")
    trip2.AddStopTime(self.stop1, stop_time="7:00:00")

    schedule.Validate(self.problems)

    self.accumulator.AssertNoMoreExceptions()

  def testOverlapSameServicePeriod(self):

    schedule, route, sp1 = self.schedule, self.route, self.sp1

    trip1 = route.AddTrip(schedule, service_period=sp1, trip_id="CITY1")
    trip1.block_id = "BLOCK"
    trip1.AddStopTime(self.stop1, stop_time="6:00:00")
    trip1.AddStopTime(self.stop2, stop_time="6:30:00")

    trip2 = route.AddTrip(schedule, service_period=sp1, trip_id="CITY2")
    trip2.block_id = "BLOCK"
    trip2.AddStopTime(self.stop2, stop_time="6:20:00")
    trip2.AddStopTime(self.stop1, stop_time="6:50:00")

    schedule.Validate(self.problems)

    e = self.accumulator.PopException('OverlappingTripsInSameBlock')
    self.assertEqual(e.trip_id1, 'CITY1')
    self.assertEqual(e.trip_id2, 'CITY2')
    self.assertEqual(e.block_id, 'BLOCK')

    self.accumulator.AssertNoMoreExceptions()

  def testOverlapDifferentServicePeriods(self):

    schedule, route, sp1, sp2 = self.schedule, self.route, self.sp1, self.sp2

    trip1 = route.AddTrip(schedule, service_period=sp1, trip_id="CITY1")
    trip1.block_id = "BLOCK"
    trip1.AddStopTime(self.stop1, stop_time="6:00:00")
    trip1.AddStopTime(self.stop2, stop_time="6:30:00")

    trip2 = route.AddTrip(schedule, service_period=sp2, trip_id="CITY2")
    trip2.block_id = "BLOCK"
    trip2.AddStopTime(self.stop2, stop_time="6:20:00")
    trip2.AddStopTime(self.stop1, stop_time="6:50:00")

    trip3 = route.AddTrip(schedule, service_period=sp1, trip_id="CITY3")
    trip3.block_id = "BLOCK"
    trip3.AddStopTime(self.stop1, stop_time="7:00:00")
    trip3.AddStopTime(self.stop2, stop_time="7:30:00")

    trip4 = route.AddTrip(schedule, service_period=sp2, trip_id="CITY4")
    trip4.block_id = "BLOCK"
    trip4.AddStopTime(self.stop2, stop_time="7:20:00")
    trip4.AddStopTime(self.stop1, stop_time="7:50:00")

    schedule.Validate(self.problems)

    e = self.accumulator.PopException('OverlappingTripsInSameBlock')
    self.assertEqual(e.trip_id1, 'CITY1')
    self.assertEqual(e.trip_id2, 'CITY2')
    self.assertEqual(e.block_id, 'BLOCK')

    e = self.accumulator.PopException('OverlappingTripsInSameBlock')
    self.assertEqual(e.trip_id1, 'CITY3')
    self.assertEqual(e.trip_id2, 'CITY4')
    self.assertEqual(e.block_id, 'BLOCK')

    self.accumulator.AssertNoMoreExceptions()

    # If service period overlap calculation caching is working correctly,
    # we expect only two calls to GetServicePeriod(), one each for sp1 and
    # sp2, as oppossed four calls total for the four overlapping trips
    self.assertEquals(2, schedule.GetServicePeriodCallCount())

  def testNoOverlapDifferentServicePeriods(self):

    schedule, route, sp1, sp3 = self.schedule, self.route, self.sp1, self.sp3

    trip1 = route.AddTrip(schedule, service_period=sp1, trip_id="CITY1")
    trip1.block_id = "BLOCK"
    trip1.AddStopTime(self.stop1, stop_time="6:00:00")
    trip1.AddStopTime(self.stop2, stop_time="6:30:00")

    trip2 = route.AddTrip(schedule, service_period=sp3, trip_id="CITY2")
    trip2.block_id = "BLOCK"
    trip2.AddStopTime(self.stop2, stop_time="6:20:00")
    trip2.AddStopTime(self.stop1, stop_time="6:50:00")

    schedule.Validate(self.problems)

    self.accumulator.AssertNoMoreExceptions()

class ColorLuminanceTestCase(util.TestCase):
  def runTest(self):
    self.assertEqual(transitfeed.ColorLuminance('000000'), 0,
        "ColorLuminance('000000') should be zero")
    self.assertEqual(transitfeed.ColorLuminance('FFFFFF'), 255,
        "ColorLuminance('FFFFFF') should be 255")
    RGBmsg = ("ColorLuminance('RRGGBB') should be "
              "0.299*<Red> + 0.587*<Green> + 0.114*<Blue>")
    decimal_places_tested = 8
    self.assertAlmostEqual(transitfeed.ColorLuminance('640000'), 29.9,
                           decimal_places_tested, RGBmsg)
    self.assertAlmostEqual(transitfeed.ColorLuminance('006400'), 58.7,
                     decimal_places_tested, RGBmsg)
    self.assertAlmostEqual(transitfeed.ColorLuminance('000064'), 11.4,
                     decimal_places_tested, RGBmsg)
    self.assertAlmostEqual(transitfeed.ColorLuminance('1171B3'),
                     0.299*17 + 0.587*113 + 0.114*179,
                     decimal_places_tested, RGBmsg)

INVALID_VALUE = Exception()
class ValidationTestCase(util.TestCase):
  def setUp(self):
    self.accumulator = RecordingProblemAccumulator(
        self, ("ExpirationDate", "NoServiceExceptions"))
    self.problems = transitfeed.ProblemReporter(self.accumulator)

  def tearDown(self):
    self.accumulator.TearDownAssertNoMoreExceptions()

  def ExpectNoProblems(self, object):
    self.accumulator.AssertNoMoreExceptions()
    object.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  # TODO: think about Expect*Closure methods. With the
  # RecordingProblemAccumulator it is now possible to replace
  # self.ExpectMissingValueInClosure(lambda: o.method(...), foo)
  # with
  # o.method(...)
  # self.ExpectMissingValueInClosure(foo)
  # because problems don't raise an exception. This has the advantage of
  # making it easy and clear to test the return value of o.method(...) and
  # easier to test for a sequence of problems caused by one call.
  # neun@ 2011-01-18: for the moment I don't remove the Expect*InClosure methods
  # as they allow enforcing an AssertNoMoreExceptions() before validation.
  # When removing them we do have to make sure that each "logical test block"
  # before an Expect*InClosure usage really ends with AssertNoMoreExceptions.
  # See http://codereview.appspot.com/4020041/
  def ValidateAndExpectMissingValue(self, object, column_name):
    self.accumulator.AssertNoMoreExceptions()
    object.Validate(self.problems)
    self.ExpectException('MissingValue', column_name)

  def ExpectMissingValueInClosure(self, column_name, c):
    self.accumulator.AssertNoMoreExceptions()
    rv = c()
    self.ExpectException('MissingValue', column_name)

  def ValidateAndExpectInvalidValue(self, object, column_name,
                                    value=INVALID_VALUE):
    self.accumulator.AssertNoMoreExceptions()
    object.Validate(self.problems)
    self.ExpectException('InvalidValue', column_name, value)

  def ExpectInvalidValueInClosure(self, column_name, value=INVALID_VALUE,
                                  c=None):
    self.accumulator.AssertNoMoreExceptions()
    rv = c()
    self.ExpectException('InvalidValue', column_name, value)

  def ValidateAndExpectInvalidFloatValue(self, object, value):
    self.accumulator.AssertNoMoreExceptions()
    object.Validate(self.problems)
    self.ExpectException('InvalidFloatValue', None, value)

  def ValidateAndExpectOtherProblem(self, object):
    self.accumulator.AssertNoMoreExceptions()
    object.Validate(self.problems)
    self.ExpectException('OtherProblem')

  def ExpectOtherProblemInClosure(self, c):
    self.accumulator.AssertNoMoreExceptions()
    rv = c()
    self.ExpectException('OtherProblem')

  def ValidateAndExpectDateOutsideValidRange(self, object, column_name,
                                             value=INVALID_VALUE):
    self.accumulator.AssertNoMoreExceptions()
    object.Validate(self.problems)
    self.ExpectException('DateOutsideValidRange', column_name, value)

  def ExpectException(self, type_name, column_name=None, value=INVALID_VALUE):
    e = self.accumulator.PopException(type_name)
    if column_name:
      self.assertEqual(column_name, e.column_name)
    if value != INVALID_VALUE:
      self.assertEqual(value, e.value)
    # these should not throw any exceptions
    e.FormatProblem()
    e.FormatContext()
    self.accumulator.AssertNoMoreExceptions()

  def SimpleSchedule(self):
    """Return a minimum schedule that will load without warnings."""
    schedule = transitfeed.Schedule(problem_reporter=self.problems)
    schedule.AddAgency("Fly Agency", "http://iflyagency.com",
                       "America/Los_Angeles")
    service_period = transitfeed.ServicePeriod("WEEK")
    service_period.SetWeekdayService(True)
    service_period.SetStartDate("20091203")
    service_period.SetEndDate("20111203")
    service_period.SetDateHasService("20091203")
    schedule.AddServicePeriodObject(service_period)
    stop1 = schedule.AddStop(lng=1.00, lat=48.2, name="Stop 1", stop_id="stop1")
    stop2 = schedule.AddStop(lng=1.01, lat=48.2, name="Stop 2", stop_id="stop2")
    stop3 = schedule.AddStop(lng=1.03, lat=48.2, name="Stop 3", stop_id="stop3")
    route = schedule.AddRoute("54C", "", "Bus", route_id="054C")
    trip = route.AddTrip(schedule, "bus trip", trip_id="CITY1")
    trip.AddStopTime(stop1, stop_time="12:00:00")
    trip.AddStopTime(stop2, stop_time="12:00:45")
    trip.AddStopTime(stop3, stop_time="12:02:30")
    return schedule


class AgencyValidationTestCase(ValidationTestCase):
  def runTest(self):
    # success case
    agency = transitfeed.Agency(name='Test Agency', url='http://example.com',
                                timezone='America/Los_Angeles', id='TA',
                                lang='xh')
    self.ExpectNoProblems(agency)

    # bad agency
    agency = transitfeed.Agency(name='   ', url='http://example.com',
                                timezone='America/Los_Angeles', id='TA')
    self.ValidateAndExpectMissingValue(agency, 'agency_name')

    # missing url
    agency = transitfeed.Agency(name='Test Agency',
                                timezone='America/Los_Angeles', id='TA')
    self.ValidateAndExpectMissingValue(agency, 'agency_url')

    # bad url
    agency = transitfeed.Agency(name='Test Agency', url='www.example.com',
                                timezone='America/Los_Angeles', id='TA')
    self.ValidateAndExpectInvalidValue(agency, 'agency_url')

    # bad time zone
    agency = transitfeed.Agency(name='Test Agency', url='http://example.com',
                                timezone='America/Alviso', id='TA')
    agency.Validate(self.problems)
    e = self.accumulator.PopInvalidValue('agency_timezone')
    self.assertMatchesRegex('"America/Alviso" is not a common timezone',
                            e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

    # bad language code
    agency = transitfeed.Agency(name='Test Agency', url='http://example.com',
                                timezone='America/Los_Angeles', id='TA',
                                lang='English')
    self.ValidateAndExpectInvalidValue(agency, 'agency_lang')

    # bad 2-letter lanugage code
    agency = transitfeed.Agency(name='Test Agency', url='http://example.com',
                                timezone='America/Los_Angeles', id='TA',
                                lang='xx')
    self.ValidateAndExpectInvalidValue(agency, 'agency_lang')

    # capitalized language code is OK
    agency = transitfeed.Agency(name='Test Agency', url='http://example.com',
                                timezone='America/Los_Angeles', id='TA',
                                lang='EN')
    self.ExpectNoProblems(agency)

    # extra attribute in constructor is fine, only checked when loading a file
    agency = transitfeed.Agency(name='Test Agency', url='http://example.com',
                                timezone='America/Los_Angeles',
                                agency_mission='monorail you there')
    self.ExpectNoProblems(agency)

    # extra attribute in assigned later is also fine
    agency = transitfeed.Agency(name='Test Agency', url='http://example.com',
                                timezone='America/Los_Angeles')
    agency.agency_mission = 'monorail you there'
    self.ExpectNoProblems(agency)

     # good agency_fare_url url
    agency = transitfeed.Agency(name='Test Agency',
                                url='http://www.example.com',
                                timezone='America/Los_Angeles',
                                agency_fare_url="http://www.example.com/fares")
    self.ExpectNoProblems(agency)

    # bad agency_fare_url url
    agency = transitfeed.Agency(name='Test Agency',
                                url='http://www.example.com',
                                timezone='America/Los_Angeles',
                                agency_fare_url="www.example.com/fares")
    self.ValidateAndExpectInvalidValue(agency, 'agency_fare_url')

    # Multiple problems
    agency = transitfeed.Agency(name='Test Agency', url='www.example.com',
                                timezone='America/West Coast', id='TA')
    self.assertEquals(False, agency.Validate(self.problems))
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual(e.column_name, 'agency_url')
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual(e.column_name, 'agency_timezone')
    self.accumulator.AssertNoMoreExceptions()



class AgencyAttributesTestCase(ValidationTestCase):
  def testCopy(self):
    agency = transitfeed.Agency(field_dict={'agency_name': 'Test Agency',
                                            'agency_url': 'http://example.com',
                                            'timezone': 'America/Los_Angeles',
                                            'agency_mission': 'get you there'})
    self.assertEquals(agency.agency_mission, 'get you there')
    agency_copy = transitfeed.Agency(field_dict=agency)
    self.assertEquals(agency_copy.agency_mission, 'get you there')
    self.assertEquals(agency_copy['agency_mission'], 'get you there')

  def testEq(self):
    agency1 = transitfeed.Agency("Test Agency", "http://example.com",
                                 "America/Los_Angeles")
    agency2 = transitfeed.Agency("Test Agency", "http://example.com",
                                 "America/Los_Angeles")
    # Unknown columns, such as agency_mission, do affect equality
    self.assertEquals(agency1, agency2)
    agency1.agency_mission = "Get you there"
    self.assertNotEquals(agency1, agency2)
    agency2.agency_mission = "Move you"
    self.assertNotEquals(agency1, agency2)
    agency1.agency_mission = "Move you"
    self.assertEquals(agency1, agency2)
    # Private attributes don't affect equality
    agency1._private_attr = "My private message"
    self.assertEquals(agency1, agency2)
    agency2._private_attr = "Another private thing"
    self.assertEquals(agency1, agency2)

  def testDict(self):
    agency = transitfeed.Agency("Test Agency", "http://example.com",
                                "America/Los_Angeles")
    agency._private_attribute = "blah"
    # Private attributes don't appear when iterating through an agency as a
    # dict but can be directly accessed.
    self.assertEquals("blah", agency._private_attribute)
    self.assertEquals("blah", agency["_private_attribute"])
    self.assertEquals(
        set("agency_name agency_url agency_timezone".split()),
        set(agency.keys()))
    self.assertEquals({"agency_name": "Test Agency",
                       "agency_url": "http://example.com",
                       "agency_timezone": "America/Los_Angeles"},
                      dict(agency.iteritems()))


class DeprecatedAgencyFieldsTestCase(util.MemoryZipTestCase):

  def testDeprectatedFieldNames(self):
    self.SetArchiveContents(
        "agency.txt",
        "agency_id,agency_name,agency_timezone,agency_url,agency_ticket_url\n"
        "DTA,Demo Agency,America/Los_Angeles,http://google.com,"
        "http://google.com/tickets\n")
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("agency_ticket_url", e.column_name)
    self.accumulator.AssertNoMoreExceptions()


class StopValidationTestCase(ValidationTestCase):
  def runTest(self):
    # success case
    stop = transitfeed.Stop()
    stop.stop_id = '45'
    stop.stop_name = 'Couch AT End Table'
    stop.stop_lat = 50.0
    stop.stop_lon = 50.0
    stop.stop_desc = 'Edge of the Couch'
    stop.zone_id = 'A'
    stop.stop_url = 'http://example.com'
    stop.Validate(self.problems)

    # latitude too large
    stop.stop_lat = 100.0
    self.ValidateAndExpectInvalidValue(stop, 'stop_lat')
    stop.stop_lat = 50.0

    # latitude as a string works when it is valid
    # empty strings or whitespaces should get reported as MissingValue
    stop.stop_lat = '50.0'
    stop.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    stop.stop_lat = '10f'
    self.ValidateAndExpectInvalidValue(stop, 'stop_lat')
    stop.stop_lat = 'None'
    self.ValidateAndExpectInvalidValue(stop, 'stop_lat')
    stop.stop_lat = ''
    self.ValidateAndExpectMissingValue(stop, 'stop_lat')
    stop.stop_lat = ' '
    self.ValidateAndExpectMissingValue(stop, 'stop_lat')
    stop.stop_lat = 50.0

    # longitude too large
    stop.stop_lon = 200.0
    self.ValidateAndExpectInvalidValue(stop, 'stop_lon')
    stop.stop_lon = 50.0

    # longitude as a string works when it is valid
    # empty strings or whitespaces should get reported as MissingValue
    stop.stop_lon = '50.0'
    stop.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    stop.stop_lon = '10f'
    self.ValidateAndExpectInvalidValue(stop, 'stop_lon')
    stop.stop_lon = 'None'
    self.ValidateAndExpectInvalidValue(stop, 'stop_lon')
    stop.stop_lon = ''
    self.ValidateAndExpectMissingValue(stop, 'stop_lon')
    stop.stop_lon = ' '
    self.ValidateAndExpectMissingValue(stop, 'stop_lon')
    stop.stop_lon = 50.0

    # lat, lon too close to 0, 0
    stop.stop_lat = 0.0
    stop.stop_lon = 0.0
    self.ValidateAndExpectInvalidValue(stop, 'stop_lat')
    stop.stop_lat = 50.0
    stop.stop_lon = 50.0

    # invalid stop_url
    stop.stop_url = 'www.example.com'
    self.ValidateAndExpectInvalidValue(stop, 'stop_url')
    stop.stop_url = 'http://example.com'

    stop.stop_id = '   '
    self.ValidateAndExpectMissingValue(stop, 'stop_id')
    stop.stop_id = '45'

    stop.stop_name = ''
    self.ValidateAndExpectMissingValue(stop, 'stop_name')
    stop.stop_name = ' '
    self.ValidateAndExpectMissingValue(stop, 'stop_name')
    stop.stop_name = 'Couch AT End Table'

    # description same as name
    stop.stop_desc = 'Couch AT End Table'
    self.ValidateAndExpectInvalidValue(stop, 'stop_desc')
    stop.stop_desc = 'Edge of the Couch'
    self.accumulator.AssertNoMoreExceptions()
    
    stop.stop_timezone = 'This_Timezone/Does_Not_Exist'
    self.ValidateAndExpectInvalidValue(stop, 'stop_timezone')
    stop.stop_timezone = 'America/Los_Angeles'
    stop.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()


class StopAttributes(ValidationTestCase):
  def testWithoutSchedule(self):
    stop = transitfeed.Stop()
    stop.Validate(self.problems)
    for name in "stop_id stop_name stop_lat stop_lon".split():
      e = self.accumulator.PopException('MissingValue')
      self.assertEquals(name, e.column_name)
    self.accumulator.AssertNoMoreExceptions()

    stop = transitfeed.Stop()
    # Test behaviour for unset and unknown attribute
    self.assertEquals(stop['new_column'], '')
    try:
      t = stop.new_column
      self.fail('Expecting AttributeError')
    except AttributeError, e:
      pass  # Expected
    stop.stop_id = 'a'
    stop.stop_name = 'my stop'
    stop.new_column = 'val'
    stop.stop_lat = 5.909
    stop.stop_lon = '40.02'
    self.assertEquals(stop.new_column, 'val')
    self.assertEquals(stop['new_column'], 'val')
    self.assertTrue(isinstance(stop['stop_lat'], basestring))
    self.assertAlmostEqual(float(stop['stop_lat']), 5.909)
    self.assertTrue(isinstance(stop['stop_lon'], basestring))
    self.assertAlmostEqual(float(stop['stop_lon']), 40.02)
    stop.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    # After validation stop.stop_lon has been converted to a float
    self.assertAlmostEqual(stop.stop_lat, 5.909)
    self.assertAlmostEqual(stop.stop_lon, 40.02)
    self.assertEquals(stop.new_column, 'val')
    self.assertEquals(stop['new_column'], 'val')

  def testBlankAttributeName(self):
    stop1 = transitfeed.Stop(field_dict={"": "a"})
    stop2 = transitfeed.Stop(field_dict=stop1)
    self.assertEquals("a", getattr(stop1, ""))
    # The attribute "" is treated as private and not copied
    self.assertRaises(AttributeError, getattr, stop2, "")
    self.assertEquals(set(), set(stop1.keys()))
    self.assertEquals(set(), set(stop2.keys()))

  def testWithSchedule(self):
    schedule = transitfeed.Schedule(problem_reporter=self.problems)

    stop = transitfeed.Stop(field_dict={})
    # AddStopObject silently fails for Stop objects without stop_id
    schedule.AddStopObject(stop)
    self.assertFalse(schedule.GetStopList())
    self.assertFalse(stop._schedule)

    # Okay to add a stop with only stop_id
    stop = transitfeed.Stop(field_dict={"stop_id": "b"})
    schedule.AddStopObject(stop)
    stop.Validate(self.problems)
    for name in "stop_name stop_lat stop_lon".split():
      e = self.accumulator.PopException("MissingValue")
      self.assertEquals(name, e.column_name)
    self.accumulator.AssertNoMoreExceptions()

    stop.new_column = "val"
    self.assertTrue("new_column" in schedule.GetTableColumns("stops"))

    # Adding a duplicate stop_id fails
    schedule.AddStopObject(transitfeed.Stop(field_dict={"stop_id": "b"}))
    self.accumulator.PopException("DuplicateID")
    self.accumulator.AssertNoMoreExceptions()


class StopTimeValidationTestCase(ValidationTestCase):
  def runTest(self):
    stop = transitfeed.Stop()
    self.ExpectInvalidValueInClosure('arrival_time', '1a:00:00',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="1a:00:00"))
    self.ExpectInvalidValueInClosure('departure_time', '1a:00:00',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time='1a:00:00'))
    self.ExpectInvalidValueInClosure('pickup_type', '7.8',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time='10:05:00',
                                     pickup_type='7.8',
                                     drop_off_type='0'))
    self.ExpectInvalidValueInClosure('drop_off_type', 'a',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time='10:05:00',
                                     pickup_type='3',
                                     drop_off_type='a'))
    self.ExpectInvalidValueInClosure('shape_dist_traveled', '$',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time='10:05:00',
                                     pickup_type='3',
                                     drop_off_type='0',
                                     shape_dist_traveled='$'))
    self.ExpectInvalidValueInClosure('shape_dist_traveled', '0,53',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time='10:05:00',
                                     pickup_type='3',
                                     drop_off_type='0',
                                     shape_dist_traveled='0,53'))
    self.ExpectOtherProblemInClosure(
        lambda: transitfeed.StopTime(self.problems, stop,
                                     pickup_type='1', drop_off_type='1'))
    self.ExpectInvalidValueInClosure('departure_time', '10:00:00',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="11:00:00",
                                     departure_time="10:00:00"))
    self.ExpectMissingValueInClosure('arrival_time',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     departure_time="10:00:00"))
    self.ExpectMissingValueInClosure('arrival_time',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     departure_time="10:00:00",
                                     arrival_time=""))
    self.ExpectMissingValueInClosure('departure_time',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00"))
    self.ExpectMissingValueInClosure('departure_time',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time=""))
    self.ExpectInvalidValueInClosure('departure_time', '10:70:00',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time="10:70:00"))
    self.ExpectInvalidValueInClosure('departure_time', '10:00:62',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:00",
                                     departure_time="10:00:62"))
    self.ExpectInvalidValueInClosure('arrival_time', '10:00:63',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:00:63",
                                     departure_time="10:10:00"))
    self.ExpectInvalidValueInClosure('arrival_time', '10:60:00',
        lambda: transitfeed.StopTime(self.problems, stop,
                                     arrival_time="10:60:00",
                                     departure_time="11:02:00"))
    self.ExpectInvalidValueInClosure('stop', "id",
        lambda: transitfeed.StopTime(self.problems, "id",
                                     arrival_time="10:00:00",
                                     departure_time="11:02:00"))
    self.ExpectInvalidValueInClosure('stop', "3",
        lambda: transitfeed.StopTime(self.problems, "3",
                                     arrival_time="10:00:00",
                                     departure_time="11:02:00"))
    self.ExpectInvalidValueInClosure('stop', None,
        lambda: transitfeed.StopTime(self.problems, None,
                                     arrival_time="10:00:00",
                                     departure_time="11:02:00"))

    # The following should work
    transitfeed.StopTime(self.problems, stop, arrival_time="10:00:00",
        departure_time="10:05:00", pickup_type='1', drop_off_type='1')
    transitfeed.StopTime(self.problems, stop, arrival_time="10:00:00",
        departure_time="10:05:00", pickup_type='1', drop_off_type='1')
    transitfeed.StopTime(self.problems, stop, arrival_time="1:00:00",
        departure_time="1:05:00")
    transitfeed.StopTime(self.problems, stop, arrival_time="24:59:00",
        departure_time="25:05:00")
    transitfeed.StopTime(self.problems, stop, arrival_time="101:01:00",
        departure_time="101:21:00")
    transitfeed.StopTime(self.problems, stop)
    self.accumulator.AssertNoMoreExceptions()

class TooFastTravelTestCase(ValidationTestCase):
  def setUp(self):
    super(TooFastTravelTestCase, self).setUp()
    self.schedule = self.SimpleSchedule()
    self.route = self.schedule.GetRoute("054C")
    self.trip = self.route.AddTrip()

  def AddStopDistanceTime(self, dist_time_list):
    # latitude where each 0.01 degrees longitude is 1km
    magic_lat = 26.062468289
    stop = self.schedule.AddStop(magic_lat, 0, "Demo Stop 0")
    time = 0
    self.trip.AddStopTime(stop, arrival_secs=time, departure_secs=time)
    for i, (dist_delta, time_delta) in enumerate(dist_time_list):
      stop = self.schedule.AddStop(
          magic_lat, stop.stop_lon + dist_delta * 0.00001,
          "Demo Stop %d" % (i + 1))
      time += time_delta
      self.trip.AddStopTime(stop, arrival_secs=time, departure_secs=time)

  def testMovingTooFast(self):
    self.AddStopDistanceTime([(1691, 60),
                              (1616, 60)])

    self.trip.Validate(self.problems)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex(r'High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex(r'Stop 0 to Demo Stop 1', e.FormatProblem())
    self.assertMatchesRegex(r'1691 meters in 60 seconds', e.FormatProblem())
    self.assertMatchesRegex(r'\(101 km/h\)', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()

    self.route.route_type = 4  # Ferry with max_speed 80
    self.trip.Validate(self.problems)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex(r'High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex(r'Stop 0 to Demo Stop 1', e.FormatProblem())
    self.assertMatchesRegex(r'1691 meters in 60 seconds', e.FormatProblem())
    self.assertMatchesRegex(r'\(101 km/h\)', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex(r'High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex(r'Stop 1 to Demo Stop 2', e.FormatProblem())
    self.assertMatchesRegex(r'1616 meters in 60 seconds', e.FormatProblem())
    self.assertMatchesRegex(r'97 km/h', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()

    # Run test without a route_type
    self.route.route_type = None
    self.trip.Validate(self.problems)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex(r'High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex(r'Stop 0 to Demo Stop 1', e.FormatProblem())
    self.assertMatchesRegex(r'1691 meters in 60 seconds', e.FormatProblem())
    self.assertMatchesRegex(r'101 km/h', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()

  def testNoTimeDelta(self):
    # See comments where TooFastTravel is called in transitfeed.py to
    # understand why was added.
    # Movement more than max_speed in 1 minute with no time change is a warning.
    self.AddStopDistanceTime([(1616, 0),
                              (1000, 120),
                              (1691, 0)])

    self.trip.Validate(self.problems)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex('High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex('Stop 2 to Demo Stop 3', e.FormatProblem())
    self.assertMatchesRegex('1691 meters in 0 seconds', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()

    self.route.route_type = 4  # Ferry with max_speed 80
    self.trip.Validate(self.problems)
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex('High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex('Stop 0 to Demo Stop 1', e.FormatProblem())
    self.assertMatchesRegex('1616 meters in 0 seconds', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex('High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex('Stop 2 to Demo Stop 3', e.FormatProblem())
    self.assertMatchesRegex('1691 meters in 0 seconds', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()

    # Run test without a route_type
    self.route.route_type = None
    self.trip.Validate(self.problems)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex('High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex('Stop 2 to Demo Stop 3', e.FormatProblem())
    self.assertMatchesRegex('1691 meters in 0 seconds', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()

  def testNoTimeDeltaNotRounded(self):
    # See comments where TooFastTravel is called in transitfeed.py to
    # understand why was added.
    # Any movement with no time change and times not rounded to the nearest
    # minute causes a warning.
    self.AddStopDistanceTime([(500, 62),
                              (10, 0)])

    self.trip.Validate(self.problems)
    e = self.accumulator.PopException('TooFastTravel')
    self.assertMatchesRegex('High speed travel detected', e.FormatProblem())
    self.assertMatchesRegex('Stop 1 to Demo Stop 2', e.FormatProblem())
    self.assertMatchesRegex('10 meters in 0 seconds', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()


class CsvDictTestCase(util.TestCase):
  def setUp(self):
    self.accumulator = RecordingProblemAccumulator(self)
    self.problems = transitfeed.ProblemReporter(self.accumulator)
    self.zip = zipfile.ZipFile(StringIO(), 'a')
    self.loader = transitfeed.Loader(
        problems=self.problems,
        zip=self.zip)

  def tearDown(self):
    self.accumulator.TearDownAssertNoMoreExceptions()

  def testEmptyFile(self):
    self.zip.writestr("test.txt", "")
    results = list(self.loader._ReadCsvDict("test.txt", [], [], []))
    self.assertEquals([], results)
    self.accumulator.PopException("EmptyFile")
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderOnly(self):
    self.zip.writestr("test.txt", "test_id,test_name")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderAndNewLineOnly(self):
    self.zip.writestr("test.txt", "test_id,test_name\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderWithSpaceBefore(self):
    self.zip.writestr("test.txt", " test_id, test_name\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderWithSpaceBeforeAfter(self):
    self.zip.writestr("test.txt", "test_id , test_name\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("CsvSyntax")
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderQuoted(self):
    self.zip.writestr("test.txt", "\"test_id\", \"test_name\"\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderSpaceAfterQuoted(self):
    self.zip.writestr("test.txt", "\"test_id\" , \"test_name\"\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("CsvSyntax")
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderSpaceInQuotesAfterValue(self):
    self.zip.writestr("test.txt", "\"test_id \",\"test_name\"\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("CsvSyntax")
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderSpaceInQuotesBeforeValue(self):
    self.zip.writestr("test.txt", "\"test_id\",\" test_name\"\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("CsvSyntax")
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderEmptyColumnName(self):
    self.zip.writestr("test.txt", 'test_id,test_name,\n')
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("CsvSyntax")
    self.accumulator.AssertNoMoreExceptions()

  def testHeaderAllUnknownColumnNames(self):
    self.zip.writestr("test.txt", 'id,nam\n')
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("CsvSyntax")
    self.assertTrue(e.FormatProblem().find("missing the header") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testFieldWithSpaces(self):
    self.zip.writestr("test.txt",
                      "test_id,test_name\n"
                      "id1 , my name\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([({"test_id": "id1 ", "test_name": "my name"}, 2,
                        ["test_id", "test_name"], ["id1 ", "my name"])],
                        results)
    self.accumulator.AssertNoMoreExceptions()

  def testFieldWithOnlySpaces(self):
    self.zip.writestr("test.txt",
                      "test_id,test_name\n"
                      "id1,  \n")  # spaces are skipped to yield empty field
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([({"test_id": "id1", "test_name": ""}, 2,
                        ["test_id", "test_name"], ["id1", ""])], results)
    self.accumulator.AssertNoMoreExceptions()

  def testQuotedFieldWithSpaces(self):
    self.zip.writestr("test.txt",
                      'test_id,"test_name",test_size\n'
                      '"id1" , "my name" , "234 "\n')
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name",
                                             "test_size"], [], []))
    self.assertEquals(
        [({"test_id": "id1 ", "test_name": "my name ", "test_size": "234 "}, 2,
          ["test_id", "test_name", "test_size"], ["id1 ", "my name ", "234 "])],
        results)
    self.accumulator.AssertNoMoreExceptions()

  def testQuotedFieldWithCommas(self):
    self.zip.writestr("test.txt",
                      'id,name1,name2\n'
                      '"1", "brown, tom", "brown, ""tom"""\n')
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["id", "name1", "name2"], [], []))
    self.assertEquals(
        [({"id": "1", "name1": "brown, tom", "name2": "brown, \"tom\""}, 2,
          ["id", "name1", "name2"], ["1", "brown, tom", "brown, \"tom\""])],
        results)
    self.accumulator.AssertNoMoreExceptions()

  def testUnknownColumn(self):
    # A small typo (omitting '_' in a header name) is detected
    self.zip.writestr("test.txt", "test_id,testname\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("UnrecognizedColumn")
    self.assertEquals("testname", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testDeprecatedColumn(self):
    self.zip.writestr("test.txt", "test_id,test_old\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_new"],
                                            ["test_id"],
                                            [("test_old", "test_new")]))
    self.assertEquals([], results)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("test_old", e.column_name)
    self.assertTrue("test_new" in e.reason)
    self.accumulator.AssertNoMoreExceptions()

  def testDeprecatedColumnWithoutNewColumn(self):
    self.zip.writestr("test.txt", "test_id,test_old\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_new"],
                                            ["test_id"],
                                            [("test_old", None)]))
    self.assertEquals([], results)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("test_old", e.column_name)
    self.assertTrue(not e.reason or "use the new column" not in e.reason)
    self.accumulator.AssertNoMoreExceptions()

  def testDeprecatedValuesBeingRead(self):
    self.zip.writestr("test.txt",
                      "test_id,test_old\n"
                      "1,old_value1\n"
                      "2,old_value2\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_new"],
                                            ["test_id"],
                                            [("test_old", "test_new")]))
    self.assertEquals(2, len(results))
    self.assertEquals('old_value1', results[0][0]['test_old'])
    self.assertEquals('old_value2', results[1][0]['test_old'])
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals('test_old', e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testMissingRequiredColumn(self):
    self.zip.writestr("test.txt", "test_id,test_size\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_size"],
                                            ["test_name"], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("MissingColumn")
    self.assertEquals("test_name", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testRequiredNotInAllCols(self):
    self.zip.writestr("test.txt", "test_id,test_name,test_size\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_size"],
                                            ["test_name"], []))
    self.assertEquals([], results)
    e = self.accumulator.PopException("UnrecognizedColumn")
    self.assertEquals("test_name", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testBlankLine(self):
    # line_num is increased for an empty line
    self.zip.writestr("test.txt",
                      "test_id,test_name\n"
                      "\n"
                      "id1,my name\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 3,
                        ["test_id", "test_name"], ["id1", "my name"])], results)
    self.accumulator.AssertNoMoreExceptions()

  def testExtraComma(self):
    self.zip.writestr("test.txt",
                      "test_id,test_name\n"
                      "id1,my name,\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 2,
                        ["test_id", "test_name"], ["id1", "my name"])],
                      results)
    e = self.accumulator.PopException("OtherProblem")
    self.assertTrue(e.FormatProblem().find("too many cells") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testMissingComma(self):
    self.zip.writestr("test.txt",
                      "test_id,test_name\n"
                      "id1 my name\n")
    results = list(self.loader._ReadCsvDict("test.txt",
                                            ["test_id", "test_name"], [], []))
    self.assertEquals([({"test_id": "id1 my name"}, 2,
                        ["test_id", "test_name"], ["id1 my name"])], results)
    e = self.accumulator.PopException("OtherProblem")
    self.assertTrue(e.FormatProblem().find("missing cells") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testDetectsDuplicateHeaders(self):
    self.zip.writestr(
        "transfers.txt",
        "from_stop_id,from_stop_id,to_stop_id,transfer_type,min_transfer_time,"
        "min_transfer_time,min_transfer_time,min_transfer_time,unknown,"
        "unknown\n"
        "BEATTY_AIRPORT,BEATTY_AIRPORT,BULLFROG,3,,2,,,,\n"
        "BULLFROG,BULLFROG,BEATTY_AIRPORT,2,1200,1,,,,\n")

    list(self.loader._ReadCsvDict("transfers.txt",
                                  transitfeed.Transfer._FIELD_NAMES,
                                  transitfeed.Transfer._REQUIRED_FIELD_NAMES,
                                  transitfeed.Transfer._DEPRECATED_FIELD_NAMES))

    self.accumulator.PopDuplicateColumn("transfers.txt", "min_transfer_time", 4)
    self.accumulator.PopDuplicateColumn("transfers.txt", "from_stop_id", 2)
    self.accumulator.PopDuplicateColumn("transfers.txt", "unknown", 2)
    e = self.accumulator.PopException("UnrecognizedColumn")
    self.assertEquals("unknown", e.column_name)
    self.accumulator.AssertNoMoreExceptions()


class ReadCsvTestCase(util.TestCase):
  def setUp(self):
    self.accumulator = RecordingProblemAccumulator(self)
    self.problems = transitfeed.ProblemReporter(self.accumulator)
    self.zip = zipfile.ZipFile(StringIO(), 'a')
    self.loader = transitfeed.Loader(
        problems=self.problems,
        zip=self.zip)

  def tearDown(self):
    self.accumulator.TearDownAssertNoMoreExceptions()

  def testDetectsDuplicateHeaders(self):
    self.zip.writestr(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date,end_date,end_date,tuesday,unknown,unknown\n"
        "FULLW,1,1,1,1,1,1,1,20070101,20101231,,,,,\n")

    list(self.loader._ReadCSV("calendar.txt",
                              transitfeed.ServicePeriod._FIELD_NAMES,
                              transitfeed.ServicePeriod._REQUIRED_FIELD_NAMES,
                              transitfeed.ServicePeriod._DEPRECATED_FIELD_NAMES
                              ))

    self.accumulator.PopDuplicateColumn("calendar.txt", "end_date", 3)
    self.accumulator.PopDuplicateColumn("calendar.txt", "unknown", 2)
    self.accumulator.PopDuplicateColumn("calendar.txt", "tuesday", 2)
    e = self.accumulator.PopException("UnrecognizedColumn")
    self.assertEquals("unknown", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testDeprecatedColumn(self):
    self.zip.writestr("test.txt", "test_id,test_old\n")
    results = list(self.loader._ReadCSV("test.txt",
                                        ["test_id", "test_new"],
                                        ["test_id"],
                                        [("test_old", "test_new")]))
    self.assertEquals([], results)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("test_old", e.column_name)
    self.assertTrue("test_new" in e.reason)
    self.accumulator.AssertNoMoreExceptions()

  def testDeprecatedColumnWithoutNewColumn(self):
    self.zip.writestr("test.txt", "test_id,test_old\n")
    results = list(self.loader._ReadCSV("test.txt",
                                        ["test_id", "test_new"],
                                        ["test_id"],
                                        [("test_old", None)]))
    self.assertEquals([], results)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("test_old", e.column_name)
    self.assertTrue(not e.reason or "use the new column" not in e.reason)
    self.accumulator.AssertNoMoreExceptions()


class BasicMemoryZipTestCase(util.MemoryZipTestCase):
  def runTest(self):
    self.MakeLoaderAndLoad()
    self.accumulator.AssertNoMoreExceptions()

class ZipCompressionTestCase(util.MemoryZipTestCase):
  def runTest(self):
    schedule = self.MakeLoaderAndLoad()
    self.zip.close()
    write_output = StringIO()
    schedule.WriteGoogleTransitFeed(write_output)
    recompressedzip = zlib.compress(write_output.getvalue())
    write_size = len(write_output.getvalue())
    recompressedzip_size = len(recompressedzip)
    # If zlib can compress write_output it probably wasn't compressed
    self.assertFalse(
        recompressedzip_size < write_size * 0.60,
        "Are you sure WriteGoogleTransitFeed wrote a compressed zip? "
        "Orginial size: %d  recompressed: %d" %
        (write_size, recompressedzip_size))


class StopHierarchyTestCase(util.MemoryZipTestCase):
  def testParentAtSameLatLon(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
        "STATION,Airport,36.868446,-116.784582,1,\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    self.assertEquals(1, schedule.stops["STATION"].location_type)
    self.assertEquals(0, schedule.stops["BEATTY_AIRPORT"].location_type)
    self.accumulator.AssertNoMoreExceptions()

  def testBadLocationType(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,2\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,notvalid\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("location_type", e.column_name)
    self.assertEquals(2, e.row_num)
    self.assertEquals(1, e.type)
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("location_type", e.column_name)
    self.assertEquals(3, e.row_num)
    self.assertEquals(0, e.type)
    self.accumulator.AssertNoMoreExceptions()

  def testBadLocationTypeAtSameLatLon(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
        "STATION,Airport,36.868446,-116.784582,2,\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("location_type", e.column_name)
    self.assertEquals(3, e.row_num)
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("parent_station", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testStationUsed(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,1\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,\n")
    schedule = self.MakeLoaderAndLoad()
    self.accumulator.PopException("UsedStation")
    self.accumulator.AssertNoMoreExceptions()

  def testParentNotFound(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("parent_station", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testParentIsStop(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,BULLFROG\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("parent_station", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testParentOfEntranceIsStop(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,2,BULLFROG\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("location_type", e.column_name)
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("parent_station", e.column_name)
    self.assertTrue(e.FormatProblem().find("location_type=1") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testStationWithParent(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
        "STATION,Airport,36.868446,-116.784582,1,STATION2\n"
        "STATION2,Airport 2,36.868000,-116.784000,1,\n"
        "BULLFROG,Bullfrog,36.868088,-116.784797,,STATION2\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("parent_station", e.column_name)
    self.assertEquals(3, e.row_num)
    self.accumulator.AssertNoMoreExceptions()

  def testStationWithSelfParent(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
        "STATION,Airport,36.868446,-116.784582,1,STATION\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEquals("parent_station", e.column_name)
    self.assertEquals(3, e.row_num)
    self.accumulator.AssertNoMoreExceptions()

  def testStopNearToNonParentStation(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,\n"
        "BULLFROG,Bullfrog,36.868446,-116.784582,,\n"
        "BULLFROG_ST,Bullfrog,36.868446,-116.784582,1,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("DifferentStationTooClose")
    self.assertMatchesRegex(
        "The parent_station of stop \"Bullfrog\"", e.FormatProblem())
    e = self.accumulator.PopException("StopsTooClose")
    self.assertMatchesRegex("BEATTY_AIRPORT", e.FormatProblem())
    self.assertMatchesRegex("BULLFROG", e.FormatProblem())
    self.assertMatchesRegex("are 0.00m apart", e.FormatProblem())
    e = self.accumulator.PopException("DifferentStationTooClose")
    self.assertMatchesRegex(
        "The parent_station of stop \"Airport\"", e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

  def testStopTooFarFromParentStation(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BULLFROG_ST,Bullfrog,36.880,-116.817,1,\n"   # Parent station of all.
        "BEATTY_AIRPORT,Airport,36.880,-116.816,,BULLFROG_ST\n"   # ~ 90m far
        "BULLFROG,Bullfrog,36.881,-116.818,,BULLFROG_ST\n"        # ~ 150m far
        "STAGECOACH,Stagecoach,36.915,-116.751,,BULLFROG_ST\n")   # > 3km far
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("StopTooFarFromParentStation")
    self.assertEqual(1, e.type)  # Warning
    self.assertTrue(e.FormatProblem().find(
        "Bullfrog (ID BULLFROG) is too far from its parent"
        " station Bullfrog (ID BULLFROG_ST)") != -1)
    e = self.accumulator.PopException("StopTooFarFromParentStation")
    self.assertEqual(0, e.type)  # Error
    self.assertTrue(e.FormatProblem().find(
        "Stagecoach (ID STAGECOACH) is too far from its parent"
        " station Bullfrog (ID BULLFROG_ST)") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testStopTimeZone(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station,"
        "stop_timezone\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION,"
        "America/New_York\n"
        "STATION,Airport,36.868446,-116.784582,1,,\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,,\n")    
    self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("InvalidValue")
    self.assertEqual(1, e.type)  # Warning
    self.assertEquals(2, e.row_num)
    self.assertEquals("stop_timezone", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  #Uncomment once validation is implemented
  #def testStationWithoutReference(self):
  #  self.SetArchiveContents(
  #      "stops.txt",
  #      "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
  #      "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,\n"
  #      "STATION,Airport,36.868446,-116.784582,1,\n"
  #      "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
  #      "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
  #  schedule = self.MakeLoaderAndLoad()
  #  e = self.accumulator.PopException("OtherProblem")
  #  self.assertEquals("parent_station", e.column_name)
  #  self.assertEquals(2, e.row_num)
  #  self.accumulator.AssertNoMoreExceptions()


class StopSpacesTestCase(util.MemoryZipTestCase):
  def testFieldsWithSpace(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_code,stop_name,stop_lat,stop_lon,stop_url,location_type,"
        "parent_station\n"
        "BEATTY_AIRPORT, ,Airport,36.868446,-116.784582, , ,\n"
        "BULLFROG,,Bullfrog,36.88108,-116.81797,,,\n"
        "STAGECOACH,,Stagecoach Hotel,36.915682,-116.751677,,,\n")
    schedule = self.MakeLoaderAndLoad()
    self.accumulator.AssertNoMoreExceptions()

  def testFieldsWithEmptyString(self):
    self.SetArchiveContents(
        'stops.txt',
        'stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n'
        'BEATTY_AIRPORT,Airport,"",-116.784582,,\n'
        'BULLFROG,Bullfrog,36.88108,-116.81797,,\n'
        'STAGECOACH,Stagecoach Hotel,36.915682,"",,STAGECOACH-STA\n'
        'STAGECOACH-STA,Stagecoach Hotel Station,36.915682,-116.751677,1,\n')
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('MissingValue')
    self.assertEquals('stop_lat', e.column_name)
    self.assertEquals(2, e.row_num)
    e = self.accumulator.PopException('MissingValue')
    self.assertEquals('stop_lon', e.column_name)
    self.assertEquals(4, e.row_num)
    self.accumulator.AssertNoMoreExceptions()


class StopBlankHeaders(util.MemoryZipTestCase):
  def testBlankHeaderValueAtEnd(self):
    # Modify the stops.txt added by MemoryZipTestCase.setUp. This allows the
    # original stops.txt to be changed without modifying anything in this test.
    # Add a column to the end of every row, leaving the header name blank.
    new = []
    for i, row in enumerate(
        self.GetArchiveContents("stops.txt").split("\n")):
      if i == 0:
        new.append(row + ",")
      elif row:
        new.append(row + "," + str(i))  # Put a junk value in data rows
    self.SetArchiveContents("stops.txt", "\n".join(new))
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("CsvSyntax")
    self.assertTrue(e.FormatProblem().
                    find("header row should not contain any blank") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testBlankHeaderValueAtStart(self):
    # Modify the stops.txt added by MemoryZipTestCase.setUp. This allows the
    # original stops.txt to be changed without modifying anything in this test.
    # Add a column to the start of every row, leaving the header name blank.
    new = []
    for i, row in enumerate(
        self.GetArchiveContents("stops.txt").split("\n")):
      if i == 0:
        new.append("," + row)
      elif row:
        new.append(str(i) + "," + row)  # Put a junk value in data rows
    self.SetArchiveContents("stops.txt", "\n".join(new))
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("CsvSyntax")
    self.assertTrue(e.FormatProblem().
                    find("header row should not contain any blank") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testBlankHeaderValueInMiddle(self):
    # Modify the stops.txt added by MemoryZipTestCase.setUp. This allows the
    # original stops.txt to be changed without modifying anything in this test.
    # Add two columns to the start of every row, leaving the second header name
    # blank.
    new = []
    for i, row in enumerate(
        self.GetArchiveContents("stops.txt").split("\n")):
      if i == 0:
        new.append("test_name,," + row)
      elif row:
        # Put a junk value in data rows
        new.append(str(i) + "," + str(i) + "," + row)
    self.SetArchiveContents("stops.txt", "\n".join(new))
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("CsvSyntax")
    self.assertTrue(e.FormatProblem().
                    find("header row should not contain any blank") != -1)
    e = self.accumulator.PopException("UnrecognizedColumn")
    self.assertEquals("test_name", e.column_name)
    self.accumulator.AssertNoMoreExceptions()


class StopsNearEachOther(util.MemoryZipTestCase):
  def testTooNear(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "BEATTY_AIRPORT,Airport,48.20000,140\n"
        "BULLFROG,Bullfrog,48.20001,140\n"
        "STAGECOACH,Stagecoach Hotel,48.20016,140\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('StopsTooClose')
    self.assertTrue(e.FormatProblem().find("1.11m apart") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testJustFarEnough(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "BEATTY_AIRPORT,Airport,48.20000,140\n"
        "BULLFROG,Bullfrog,48.20002,140\n"
        "STAGECOACH,Stagecoach Hotel,48.20016,140\n")
    schedule = self.MakeLoaderAndLoad()
    # Stops are 2.2m apart
    self.accumulator.AssertNoMoreExceptions()

  def testSameLocation(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "BEATTY_AIRPORT,Airport,48.2,140\n"
        "BULLFROG,Bullfrog,48.2,140\n"
        "STAGECOACH,Stagecoach Hotel,48.20016,140\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('StopsTooClose')
    self.assertTrue(e.FormatProblem().find("0.00m apart") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testStationsTooNear(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,48.20000,140,,BEATTY_AIRPORT_STATION\n"
        "BULLFROG,Bullfrog,48.20003,140,,BULLFROG_STATION\n"
        "BEATTY_AIRPORT_STATION,Airport,48.20001,140,1,\n"
        "BULLFROG_STATION,Bullfrog,48.20002,140,1,\n"
        "STAGECOACH,Stagecoach Hotel,48.20016,140,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('StationsTooClose')
    self.assertTrue(e.FormatProblem().find("1.11m apart") != -1)
    self.assertTrue(e.FormatProblem().find("BEATTY_AIRPORT_STATION") != -1)
    self.accumulator.AssertNoMoreExceptions()

  def testStopNearNonParentStation(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,48.20000,140,,\n"
        "BULLFROG,Bullfrog,48.20005,140,,\n"
        "BULLFROG_STATION,Bullfrog,48.20006,140,1,\n"
        "STAGECOACH,Stagecoach Hotel,48.20016,140,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('DifferentStationTooClose')
    fmt = e.FormatProblem()
    self.assertTrue(re.search(
      r"parent_station of.*BULLFROG.*station.*BULLFROG_STATION.* 1.11m apart",
      fmt), fmt)
    self.accumulator.AssertNoMoreExceptions()


class BadLatLonInStopUnitTest(ValidationTestCase):
  def runTest(self):
    stop = transitfeed.Stop(field_dict={"stop_id": "STOP1",
                                        "stop_name": "Stop one",
                                        "stop_lat": "0x20",
                                        "stop_lon": "140.01"})
    self.ValidateAndExpectInvalidValue(stop, "stop_lat")

    stop = transitfeed.Stop(field_dict={"stop_id": "STOP1",
                                        "stop_name": "Stop one",
                                        "stop_lat": "13.0",
                                        "stop_lon": "1e2"})
    self.ValidateAndExpectInvalidFloatValue(stop, "1e2")


class BadLatLonInFileUnitTest(util.MemoryZipTestCase):
  def runTest(self):
    self.SetArchiveContents(
        "stops.txt",
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "BEATTY_AIRPORT,Airport,0x20,140.00\n"
        "BULLFROG,Bullfrog,48.20001,140.0123\n"
        "STAGECOACH,Stagecoach Hotel,48.002,bogus\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('InvalidValue')
    self.assertEquals(2, e.row_num)
    self.assertEquals("stop_lat", e.column_name)
    e = self.accumulator.PopException('InvalidValue')
    self.assertEquals(4, e.row_num)
    self.assertEquals("stop_lon", e.column_name)
    self.accumulator.AssertNoMoreExceptions()


class LoadUnknownFileInZipTestCase(util.MemoryZipTestCase):
  def runTest(self):
    self.SetArchiveContents(
        "stpos.txt",
        "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
        "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
        "STATION,Airport,36.868446,-116.784582,1,\n"
        "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
        "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('UnknownFile')
    self.assertEquals('stpos.txt', e.file_name)
    self.accumulator.AssertNoMoreExceptions()


class TabDelimitedTestCase(util.MemoryZipTestCase):
  def runTest(self):
    # Create an extremely corrupt file by replacing each comma with a tab,
    # ignoring csv quoting.
    for arcname in self.GetArchiveNames():
      contents = self.GetArchiveContents(arcname)
      self.SetArchiveContents(arcname, contents.replace(",", "\t"))
    schedule = self.MakeLoaderAndLoad()
    # Don't call self.accumulator.AssertNoMoreExceptions() because there are
    # lots of problems but I only care that the validator doesn't crash. In the
    # magical future the validator will stop when the csv is obviously hosed.


class RouteMemoryZipTestCase(util.MemoryZipTestCase):
  def assertLoadAndCheckExtraValues(self, schedule_file):
    """Load file-like schedule_file and check for extra route columns."""
    load_problems = GetTestFailureProblemReporter(
        self, ("ExpirationDate", "UnrecognizedColumn"))
    loaded_schedule = transitfeed.Loader(schedule_file,
                                         problems=load_problems,
                                         extra_validation=True).Load()
    self.assertEqual("foo", loaded_schedule.GetRoute("t")["t_foo"])
    self.assertEqual("", loaded_schedule.GetRoute("AB")["t_foo"])
    self.assertEqual("bar", loaded_schedule.GetRoute("n")["n_foo"])
    self.assertEqual("", loaded_schedule.GetRoute("AB")["n_foo"])
    # Uncomment the following lines to print the string in testExtraFileColumn
    # print repr(zipfile.ZipFile(schedule_file).read("routes.txt"))
    # self.fail()

  def testExtraObjectAttribute(self):
    """Extra columns added to an object are preserved when writing."""
    schedule = self.MakeLoaderAndLoad()
    # Add an attribute after AddRouteObject
    route_t = transitfeed.Route(short_name="T", route_type="Bus", route_id="t")
    schedule.AddRouteObject(route_t)
    route_t.t_foo = "foo"
    # Add an attribute before AddRouteObject
    route_n = transitfeed.Route(short_name="N", route_type="Bus", route_id="n")
    route_n.n_foo = "bar"
    schedule.AddRouteObject(route_n)
    saved_schedule_file = StringIO()
    schedule.WriteGoogleTransitFeed(saved_schedule_file)
    self.accumulator.AssertNoMoreExceptions()

    self.assertLoadAndCheckExtraValues(saved_schedule_file)

  def testExtraFileColumn(self):
    """Extra columns loaded from a file are preserved when writing."""
    # Uncomment the code in assertLoadAndCheckExtraValues to generate this
    # string.
    self.SetArchiveContents(
        "routes.txt",
        "route_id,agency_id,route_short_name,route_long_name,route_type,"
        "t_foo,n_foo\n"
        "AB,DTA,,Airport Bullfrog,3,,\n"
        "t,DTA,T,,3,foo,\n"
        "n,DTA,N,,3,,bar\n")
    load1_problems = GetTestFailureProblemReporter(
        self, ("ExpirationDate", "UnrecognizedColumn"))
    schedule = self.MakeLoaderAndLoad(problems=load1_problems)
    saved_schedule_file = StringIO()
    schedule.WriteGoogleTransitFeed(saved_schedule_file)

    self.assertLoadAndCheckExtraValues(saved_schedule_file)


class RouteConstructorTestCase(util.TestCase):
  def setUp(self):
    self.accumulator = RecordingProblemAccumulator(self)
    self.problems = transitfeed.ProblemReporter(self.accumulator)

  def tearDown(self):
    self.accumulator.TearDownAssertNoMoreExceptions()

  def testDefault(self):
    route = transitfeed.Route()
    repr(route)
    self.assertEqual({}, dict(route))
    route.Validate(self.problems)
    repr(route)
    self.assertEqual({}, dict(route))

    e = self.accumulator.PopException('MissingValue')
    self.assertEqual('route_id', e.column_name)
    e = self.accumulator.PopException('MissingValue')
    self.assertEqual('route_type', e.column_name)
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual('route_short_name', e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testInitArgs(self):
    # route_type name
    route = transitfeed.Route(route_id='id1', short_name='22', route_type='Bus')
    repr(route)
    route.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals(3, route.route_type)  # converted to an int
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'route_type': '3'}, dict(route))

    # route_type as an int
    route = transitfeed.Route(route_id='i1', long_name='Twenty 2', route_type=1)
    repr(route)
    route.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals(1, route.route_type)  # kept as an int
    self.assertEquals({'route_id': 'i1', 'route_long_name': 'Twenty 2',
                       'route_type': '1'}, dict(route))

    # route_type as a string
    route = transitfeed.Route(route_id='id1', short_name='22', route_type='1')
    repr(route)
    route.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals(1, route.route_type)  # converted to an int
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'route_type': '1'}, dict(route))

    # route_type has undefined int value
    route = transitfeed.Route(route_id='id1', short_name='22',
                              route_type='8')
    repr(route)
    route.Validate(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual('route_type', e.column_name)
    self.assertEqual(1, e.type)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'route_type': '8'}, dict(route))

    # route_type that doesn't parse
    route = transitfeed.Route(route_id='id1', short_name='22',
                              route_type='1foo')
    repr(route)
    route.Validate(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual('route_type', e.column_name)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'route_type': '1foo'}, dict(route))

    # agency_id
    route = transitfeed.Route(route_id='id1', short_name='22', route_type=1,
                              agency_id='myage')
    repr(route)
    route.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'route_type': '1', 'agency_id': 'myage'}, dict(route))

  def testInitArgOrder(self):
    """Call Route.__init__ without any names so a change in order is noticed."""
    route = transitfeed.Route('short', 'long name', 'Bus', 'r1', 'a1')
    self.assertEquals({'route_id': 'r1', 'route_short_name': 'short',
                       'route_long_name': 'long name',
                       'route_type': '3', 'agency_id': 'a1'}, dict(route))

  def testFieldDict(self):
    route = transitfeed.Route(field_dict={})
    self.assertEquals({}, dict(route))

    route = transitfeed.Route(field_dict={
      'route_id': 'id1', 'route_short_name': '22', 'agency_id': 'myage',
      'route_type': '1'})
    route.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'agency_id': 'myage', 'route_type': '1'}, dict(route))

    route = transitfeed.Route(field_dict={
      'route_id': 'id1', 'route_short_name': '22', 'agency_id': 'myage',
      'route_type': '1', 'my_column': 'v'})
    route.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'agency_id': 'myage', 'route_type': '1',
                       'my_column':'v'}, dict(route))
    route._private = 0.3  # Isn't copied
    route_copy = transitfeed.Route(field_dict=route)
    self.assertEquals({'route_id': 'id1', 'route_short_name': '22',
                       'agency_id': 'myage', 'route_type': '1',
                       'my_column':'v'}, dict(route_copy))


class RouteValidationTestCase(ValidationTestCase):
  def runTest(self):
    # success case
    route = transitfeed.Route()
    route.route_id = '054C'
    route.route_short_name = '54C'
    route.route_long_name = 'South Side - North Side'
    route.route_type = 7
    route.Validate(self.problems)

    # blank short & long names
    route.route_short_name = ''
    route.route_long_name = '    '
    self.ValidateAndExpectInvalidValue(route, 'route_short_name')

    # short name too long
    route.route_short_name = 'South Side'
    route.route_long_name = ''
    self.ValidateAndExpectInvalidValue(route, 'route_short_name')
    route.route_short_name = 'M7bis'  # 5 is OK
    route.Validate(self.problems)

    # long name contains short name
    route.route_short_name = '54C'
    route.route_long_name = '54C South Side - North Side'
    self.ValidateAndExpectInvalidValue(route, 'route_long_name')
    route.route_long_name = '54C(South Side - North Side)'
    self.ValidateAndExpectInvalidValue(route, 'route_long_name')
    route.route_long_name = '54C-South Side - North Side'
    self.ValidateAndExpectInvalidValue(route, 'route_long_name')

    # long name is same as short name
    route.route_short_name = '54C'
    route.route_long_name = '54C'
    self.ValidateAndExpectInvalidValue(route, 'route_long_name')

    # route description is same as short name
    route.route_desc = '54C'
    route.route_short_name = '54C'
    route.route_long_name = ''
    self.ValidateAndExpectInvalidValue(route, 'route_desc')
    route.route_desc = None

    # route description is same as long name
    route.route_desc = 'South Side - North Side'
    route.route_long_name = 'South Side - North Side'
    self.ValidateAndExpectInvalidValue(route, 'route_desc')
    route.route_desc = None

    # invalid route types
    route.route_type = 8
    self.ValidateAndExpectInvalidValue(route, 'route_type')
    route.route_type = -1
    self.ValidateAndExpectInvalidValue(route, 'route_type')
    route.route_type = 7

    # invalid route URL
    route.route_url = 'www.example.com'
    self.ValidateAndExpectInvalidValue(route, 'route_url')
    route.route_url = None

    # invalid route color
    route.route_color = 'orange'
    self.ValidateAndExpectInvalidValue(route, 'route_color')
    route.route_color = None

    # invalid route text color
    route.route_text_color = 'orange'
    self.ValidateAndExpectInvalidValue(route, 'route_text_color')
    route.route_text_color = None

    # missing route ID
    route.route_id = None
    self.ValidateAndExpectMissingValue(route, 'route_id')
    route.route_id = '054C'

    # bad color contrast
    route.route_text_color = None # black
    route.route_color = '0000FF'  # Bad
    self.ValidateAndExpectInvalidValue(route, 'route_color')
    route.route_color = '00BF00'  # OK
    route.Validate(self.problems)
    route.route_color = '005F00'  # Bad
    self.ValidateAndExpectInvalidValue(route, 'route_color')
    route.route_color = 'FF00FF'  # OK
    route.Validate(self.problems)
    route.route_text_color = 'FFFFFF' # OK too
    route.Validate(self.problems)
    route.route_text_color = '00FF00' # think of color-blind people!
    self.ValidateAndExpectInvalidValue(route, 'route_color')
    route.route_text_color = '007F00'
    route.route_color = 'FF0000'
    self.ValidateAndExpectInvalidValue(route, 'route_color')
    route.route_color = '00FFFF'      # OK
    route.Validate(self.problems)
    route.route_text_color = None # black
    route.route_color = None      # white
    route.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()


class ShapeValidationTestCase(ValidationTestCase):
  def ExpectFailedAdd(self, shape, lat, lon, dist, column_name, value):
    self.ExpectInvalidValueInClosure(
        column_name, value,
        lambda: shape.AddPoint(lat, lon, dist, self.problems))

  def runTest(self):
    shape = transitfeed.Shape('TEST')
    repr(shape)  # shouldn't crash
    self.ValidateAndExpectOtherProblem(shape)  # no points!

    self.ExpectFailedAdd(shape, 36.905019, -116.763207, -1,
                         'shape_dist_traveled', -1)

    shape.AddPoint(36.915760, -116.751709, 0, self.problems)
    shape.AddPoint(36.905018, -116.763206, 5, self.problems)
    shape.Validate(self.problems)

    shape.shape_id = None
    self.ValidateAndExpectMissingValue(shape, 'shape_id')
    shape.shape_id = 'TEST'

    self.ExpectFailedAdd(shape, 91, -116.751709, 6, 'shape_pt_lat', 91)
    self.ExpectFailedAdd(shape, -91, -116.751709, 6, 'shape_pt_lat', -91)

    self.ExpectFailedAdd(shape, 36.915760, -181, 6, 'shape_pt_lon', -181)
    self.ExpectFailedAdd(shape, 36.915760, 181, 6, 'shape_pt_lon', 181)

    self.ExpectFailedAdd(shape, 0.5, -0.5, 6, 'shape_pt_lat', 0.5)
    self.ExpectFailedAdd(shape, 0, 0, 6, 'shape_pt_lat', 0)

    # distance decreasing is bad, but staying the same is OK
    shape.AddPoint(36.905019, -116.763206, 4, self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('Each subsequent point', e.FormatProblem())
    self.assertMatchesRegex('distance was 5.000000.', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

    shape.AddPoint(36.925019, -116.764206, 6, self.problems)
    self.accumulator.AssertNoMoreExceptions()

    shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 6, 8)
    shape.AddShapePointObjectUnsorted(shapepoint, self.problems)
    shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 5, 10)
    shape.AddShapePointObjectUnsorted(shapepoint, self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('Each subsequent point', e.FormatProblem())
    self.assertMatchesRegex('distance was 8.000000.', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

    shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 6, 11)
    shape.AddShapePointObjectUnsorted(shapepoint, self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('The sequence number 6 occurs ', e.FormatProblem())
    self.assertMatchesRegex('once in shape TEST.', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()


class ShapePointValidationTestCase(ValidationTestCase):
  def runTest(self):
    shapepoint = transitfeed.ShapePoint('', 36.915720, -116.7156, 0, 0)
    self.ExpectMissingValueInClosure('shape_id',
        lambda: shapepoint.ParseAttributes(self.problems))

    shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '00', '0')
    shapepoint.ParseAttributes(self.problems)
    e = self.accumulator.PopException('InvalidNonNegativeIntegerValue')
    self.assertMatchesRegex('not have a leading zero', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

    shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', -1, '0')
    shapepoint.ParseAttributes(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('Value should be a number', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

    shapepoint = transitfeed.ShapePoint('T', '0.1', '0.1', '1', '0')
    shapepoint.ParseAttributes(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('too close to 0, 0,', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

    shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '0', '')
    shapepoint.ParseAttributes(self.problems)
    shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '0', '-1')
    shapepoint.ParseAttributes(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('Invalid value -1.0', e.FormatProblem())
    self.assertMatchesRegex('should be a positive number', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()


class FareAttributeValidationTestCase(ValidationTestCase):
  def runTest(self):
    fare = transitfeed.FareAttribute()
    fare.fare_id = "normal"
    fare.price = 1.50
    fare.currency_type = "USD"
    fare.payment_method = 0
    fare.transfers = 1
    fare.transfer_duration = 7200
    fare.Validate(self.problems)

    fare.fare_id = None
    self.ValidateAndExpectMissingValue(fare, "fare_id")
    fare.fare_id = ''
    self.ValidateAndExpectMissingValue(fare, "fare_id")
    fare.fare_id = "normal"

    fare.price = "1.50"
    self.ValidateAndExpectInvalidValue(fare, "price")
    fare.price = 1
    fare.Validate(self.problems)
    fare.price = None
    self.ValidateAndExpectMissingValue(fare, "price")
    fare.price = 0.0
    fare.Validate(self.problems)
    fare.price = -1.50
    self.ValidateAndExpectInvalidValue(fare, "price")
    fare.price = 1.50

    fare.currency_type = ""
    self.ValidateAndExpectMissingValue(fare, "currency_type")
    fare.currency_type = None
    self.ValidateAndExpectMissingValue(fare, "currency_type")
    fare.currency_type = "usd"
    self.ValidateAndExpectInvalidValue(fare, "currency_type")
    fare.currency_type = "KML"
    self.ValidateAndExpectInvalidValue(fare, "currency_type")
    fare.currency_type = "USD"

    fare.payment_method = "0"
    self.ValidateAndExpectInvalidValue(fare, "payment_method")
    fare.payment_method = -1
    self.ValidateAndExpectInvalidValue(fare, "payment_method")
    fare.payment_method = 1
    fare.Validate(self.problems)
    fare.payment_method = 2
    self.ValidateAndExpectInvalidValue(fare, "payment_method")
    fare.payment_method = None
    self.ValidateAndExpectMissingValue(fare, "payment_method")
    fare.payment_method = ""
    self.ValidateAndExpectMissingValue(fare, "payment_method")
    fare.payment_method = 0

    fare.transfers = "1"
    self.ValidateAndExpectInvalidValue(fare, "transfers")
    fare.transfers = -1
    self.ValidateAndExpectInvalidValue(fare, "transfers")
    fare.transfers = 2
    fare.Validate(self.problems)
    fare.transfers = 3
    self.ValidateAndExpectInvalidValue(fare, "transfers")
    fare.transfers = None
    fare.Validate(self.problems)
    fare.transfers = 1

    fare.transfer_duration = 0
    fare.Validate(self.problems)
    fare.transfer_duration = None
    fare.Validate(self.problems)
    fare.transfer_duration = -3600
    self.ValidateAndExpectInvalidValue(fare, "transfer_duration")
    fare.transfers = 0  # no transfers allowed and duration specified!
    fare.transfer_duration = 3600
    fare.Validate(self.problems)
    fare.transfers = 1
    fare.transfer_duration = "3600"
    self.ValidateAndExpectInvalidValue(fare, "transfer_duration")
    fare.transfer_duration = 7200
    self.accumulator.AssertNoMoreExceptions()


class TransferObjectTestCase(ValidationTestCase):
  def testValidation(self):
    # Totally bogus data shouldn't cause a crash
    transfer = transitfeed.Transfer(field_dict={"ignored": "foo"})
    self.assertEquals(0, transfer.transfer_type)

    transfer = transitfeed.Transfer(from_stop_id="S1", to_stop_id="S2",
                                    transfer_type="1")
    self.assertEquals("S1", transfer.from_stop_id)
    self.assertEquals("S2", transfer.to_stop_id)
    self.assertEquals(1, transfer.transfer_type)
    self.assertEquals(None, transfer.min_transfer_time)
    # references to other tables aren't checked without schedule so this
    # validates even though from_stop_id and to_stop_id are invalid.
    transfer.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.assertEquals("S1", transfer.from_stop_id)
    self.assertEquals("S2", transfer.to_stop_id)
    self.assertEquals(1, transfer.transfer_type)
    self.assertEquals(None, transfer.min_transfer_time)
    self.accumulator.AssertNoMoreExceptions()

    transfer = transitfeed.Transfer(field_dict={"from_stop_id": "S1", \
                                                "to_stop_id": "S2", \
                                                "transfer_type": "2", \
                                                "min_transfer_time": "2"})
    self.assertEquals("S1", transfer.from_stop_id)
    self.assertEquals("S2", transfer.to_stop_id)
    self.assertEquals(2, transfer.transfer_type)
    self.assertEquals(2, transfer.min_transfer_time)
    transfer.Validate(self.problems)
    self.assertEquals("S1", transfer.from_stop_id)
    self.assertEquals("S2", transfer.to_stop_id)
    self.assertEquals(2, transfer.transfer_type)
    self.assertEquals(2, transfer.min_transfer_time)
    self.accumulator.AssertNoMoreExceptions()

    transfer = transitfeed.Transfer(field_dict={"from_stop_id": "S1", \
                                                "to_stop_id": "S2", \
                                                "transfer_type": "-4", \
                                                "min_transfer_time": "2"})
    self.assertEquals("S1", transfer.from_stop_id)
    self.assertEquals("S2", transfer.to_stop_id)
    self.assertEquals("-4", transfer.transfer_type)
    self.assertEquals(2, transfer.min_transfer_time)
    transfer.Validate(self.problems)
    e = self.accumulator.PopInvalidValue("transfer_type")
    e = self.accumulator.PopException(
        "MinimumTransferTimeSetWithInvalidTransferType")
    self.assertEquals("S1", transfer.from_stop_id)
    self.assertEquals("S2", transfer.to_stop_id)
    self.assertEquals("-4", transfer.transfer_type)
    self.assertEquals(2, transfer.min_transfer_time)

    transfer = transitfeed.Transfer(field_dict={"from_stop_id": "S1", \
                                                "to_stop_id": "S2", \
                                                "transfer_type": "", \
                                                "min_transfer_time": "-1"})
    self.assertEquals(0, transfer.transfer_type)
    transfer.Validate(self.problems)
    # It's negative *and* transfer_type is not 2
    e = self.accumulator.PopException(
        "MinimumTransferTimeSetWithInvalidTransferType")
    e = self.accumulator.PopInvalidValue("min_transfer_time")

    # Non-integer min_transfer_time with transfer_type == 2
    transfer = transitfeed.Transfer(field_dict={"from_stop_id": "S1", \
                                                "to_stop_id": "S2", \
                                                "transfer_type": "2", \
                                                "min_transfer_time": "foo"})
    self.assertEquals("foo", transfer.min_transfer_time)
    transfer.Validate(self.problems)
    e = self.accumulator.PopInvalidValue("min_transfer_time")

    # Non-integer min_transfer_time with transfer_type != 2
    transfer = transitfeed.Transfer(field_dict={"from_stop_id": "S1", \
                                                "to_stop_id": "S2", \
                                                "transfer_type": "1", \
                                                "min_transfer_time": "foo"})
    self.assertEquals("foo", transfer.min_transfer_time)
    transfer.Validate(self.problems)
    # It's not an integer *and* transfer_type is not 2
    e = self.accumulator.PopException(
        "MinimumTransferTimeSetWithInvalidTransferType")
    e = self.accumulator.PopInvalidValue("min_transfer_time")

    # Fractional min_transfer_time with transfer_type == 2
    transfer = transitfeed.Transfer(field_dict={"from_stop_id": "S1", \
                                                "to_stop_id": "S2", \
                                                "transfer_type": "2", \
                                                "min_transfer_time": "2.5"})
    self.assertEquals("2.5", transfer.min_transfer_time)
    transfer.Validate(self.problems)
    e = self.accumulator.PopInvalidValue("min_transfer_time")

    # Fractional min_transfer_time with transfer_type != 2
    transfer = transitfeed.Transfer(field_dict={"from_stop_id": "S1", \
                                                "to_stop_id": "S2", \
                                                "transfer_type": "1", \
                                                "min_transfer_time": "2.5"})
    self.assertEquals("2.5", transfer.min_transfer_time)
    transfer.Validate(self.problems)
    # It's not an integer *and* transfer_type is not 2
    e = self.accumulator.PopException(
        "MinimumTransferTimeSetWithInvalidTransferType")
    e = self.accumulator.PopInvalidValue("min_transfer_time")

    # simple successes
    transfer = transitfeed.Transfer()
    transfer.from_stop_id = "S1"
    transfer.to_stop_id = "S2"
    transfer.transfer_type = 0
    repr(transfer)  # shouldn't crash
    transfer.Validate(self.problems)
    transfer.transfer_type = 3
    transfer.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()

    # transfer_type is out of range
    transfer.transfer_type = 4
    self.ValidateAndExpectInvalidValue(transfer, "transfer_type")
    transfer.transfer_type = -1
    self.ValidateAndExpectInvalidValue(transfer, "transfer_type")
    transfer.transfer_type = "text"
    self.ValidateAndExpectInvalidValue(transfer, "transfer_type")
    transfer.transfer_type = 2

    # invalid min_transfer_time
    transfer.min_transfer_time = -1
    self.ValidateAndExpectInvalidValue(transfer, "min_transfer_time")
    transfer.min_transfer_time = "text"
    self.ValidateAndExpectInvalidValue(transfer, "min_transfer_time")
    transfer.min_transfer_time = 4*3600
    transfer.Validate(self.problems)
    e = self.accumulator.PopInvalidValue("min_transfer_time")
    self.assertEquals(e.type, transitfeed.TYPE_WARNING)
    transfer.min_transfer_time = 25*3600
    transfer.Validate(self.problems)
    e = self.accumulator.PopInvalidValue("min_transfer_time")
    self.assertEquals(e.type, transitfeed.TYPE_ERROR)
    transfer.min_transfer_time = 250
    transfer.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()

    # missing stop ids
    transfer.from_stop_id = ""
    self.ValidateAndExpectMissingValue(transfer, 'from_stop_id')
    transfer.from_stop_id = "S1"
    transfer.to_stop_id = None
    self.ValidateAndExpectMissingValue(transfer, 'to_stop_id')
    transfer.to_stop_id = "S2"

    # from_stop_id and to_stop_id are present in schedule
    schedule = transitfeed.Schedule()
    # 597m appart
    stop1 = schedule.AddStop(57.5, 30.2, "stop 1")
    stop2 = schedule.AddStop(57.5, 30.21, "stop 2")
    transfer = transitfeed.Transfer(schedule=schedule)
    transfer.from_stop_id = stop1.stop_id
    transfer.to_stop_id = stop2.stop_id
    transfer.transfer_type = 2
    transfer.min_transfer_time = 600
    repr(transfer)  # shouldn't crash
    transfer.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()

    # only from_stop_id is present in schedule
    schedule = transitfeed.Schedule()
    stop1 = schedule.AddStop(57.5, 30.2, "stop 1")
    transfer = transitfeed.Transfer(schedule=schedule)
    transfer.from_stop_id = stop1.stop_id
    transfer.to_stop_id = "unexist"
    transfer.transfer_type = 2
    transfer.min_transfer_time = 250
    self.ValidateAndExpectInvalidValue(transfer, 'to_stop_id')
    transfer.from_stop_id = "unexist"
    transfer.to_stop_id = stop1.stop_id
    self.ValidateAndExpectInvalidValue(transfer, "from_stop_id")
    self.accumulator.AssertNoMoreExceptions()

    # Transfer can only be added to a schedule once because _schedule is set
    transfer = transitfeed.Transfer()
    transfer.from_stop_id = stop1.stop_id
    transfer.to_stop_id = stop1.stop_id
    schedule.AddTransferObject(transfer)
    self.assertRaises(AssertionError, schedule.AddTransferObject, transfer)

  def testValidationSpeedDistanceAllTransferTypes(self):
    schedule = transitfeed.Schedule()
    transfer = transitfeed.Transfer(schedule=schedule)
    stop1 = schedule.AddStop(1, 0, "stop 1")
    stop2 = schedule.AddStop(0, 1, "stop 2")
    transfer = transitfeed.Transfer(schedule=schedule)
    transfer.from_stop_id = stop1.stop_id
    transfer.to_stop_id = stop2.stop_id
    for transfer_type in [0, 1, 2, 3]:
      transfer.transfer_type = transfer_type

      # from_stop_id and to_stop_id are present in schedule
      # and a bit far away (should be warning)
      # 2303m appart
      stop1.stop_lat = 57.5
      stop1.stop_lon = 30.32
      stop2.stop_lat = 57.52
      stop2.stop_lon = 30.33
      transfer.min_transfer_time = 2500
      repr(transfer)  # shouldn't crash
      transfer.Validate(self.problems)
      if transfer_type != 2:
        e = self.accumulator.PopException(
            "MinimumTransferTimeSetWithInvalidTransferType")
        self.assertEquals(e.transfer_type, transfer.transfer_type)
      e = self.accumulator.PopException('TransferDistanceTooBig')
      self.assertEquals(e.type, transitfeed.TYPE_WARNING)
      self.assertEquals(e.from_stop_id, stop1.stop_id)
      self.assertEquals(e.to_stop_id, stop2.stop_id)
      self.accumulator.AssertNoMoreExceptions()

      # from_stop_id and to_stop_id are present in schedule
      # and too far away (should be error)
      # 11140m appart
      stop1.stop_lat = 57.5
      stop1.stop_lon = 30.32
      stop2.stop_lat = 57.4
      stop2.stop_lon = 30.33
      transfer.min_transfer_time = 3600
      repr(transfer)  # shouldn't crash
      transfer.Validate(self.problems)
      if transfer_type != 2:
        e = self.accumulator.PopException(
            "MinimumTransferTimeSetWithInvalidTransferType")
        self.assertEquals(e.transfer_type, transfer.transfer_type)
      e = self.accumulator.PopException('TransferDistanceTooBig')
      self.assertEquals(e.type, transitfeed.TYPE_ERROR)
      self.assertEquals(e.from_stop_id, stop1.stop_id)
      self.assertEquals(e.to_stop_id, stop2.stop_id)
      e = self.accumulator.PopException('TransferWalkingSpeedTooFast')
      self.assertEquals(e.type, transitfeed.TYPE_WARNING)
      self.assertEquals(e.from_stop_id, stop1.stop_id)
      self.assertEquals(e.to_stop_id, stop2.stop_id)
      self.accumulator.AssertNoMoreExceptions()

  def testSmallTransferTimeTriggersWarning(self):
    # from_stop_id and to_stop_id are present in schedule
    # and transfer time is too small
    schedule = transitfeed.Schedule()
    # 298m appart
    stop1 = schedule.AddStop(57.5, 30.2, "stop 1")
    stop2 = schedule.AddStop(57.5, 30.205, "stop 2")
    transfer = transitfeed.Transfer(schedule=schedule)
    transfer.from_stop_id = stop1.stop_id
    transfer.to_stop_id = stop2.stop_id
    transfer.transfer_type = 2
    transfer.min_transfer_time = 1
    repr(transfer)  # shouldn't crash
    transfer.Validate(self.problems)
    e = self.accumulator.PopException('TransferWalkingSpeedTooFast')
    self.assertEquals(e.type, transitfeed.TYPE_WARNING)
    self.assertEquals(e.from_stop_id, stop1.stop_id)
    self.assertEquals(e.to_stop_id, stop2.stop_id)
    self.accumulator.AssertNoMoreExceptions()

  def testVeryCloseStationsDoNotTriggerWarning(self):
    # from_stop_id and to_stop_id are present in schedule
    # and transfer time is too small, but stations
    # are very close together.
    schedule = transitfeed.Schedule()
    # 239m appart
    stop1 = schedule.AddStop(57.5, 30.2, "stop 1")
    stop2 = schedule.AddStop(57.5, 30.204, "stop 2")
    transfer = transitfeed.Transfer(schedule=schedule)
    transfer.from_stop_id = stop1.stop_id
    transfer.to_stop_id = stop2.stop_id
    transfer.transfer_type = 2
    transfer.min_transfer_time = 1
    repr(transfer)  # shouldn't crash
    transfer.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testCustomAttribute(self):
    """Add unknown attributes to a Transfer and make sure they are saved."""
    transfer = transitfeed.Transfer()
    transfer.attr1 = "foo1"
    schedule = self.SimpleSchedule()
    transfer.to_stop_id = "stop1"
    transfer.from_stop_id = "stop1"
    schedule.AddTransferObject(transfer)
    transfer.attr2 = "foo2"

    saved_schedule_file = StringIO()
    schedule.WriteGoogleTransitFeed(saved_schedule_file)
    self.accumulator.AssertNoMoreExceptions()

    # Ignore NoServiceExceptions error to keep the test simple
    load_problems = GetTestFailureProblemReporter(
        self, ("ExpirationDate", "UnrecognizedColumn", "NoServiceExceptions"))
    loaded_schedule = transitfeed.Loader(saved_schedule_file,
                                         problems=load_problems,
                                         extra_validation=True).Load()
    transfers = loaded_schedule.GetTransferList()
    self.assertEquals(1, len(transfers))
    self.assertEquals("foo1", transfers[0].attr1)
    self.assertEquals("foo1", transfers[0]["attr1"])
    self.assertEquals("foo2", transfers[0].attr2)
    self.assertEquals("foo2", transfers[0]["attr2"])

  def testDuplicateId(self):
    schedule = self.SimpleSchedule()
    transfer1 = transitfeed.Transfer(from_stop_id="stop1", to_stop_id="stop2")
    schedule.AddTransferObject(transfer1)
    transfer2 = transitfeed.Transfer(field_dict=transfer1)
    transfer2.transfer_type = 3
    schedule.AddTransferObject(transfer2)
    transfer2.Validate()
    e = self.accumulator.PopException('DuplicateID')
    self.assertEquals('(from_stop_id, to_stop_id)', e.column_name)
    self.assertEquals('(stop1, stop2)', e.value)
    self.assertTrue(e.IsWarning())
    self.accumulator.AssertNoMoreExceptions()
    # Check that both transfers were kept
    self.assertEquals(transfer1, schedule.GetTransferList()[0])
    self.assertEquals(transfer2, schedule.GetTransferList()[1])

    # Adding a transfer with a different ID shouldn't cause a problem report.
    transfer3 = transitfeed.Transfer(from_stop_id="stop1", to_stop_id="stop3")
    schedule.AddTransferObject(transfer3)
    self.assertEquals(3, len(schedule.GetTransferList()))
    self.accumulator.AssertNoMoreExceptions()

    # GetTransferIter should return all Transfers
    transfer4 = transitfeed.Transfer(from_stop_id="stop1")
    schedule.AddTransferObject(transfer4)
    self.assertEquals(
        ",stop2,stop2,stop3",
        ",".join(sorted(t["to_stop_id"] for t in schedule.GetTransferIter())))
    self.accumulator.AssertNoMoreExceptions()


class TransferValidationTestCase(util.MemoryZipTestCase):
  """Integration test for transfers."""

  def testInvalidStopIds(self):
    self.SetArchiveContents(
        "transfers.txt",
        "from_stop_id,to_stop_id,transfer_type\n"
        "DOESNOTEXIST,BULLFROG,2\n"
        ",BULLFROG,2\n"
        "BULLFROG,,2\n"
        "BULLFROG,DOESNOTEXISTEITHER,2\n"
        "DOESNOTEXIT,DOESNOTEXISTEITHER,2\n"
        ",,2\n")
    schedule = self.MakeLoaderAndLoad()
    # First row
    e = self.accumulator.PopInvalidValue('from_stop_id')
    # Second row
    e = self.accumulator.PopMissingValue('from_stop_id')
    # Third row
    e = self.accumulator.PopMissingValue('to_stop_id')
    # Fourth row
    e = self.accumulator.PopInvalidValue('to_stop_id')
    # Fifth row
    e = self.accumulator.PopInvalidValue('from_stop_id')
    e = self.accumulator.PopInvalidValue('to_stop_id')
    # Sixth row
    e = self.accumulator.PopMissingValue('from_stop_id')
    e = self.accumulator.PopMissingValue('to_stop_id')
    self.accumulator.AssertNoMoreExceptions()

  def testDuplicateTransfer(self):
    self.AppendToArchiveContents(
        "stops.txt",
        "BEATTY_AIRPORT_HANGER,Airport Hanger,36.868178,-116.784915\n"
        "BEATTY_AIRPORT_34,Runway 34,36.85352,-116.786316\n")
    self.AppendToArchiveContents(
        "trips.txt",
        "AB,FULLW,AIR1\n")
    self.AppendToArchiveContents(
        "stop_times.txt",
        "AIR1,7:00:00,7:00:00,BEATTY_AIRPORT_HANGER,1\n"
        "AIR1,7:05:00,7:05:00,BEATTY_AIRPORT_34,2\n"
        "AIR1,7:10:00,7:10:00,BEATTY_AIRPORT_HANGER,3\n")
    self.SetArchiveContents(
        "transfers.txt",
        "from_stop_id,to_stop_id,transfer_type\n"
        "BEATTY_AIRPORT,BEATTY_AIRPORT_HANGER,0\n"
        "BEATTY_AIRPORT,BEATTY_AIRPORT_HANGER,3")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('DuplicateID')
    self.assertEquals('(from_stop_id, to_stop_id)', e.column_name)
    self.assertEquals('(BEATTY_AIRPORT, BEATTY_AIRPORT_HANGER)', e.value)
    self.assertTrue(e.IsWarning())
    self.assertEquals('transfers.txt', e.file_name)
    self.assertEquals(3, e.row_num)
    self.accumulator.AssertNoMoreExceptions()

    saved_schedule_file = StringIO()
    schedule.WriteGoogleTransitFeed(saved_schedule_file)
    self.accumulator.AssertNoMoreExceptions()
    load_problems = GetTestFailureProblemReporter(
        self, ("ExpirationDate", "DuplicateID"))
    loaded_schedule = transitfeed.Loader(saved_schedule_file,
                                         problems=load_problems,
                                         extra_validation=True).Load()
    self.assertEquals(
        [0, 3],
        [int(t.transfer_type) for t in loaded_schedule.GetTransferIter()])


class ServicePeriodValidationTestCase(ValidationTestCase):
  def runTest(self):
    # success case
    period = transitfeed.ServicePeriod()
    repr(period)  # shouldn't crash
    period.service_id = 'WEEKDAY'
    period.start_date = '20070101'
    period.end_date = '20071231'
    period.day_of_week[0] = True
    repr(period)  # shouldn't crash
    period.Validate(self.problems)

    # missing start_date. If one of start_date or end_date is None then
    # ServicePeriod.Validate assumes the required column is missing and already
    # generated an error. Instead set it to an empty string, such as when the
    # csv cell is empty. See also comment in ServicePeriod.Validate.
    period.start_date = ''
    self.ValidateAndExpectMissingValue(period, 'start_date')
    period.start_date = '20070101'

    # missing end_date
    period.end_date = ''
    self.ValidateAndExpectMissingValue(period, 'end_date')
    period.end_date = '20071231'

    # invalid start_date
    period.start_date = '2007-01-01'
    self.ValidateAndExpectInvalidValue(period, 'start_date')
    period.start_date = '20070101'

    # impossible start_date
    period.start_date = '20070229'
    self.ValidateAndExpectInvalidValue(period, 'start_date')
    period.start_date = '20070101'

    # invalid end_date
    period.end_date = '2007/12/31'
    self.ValidateAndExpectInvalidValue(period, 'end_date')
    period.end_date = '20071231'

    # start & end dates out of order
    period.end_date = '20060101'
    self.ValidateAndExpectInvalidValue(period, 'end_date')
    period.end_date = '20071231'

    # no service in period
    period.day_of_week[0] = False
    self.ValidateAndExpectOtherProblem(period)
    period.day_of_week[0] = True

    # invalid exception date
    period.SetDateHasService('2007', False)
    self.ValidateAndExpectInvalidValue(period, 'date', '2007')
    period.ResetDateToNormalService('2007')

    period2 = transitfeed.ServicePeriod(
        field_list=['serviceid1', '20060101', '20071231', '1', '0', 'h', '1',
                    '1', '1', '1'])
    self.ValidateAndExpectInvalidValue(period2, 'wednesday', 'h')
    repr(period)  # shouldn't crash

  def testHasExceptions(self):
    # A new ServicePeriod object has no exceptions
    period = transitfeed.ServicePeriod()
    self.assertFalse(period.HasExceptions())

    # Only regular service, no exceptions
    period.service_id = 'WEEKDAY'
    period.start_date = '20070101'
    period.end_date = '20071231'
    period.day_of_week[0] = True
    self.assertFalse(period.HasExceptions())

    # Regular service + removed service exception
    period.SetDateHasService('20070101', False)
    self.assertTrue(period.HasExceptions())

    # Regular service + added service exception
    period.SetDateHasService('20070101', True)
    self.assertTrue(period.HasExceptions())

    # Only added service exception
    period = transitfeed.ServicePeriod()
    period.SetDateHasService('20070101', True)
    self.assertTrue(period.HasExceptions())

    # Only removed service exception
    period = transitfeed.ServicePeriod()
    period.SetDateHasService('20070101', False)
    self.assertTrue(period.HasExceptions())

  def testServicePeriodDateOutsideValidRange(self):
    # regular service, no exceptions, start_date invalid
    period = transitfeed.ServicePeriod()
    period.service_id = 'WEEKDAY'
    period.start_date = '20070101'
    period.end_date = '21071231'
    period.day_of_week[0] = True
    self.ValidateAndExpectDateOutsideValidRange(period, 'end_date', '21071231')

    # regular service, no exceptions, start_date invalid
    period2 = transitfeed.ServicePeriod()
    period2.service_id = 'SUNDAY'
    period2.start_date = '18990101'
    period2.end_date = '19991231'
    period2.day_of_week[6] = True
    self.ValidateAndExpectDateOutsideValidRange(period2, 'start_date',
                                                '18990101')

    # regular service, no exceptions, both start_date and end_date invalid
    period3 = transitfeed.ServicePeriod()
    period3.service_id = 'SATURDAY'
    period3.start_date = '18990101'
    period3.end_date = '29991231'
    period3.day_of_week[5] = True
    period3.Validate(self.problems)
    e = self.accumulator.PopDateOutsideValidRange('start_date')
    self.assertEquals('18990101', e.value)
    e.FormatProblem() #should not throw any exceptions
    e.FormatContext() #should not throw any exceptions
    e = self.accumulator.PopDateOutsideValidRange('end_date')
    self.assertEqual('29991231', e.value)
    e.FormatProblem() #should not throw any exceptions
    e.FormatContext() #should not throw any exceptions
    self.accumulator.AssertNoMoreExceptions()

  def testServicePeriodExceptionDateOutsideValidRange(self):
    """ date exceptions of ServicePeriod must be in [1900,2100] """
    # regular service, 3 exceptions, date of 1st and 3rd invalid
    period = transitfeed.ServicePeriod()
    period.service_id = 'WEEKDAY'
    period.start_date = '20070101'
    period.end_date = '20071231'
    period.day_of_week[0] = True
    period.SetDateHasService('21070101', False) #removed service exception
    period.SetDateHasService('20070205', False) #removed service exception
    period.SetDateHasService('10070102', True) #added service exception
    period.Validate(self.problems)

    # check for error from first date exception
    e = self.accumulator.PopDateOutsideValidRange('date')
    self.assertEqual('21070101', e.value)
    e.FormatProblem() #should not throw any exceptions
    e.FormatContext() #should not throw any exceptions

    # check for error from third date exception
    e = self.accumulator.PopDateOutsideValidRange('date')
    self.assertEqual('10070102', e.value)
    e.FormatProblem() #should not throw any exceptions
    e.FormatContext() #should not throw any exceptions
    self.accumulator.AssertNoMoreExceptions()


class ServicePeriodDateRangeTestCase(ValidationTestCase):
  def runTest(self):
    period = transitfeed.ServicePeriod()
    period.service_id = 'WEEKDAY'
    period.start_date = '20070101'
    period.end_date = '20071231'
    period.SetWeekdayService(True)
    period.SetDateHasService('20071231', False)
    period.Validate(self.problems)
    self.assertEqual(('20070101', '20071231'), period.GetDateRange())

    period2 = transitfeed.ServicePeriod()
    period2.service_id = 'HOLIDAY'
    period2.SetDateHasService('20071225', True)
    period2.SetDateHasService('20080101', True)
    period2.SetDateHasService('20080102', False)
    period2.Validate(self.problems)
    self.assertEqual(('20071225', '20080101'), period2.GetDateRange())

    period2.start_date = '20071201'
    period2.end_date = '20071225'
    period2.Validate(self.problems)
    self.assertEqual(('20071201', '20080101'), period2.GetDateRange())

    period3 = transitfeed.ServicePeriod()
    self.assertEqual((None, None), period3.GetDateRange())

    period4 = transitfeed.ServicePeriod()
    period4.service_id = 'halloween'
    period4.SetDateHasService('20051031', True)
    self.assertEqual(('20051031', '20051031'), period4.GetDateRange())
    period4.Validate(self.problems)

    schedule = transitfeed.Schedule(problem_reporter=self.problems)
    self.assertEqual((None, None), schedule.GetDateRange())
    schedule.AddServicePeriodObject(period)
    self.assertEqual(('20070101', '20071231'), schedule.GetDateRange())
    schedule.AddServicePeriodObject(period2)
    self.assertEqual(('20070101', '20080101'), schedule.GetDateRange())
    schedule.AddServicePeriodObject(period4)
    self.assertEqual(('20051031', '20080101'), schedule.GetDateRange())
    self.accumulator.AssertNoMoreExceptions()


class NoServiceExceptionsTestCase(util.MemoryZipTestCase):

  def testNoCalendarDates(self):
    self.RemoveArchive("calendar_dates.txt")
    self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("NoServiceExceptions")
    self.accumulator.AssertNoMoreExceptions()

  def testNoExceptionsWhenFeedActiveForShortPeriodOfTime(self):
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "FULLW,1,1,1,1,1,1,1,20070101,20070630\n"
        "WE,0,0,0,0,0,1,1,20070101,20070331\n")
    self.RemoveArchive("calendar_dates.txt")
    self.MakeLoaderAndLoad()
    self.accumulator.AssertNoMoreExceptions()

  def testEmptyCalendarDates(self):
    self.SetArchiveContents(
        "calendar_dates.txt",
        "")
    self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("EmptyFile")
    e = self.accumulator.PopException("NoServiceExceptions")
    self.accumulator.AssertNoMoreExceptions()

  def testCalendarDatesWithHeaderOnly(self):
    self.SetArchiveContents(
        "calendar_dates.txt",
        "service_id,date,exception_type\n")
    self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("NoServiceExceptions")
    self.accumulator.AssertNoMoreExceptions()

  def testCalendarDatesWithAddedServiceException(self):
    self.SetArchiveContents(
        "calendar_dates.txt",
        "service_id,date,exception_type\n"
        "FULLW,20070101,1\n")
    self.MakeLoaderAndLoad()
    self.accumulator.AssertNoMoreExceptions()

  def testCalendarDatesWithRemovedServiceException(self):
    self.SetArchiveContents(
        "calendar_dates.txt",
        "service_id,date,exception_type\n"
        "FULLW,20070101,2\n")
    self.MakeLoaderAndLoad()
    self.accumulator.AssertNoMoreExceptions()


class ServicePeriodTestCase(util.TestCase):
  def testActive(self):
    """Test IsActiveOn and ActiveDates"""
    period = transitfeed.ServicePeriod()
    period.service_id = 'WEEKDAY'
    period.start_date = '20071226'
    period.end_date = '20071231'
    period.SetWeekdayService(True)
    period.SetDateHasService('20071230', True)
    period.SetDateHasService('20071231', False)
    period.SetDateHasService('20080102', True)
    #      December  2007
    #  Su Mo Tu We Th Fr Sa
    #  23 24 25 26 27 28 29
    #  30 31

    # Some tests have named arguments and others do not to ensure that any
    # (possibly unwanted) changes to the API get caught

    # calendar_date exceptions near start date
    self.assertFalse(period.IsActiveOn(date='20071225'))
    self.assertFalse(period.IsActiveOn(date='20071225',
                                       date_object=date(2007, 12, 25)))
    self.assertTrue(period.IsActiveOn(date='20071226'))
    self.assertTrue(period.IsActiveOn(date='20071226',
                                      date_object=date(2007, 12, 26)))

    # calendar_date exceptions near end date
    self.assertTrue(period.IsActiveOn('20071230'))
    self.assertTrue(period.IsActiveOn('20071230', date(2007, 12, 30)))
    self.assertFalse(period.IsActiveOn('20071231'))
    self.assertFalse(period.IsActiveOn('20071231', date(2007, 12, 31)))

    # date just outside range, both weekday and an exception
    self.assertFalse(period.IsActiveOn('20080101'))
    self.assertFalse(period.IsActiveOn('20080101', date(2008, 1, 1)))
    self.assertTrue(period.IsActiveOn('20080102'))
    self.assertTrue(period.IsActiveOn('20080102', date(2008, 1, 2)))

    self.assertEquals(period.ActiveDates(),
                      ['20071226', '20071227', '20071228', '20071230',
                       '20080102'])


    # Test of period without start_date, end_date
    period_dates = transitfeed.ServicePeriod()
    period_dates.SetDateHasService('20071230', True)
    period_dates.SetDateHasService('20071231', False)

    self.assertFalse(period_dates.IsActiveOn(date='20071229'))
    self.assertFalse(period_dates.IsActiveOn(date='20071229',
                                             date_object=date(2007, 12, 29)))
    self.assertTrue(period_dates.IsActiveOn('20071230'))
    self.assertTrue(period_dates.IsActiveOn('20071230', date(2007, 12, 30)))
    self.assertFalse(period_dates.IsActiveOn('20071231'))
    self.assertFalse(period_dates.IsActiveOn('20071231', date(2007, 12, 31)))
    self.assertEquals(period_dates.ActiveDates(), ['20071230'])

    # Test with an invalid ServicePeriod; one of start_date, end_date is set
    period_no_end = transitfeed.ServicePeriod()
    period_no_end.start_date = '20071226'
    self.assertFalse(period_no_end.IsActiveOn(date='20071231'))
    self.assertFalse(period_no_end.IsActiveOn(date='20071231',
                                              date_object=date(2007, 12, 31)))
    self.assertEquals(period_no_end.ActiveDates(), [])
    period_no_start = transitfeed.ServicePeriod()
    period_no_start.end_date = '20071230'
    self.assertFalse(period_no_start.IsActiveOn('20071229'))
    self.assertFalse(period_no_start.IsActiveOn('20071229', date(2007, 12, 29)))
    self.assertEquals(period_no_start.ActiveDates(), [])

    period_empty = transitfeed.ServicePeriod()
    self.assertFalse(period_empty.IsActiveOn('20071231'))
    self.assertFalse(period_empty.IsActiveOn('20071231', date(2007, 12, 31)))
    self.assertEquals(period_empty.ActiveDates(), [])


class GetServicePeriodsActiveEachDateTestCase(util.TestCase):
  def testEmpty(self):
    schedule = transitfeed.Schedule()
    self.assertEquals(
        [],
        schedule.GetServicePeriodsActiveEachDate(date(2009, 1, 1),
                                                 date(2009, 1, 1)))
    self.assertEquals(
        [(date(2008, 12, 31), []), (date(2009, 1, 1), [])],
        schedule.GetServicePeriodsActiveEachDate(date(2008, 12, 31),
                                                 date(2009, 1, 2)))
  def testOneService(self):
    schedule = transitfeed.Schedule()
    sp1 = transitfeed.ServicePeriod()
    sp1.service_id = "sp1"
    sp1.SetDateHasService("20090101")
    sp1.SetDateHasService("20090102")
    schedule.AddServicePeriodObject(sp1)
    self.assertEquals(
        [],
        schedule.GetServicePeriodsActiveEachDate(date(2009, 1, 1),
                                                 date(2009, 1, 1)))
    self.assertEquals(
        [(date(2008, 12, 31), []), (date(2009, 1, 1), [sp1])],
        schedule.GetServicePeriodsActiveEachDate(date(2008, 12, 31),
                                                 date(2009, 1, 2)))

  def testTwoService(self):
    schedule = transitfeed.Schedule()
    sp1 = transitfeed.ServicePeriod()
    sp1.service_id = "sp1"
    sp1.SetDateHasService("20081231")
    sp1.SetDateHasService("20090101")

    schedule.AddServicePeriodObject(sp1)
    sp2 = transitfeed.ServicePeriod()
    sp2.service_id = "sp2"
    sp2.SetStartDate("20081201")
    sp2.SetEndDate("20081231")
    sp2.SetWeekendService()
    sp2.SetWeekdayService()
    schedule.AddServicePeriodObject(sp2)
    self.assertEquals(
        [],
        schedule.GetServicePeriodsActiveEachDate(date(2009, 1, 1),
                                                 date(2009, 1, 1)))
    date_services = schedule.GetServicePeriodsActiveEachDate(date(2008, 12, 31),
                                                             date(2009, 1, 2))
    self.assertEquals(
        [date(2008, 12, 31), date(2009, 1, 1)], [d for d, _ in date_services])
    self.assertEquals(set([sp1, sp2]), set(date_services[0][1]))
    self.assertEquals([sp1], date_services[1][1])


class TripMemoryZipTestCase(util.MemoryZipTestCase):
  def assertLoadAndCheckExtraValues(self, schedule_file):
    """Load file-like schedule_file and check for extra trip columns."""
    load_problems = GetTestFailureProblemReporter(
        self, ("ExpirationDate", "UnrecognizedColumn"))
    loaded_schedule = transitfeed.Loader(schedule_file,
                                         problems=load_problems,
                                         extra_validation=True).Load()
    self.assertEqual("foo", loaded_schedule.GetTrip("AB1")["t_foo"])
    self.assertEqual("", loaded_schedule.GetTrip("AB2")["t_foo"])
    self.assertEqual("", loaded_schedule.GetTrip("AB1")["n_foo"])
    self.assertEqual("bar", loaded_schedule.GetTrip("AB2")["n_foo"])
    # Uncomment the following lines to print the string in testExtraFileColumn
    # print repr(zipfile.ZipFile(schedule_file).read("trips.txt"))
    # self.fail()

  def testExtraObjectAttribute(self):
    """Extra columns added to an object are preserved when writing."""
    schedule = self.MakeLoaderAndLoad()
    # Add an attribute to an existing trip
    trip1 = schedule.GetTrip("AB1")
    trip1.t_foo = "foo"
    # Make a copy of trip_id=AB1 and add an attribute before AddTripObject
    trip2 = transitfeed.Trip(field_dict=trip1)
    trip2.trip_id = "AB2"
    trip2.t_foo = ""
    trip2.n_foo = "bar"
    schedule.AddTripObject(trip2)
    trip2.AddStopTime(stop=schedule.GetStop("BULLFROG"), stop_time="09:00:00")
    trip2.AddStopTime(stop=schedule.GetStop("STAGECOACH"), stop_time="09:30:00")
    saved_schedule_file = StringIO()
    schedule.WriteGoogleTransitFeed(saved_schedule_file)
    self.accumulator.AssertNoMoreExceptions()

    self.assertLoadAndCheckExtraValues(saved_schedule_file)

  def testExtraFileColumn(self):
    """Extra columns loaded from a file are preserved when writing."""
    # Uncomment the code in assertLoadAndCheckExtraValues to generate this
    # string.
    self.SetArchiveContents(
        "trips.txt",
        "route_id,service_id,trip_id,t_foo,n_foo\n"
        "AB,FULLW,AB1,foo,\n"
        "AB,FULLW,AB2,,bar\n")
    self.AppendToArchiveContents(
        "stop_times.txt",
        "AB2,09:00:00,09:00:00,BULLFROG,1\n"
        "AB2,09:30:00,09:30:00,STAGECOACH,2\n")
    load1_problems = GetTestFailureProblemReporter(
        self, ("ExpirationDate", "UnrecognizedColumn"))
    schedule = self.MakeLoaderAndLoad(problems=load1_problems)
    saved_schedule_file = StringIO()
    schedule.WriteGoogleTransitFeed(saved_schedule_file)

    self.assertLoadAndCheckExtraValues(saved_schedule_file)


class TripValidationTestCase(ValidationTestCase):
  def runTest(self):
    trip = transitfeed.Trip()
    repr(trip)  # shouldn't crash

    schedule = self.SimpleSchedule()
    trip = transitfeed.Trip()
    repr(trip)  # shouldn't crash

    trip = transitfeed.Trip()
    trip.trip_headsign = '\xBA\xDF\x0D'  # Not valid ascii or utf8
    repr(trip)  # shouldn't crash

    trip.route_id = '054C'
    trip.service_id = 'WEEK'
    trip.trip_id = '054C-00'
    trip.trip_headsign = 'via Polish Hill'
    trip.direction_id = '0'
    trip.block_id = None
    trip.shape_id = None
    trip.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    repr(trip)  # shouldn't crash

    # missing route ID
    trip.route_id = None
    self.ValidateAndExpectMissingValue(trip, 'route_id')
    trip.route_id = '054C'

    # missing service ID
    trip.service_id = None
    self.ValidateAndExpectMissingValue(trip, 'service_id')
    trip.service_id = 'WEEK'

    # missing trip ID
    trip.trip_id = None
    self.ValidateAndExpectMissingValue(trip, 'trip_id')
    trip.trip_id = '054C-00'

    # invalid direction ID
    trip.direction_id = 'NORTH'
    self.ValidateAndExpectInvalidValue(trip, 'direction_id')
    trip.direction_id = '0'

    # AddTripObject validates that route_id, service_id, .... are found in the
    # schedule. The Validate calls made by self.Expect... above can't make this
    # check because trip is not in a schedule.
    trip.route_id = '054C-notfound'
    schedule.AddTripObject(trip, self.problems, True)
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual('route_id', e.column_name)
    self.accumulator.AssertNoMoreExceptions()
    trip.route_id = '054C'

    # Make sure calling Trip.Validate validates that route_id and service_id
    # are found in the schedule.
    trip.service_id = 'WEEK-notfound'
    trip.Validate(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual('service_id', e.column_name)
    self.accumulator.AssertNoMoreExceptions()
    trip.service_id = 'WEEK'

    trip.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()

    # expect no problems for non-overlapping periods
    trip.AddFrequency("06:00:00", "12:00:00", 600)
    trip.AddFrequency("01:00:00", "02:00:00", 1200)
    trip.AddFrequency("04:00:00", "05:00:00", 1000)
    trip.AddFrequency("12:00:00", "19:00:00", 700)
    trip.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    trip.ClearFrequencies()

    # overlapping headway periods
    trip.AddFrequency("00:00:00", "12:00:00", 600)
    trip.AddFrequency("06:00:00", "18:00:00", 1200)
    self.ValidateAndExpectOtherProblem(trip)
    trip.ClearFrequencies()
    trip.AddFrequency("12:00:00", "20:00:00", 600)
    trip.AddFrequency("06:00:00", "18:00:00", 1200)
    self.ValidateAndExpectOtherProblem(trip)
    trip.ClearFrequencies()
    trip.AddFrequency("06:00:00", "12:00:00", 600)
    trip.AddFrequency("00:00:00", "25:00:00", 1200)
    self.ValidateAndExpectOtherProblem(trip)
    trip.ClearFrequencies()
    trip.AddFrequency("00:00:00", "20:00:00", 600)
    trip.AddFrequency("06:00:00", "18:00:00", 1200)
    self.ValidateAndExpectOtherProblem(trip)
    trip.ClearFrequencies()
    self.accumulator.AssertNoMoreExceptions()


class FrequencyValidationTestCase(ValidationTestCase):
  def setUp(self):
    ValidationTestCase.setUp(self)
    self.schedule = self.SimpleSchedule()
    trip = transitfeed.Trip()
    trip.route_id = '054C'
    trip.service_id = 'WEEK'
    trip.trip_id = '054C-00'
    trip.trip_headsign = 'via Polish Hill'
    trip.direction_id = '0'
    trip.block_id = None
    trip.shape_id = None
    self.schedule.AddTripObject(trip, self.problems, True)
    self.trip = trip

  def testNonOverlappingPeriods(self):
    headway_period1 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '06:00:00',
                                                 'end_time': '12:00:00',
                                                 'headway_secs': 600,
                                                })
    headway_period2 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '01:00:00',
                                                 'end_time': '02:00:00',
                                                 'headway_secs': 1200,
                                                })
    headway_period3 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '04:00:00',
                                                 'end_time': '05:00:00',
                                                 'headway_secs': 1000,
                                                })
    headway_period4 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '12:00:00',
                                                 'end_time': '19:00:00',
                                                 'headway_secs': 700,
                                                })

    # expect no problems for non-overlapping periods
    headway_period1.AddToSchedule(self.schedule, self.problems)
    headway_period2.AddToSchedule(self.schedule, self.problems)
    headway_period3.AddToSchedule(self.schedule, self.problems)
    headway_period4.AddToSchedule(self.schedule, self.problems)
    self.trip.Validate(self.problems)
    self.accumulator.AssertNoMoreExceptions()
    self.trip.ClearFrequencies()

  def testOverlappingPeriods(self):
    # overlapping headway periods
    headway_period1 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '00:00:00',
                                                 'end_time': '12:00:00',
                                                 'headway_secs': 600,
                                                })
    headway_period2 = transitfeed.Frequency({'trip_id': '054C-00',
                                                 'start_time': '06:00:00',
                                                 'end_time': '18:00:00',
                                                 'headway_secs': 1200,
                                                })
    headway_period1.AddToSchedule(self.schedule, self.problems)
    headway_period2.AddToSchedule(self.schedule, self.problems)
    self.ValidateAndExpectOtherProblem(self.trip)
    self.trip.ClearFrequencies()
    self.accumulator.AssertNoMoreExceptions()

  def testPeriodWithInvalidTripId(self):
    headway_period1 = transitfeed.Frequency({'trip_id': 'foo',
                                                 'start_time': '00:00:00',
                                                 'end_time': '12:00:00',
                                                 'headway_secs': 600,
                                                })
    headway_period1.AddToSchedule(self.schedule, self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertEqual('trip_id', e.column_name)
    self.trip.ClearFrequencies()

  def testExactTimesStringValueConversion(self):
    # Test that no exact_times converts to 0
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800"})
    frequency.ValidateBeforeAdd(self.problems)
    self.assertEquals(frequency.ExactTimes(), 0)
    # Test that empty exact_times converts to 0
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": ""})
    frequency.ValidateBeforeAdd(self.problems)
    self.assertEquals(frequency.ExactTimes(), 0)
    # Test that exact_times "0" converts to 0
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": "0"})
    frequency.ValidateBeforeAdd(self.problems)
    self.assertEquals(frequency.ExactTimes(), 0)
    # Test that exact_times "1" converts to 1
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": "1"})
    frequency.ValidateBeforeAdd(self.problems)
    self.assertEquals(frequency.ExactTimes(), 1)
    self.accumulator.AssertNoMoreExceptions()

  def testExactTimesAsIntValue(self):
    # Test that exact_times None converts to 0
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": None})
    frequency.ValidateBeforeAdd(self.problems)
    self.assertEquals(frequency.ExactTimes(), 0)
    # Test that exact_times 0 remains 0
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": 0})
    frequency.ValidateBeforeAdd(self.problems)
    self.assertEquals(frequency.ExactTimes(), 0)
    # Test that exact_times 1 remains 1
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": 1})
    frequency.ValidateBeforeAdd(self.problems)
    self.assertEquals(frequency.ExactTimes(), 1)
    self.accumulator.AssertNoMoreExceptions()

  def testExactTimesInvalidValues(self):
    # Test that exact_times 15 raises error
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": 15})
    frequency.ValidateBeforeAdd(self.problems)
    self.accumulator.PopInvalidValue("exact_times")
    self.accumulator.AssertNoMoreExceptions()
    # Test that exact_times "yes" raises error
    frequency = transitfeed.Frequency(
        field_dict={"trip_id": "AB1,10", "start_time": "10:00:00",
                    "end_time": "23:01:00", "headway_secs": "1800",
                    "exact_times": "yes"})
    frequency.ValidateBeforeAdd(self.problems)
    self.accumulator.PopInvalidValue("exact_times")
    self.accumulator.AssertNoMoreExceptions()


class TripSequenceValidationTestCase(ValidationTestCase):
  def runTest(self):
    schedule = self.SimpleSchedule()
    # Make a new trip without any stop times
    trip = schedule.GetRoute("054C").AddTrip(trip_id="054C-00")
    stop1 = schedule.GetStop('stop1')
    stop2 = schedule.GetStop('stop2')
    stop3 = schedule.GetStop('stop3')
    stoptime1 = transitfeed.StopTime(self.problems, stop1,
                                     stop_time='12:00:00', stop_sequence=1)
    stoptime2 = transitfeed.StopTime(self.problems, stop2,
                                     stop_time='11:30:00', stop_sequence=2)
    stoptime3 = transitfeed.StopTime(self.problems, stop3,
                                     stop_time='12:15:00', stop_sequence=3)
    trip._AddStopTimeObjectUnordered(stoptime1, schedule)
    trip._AddStopTimeObjectUnordered(stoptime2, schedule)
    trip._AddStopTimeObjectUnordered(stoptime3, schedule)
    trip.Validate(self.problems)
    e = self.accumulator.PopException('OtherProblem')
    self.assertTrue(e.FormatProblem().find('Timetravel detected') != -1)
    self.assertTrue(e.FormatProblem().find('number 2 in trip 054C-00') != -1)
    self.accumulator.AssertNoMoreExceptions()


class TripServiceIDValidationTestCase(ValidationTestCase):
  def runTest(self):
    schedule = self.SimpleSchedule()
    trip1 = transitfeed.Trip()
    trip1.route_id = "054C"
    trip1.service_id = "WEEKDAY"
    trip1.trip_id = "054C_WEEK"
    self.ExpectInvalidValueInClosure(column_name="service_id",
                                     value="WEEKDAY",
                                     c=lambda: schedule.AddTripObject(trip1,
                                                            validate=True))


class TripDistanceFromStopToShapeValidationTestCase(ValidationTestCase):
  def runTest(self):
    schedule = self.SimpleSchedule()
    stop1 = schedule.stops["stop1"]
    stop2 = schedule.stops["stop2"]
    stop3 = schedule.stops["stop3"]

    # Set shape_dist_traveled
    trip = schedule.trips["CITY1"]
    trip.ClearStopTimes()
    trip.AddStopTime(stop1, stop_time="12:00:00", shape_dist_traveled=0)
    trip.AddStopTime(stop2, stop_time="12:00:45", shape_dist_traveled=500)
    trip.AddStopTime(stop3, stop_time="12:02:30", shape_dist_traveled=1500)
    trip.shape_id = "shape1"

    # Add a valid shape for the trip to the current schedule.
    shape = transitfeed.Shape("shape1")
    shape.AddPoint(48.2, 1.00, 0)
    shape.AddPoint(48.2, 1.01, 500)
    shape.AddPoint(48.2, 1.03, 1500)
    shape.max_distance = 1500
    schedule.AddShapeObject(shape)

    # The schedule should validate with no problems.
    self.ExpectNoProblems(schedule)

    # Delete a stop latitude. This should not crash validation.
    stop1.stop_lat = None
    self.ValidateAndExpectMissingValue(schedule, "stop_lat")


class TripHasStopTimeValidationTestCase(ValidationTestCase):
  def runTest(self):
    schedule = self.SimpleSchedule()
    trip = schedule.GetRoute("054C").AddTrip(trip_id="054C-00")

    # We should get an OtherProblem here because the trip has no stops.
    self.ValidateAndExpectOtherProblem(schedule)

    # It should trigger a TYPE_ERROR if there are frequencies for the trip
    # but no stops
    trip.AddFrequency("01:00:00", "12:00:00", 600)
    schedule.Validate(self.problems)
    self.accumulator.PopException('OtherProblem')  # pop first warning
    e = self.accumulator.PopException('OtherProblem')  # pop frequency error
    self.assertTrue(e.FormatProblem().find('Frequencies defined, but') != -1)
    self.assertTrue(e.FormatProblem().find('given in trip 054C-00') != -1)
    self.assertEquals(transitfeed.TYPE_ERROR, e.type)
    self.accumulator.AssertNoMoreExceptions()
    trip.ClearFrequencies()

    # Add a stop, but with only one stop passengers have nowhere to exit!
    stop = transitfeed.Stop(36.425288, -117.133162, "Demo Stop 1", "STOP1")
    schedule.AddStopObject(stop)
    trip.AddStopTime(stop, arrival_time="5:11:00", departure_time="5:12:00")
    self.ValidateAndExpectOtherProblem(schedule)

    # Add another stop, and then validation should be happy.
    stop = transitfeed.Stop(36.424288, -117.133142, "Demo Stop 2", "STOP2")
    schedule.AddStopObject(stop)
    trip.AddStopTime(stop, arrival_time="5:15:00", departure_time="5:16:00")
    schedule.Validate(self.problems)

    trip.AddStopTime(stop, stop_time="05:20:00")
    trip.AddStopTime(stop, stop_time="05:22:00")

    # Last stop must always have a time
    trip.AddStopTime(stop, arrival_secs=None, departure_secs=None)
    self.ExpectInvalidValueInClosure(
        'arrival_time', c=lambda: trip.GetEndTime(problems=self.problems))


class ShapeDistTraveledOfStopTimeValidationTestCase(ValidationTestCase):
  def runTest(self):
    schedule = self.SimpleSchedule()

    shape = transitfeed.Shape("shape_1")
    shape.AddPoint(36.425288, -117.133162, 0)
    shape.AddPoint(36.424288, -117.133142, 1)
    schedule.AddShapeObject(shape)

    trip = schedule.GetRoute("054C").AddTrip(trip_id="054C-00")
    trip.shape_id = "shape_1"

    stop = transitfeed.Stop(36.425288, -117.133162, "Demo Stop 1", "STOP1")
    schedule.AddStopObject(stop)
    trip.AddStopTime(stop, arrival_time="5:11:00", departure_time="5:12:00",
                     stop_sequence=0, shape_dist_traveled=0)
    stop = transitfeed.Stop(36.424288, -117.133142, "Demo Stop 2", "STOP2")
    schedule.AddStopObject(stop)
    trip.AddStopTime(stop, arrival_time="5:15:00", departure_time="5:16:00",
                     stop_sequence=1, shape_dist_traveled=1)

    stop = transitfeed.Stop(36.423288, -117.133122, "Demo Stop 3", "STOP3")
    schedule.AddStopObject(stop)
    trip.AddStopTime(stop, arrival_time="5:18:00", departure_time="5:19:00",
                     stop_sequence=2, shape_dist_traveled=2)
    self.accumulator.AssertNoMoreExceptions()
    schedule.Validate(self.problems)
    e = self.accumulator.PopException('OtherProblem')
    self.assertMatchesRegex('shape_dist_traveled=2', e.FormatProblem())
    self.accumulator.AssertNoMoreExceptions()

    # Error if the distance decreases.
    shape.AddPoint(36.421288, -117.133132, 2)
    stop = transitfeed.Stop(36.421288, -117.133122, "Demo Stop 4", "STOP4")
    schedule.AddStopObject(stop)
    stoptime = transitfeed.StopTime(self.problems, stop,
                                    arrival_time="5:29:00",
                                    departure_time="5:29:00", stop_sequence=3,
                                    shape_dist_traveled=1.7)
    trip.AddStopTimeObject(stoptime, schedule=schedule)
    self.accumulator.AssertNoMoreExceptions()
    schedule.Validate(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('stop STOP4 has', e.FormatProblem())
    self.assertMatchesRegex('shape_dist_traveled=1.7', e.FormatProblem())
    self.assertMatchesRegex('distance was 2.0.', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_ERROR)
    self.accumulator.AssertNoMoreExceptions()

    # Warning if distance remains the same between two stop_times
    stoptime.shape_dist_traveled = 2.0
    trip.ReplaceStopTimeObject(stoptime, schedule=schedule)
    schedule.Validate(self.problems)
    e = self.accumulator.PopException('InvalidValue')
    self.assertMatchesRegex('stop STOP4 has', e.FormatProblem())
    self.assertMatchesRegex('shape_dist_traveled=2.0', e.FormatProblem())
    self.assertMatchesRegex('distance was 2.0.', e.FormatProblem())
    self.assertEqual(e.type, transitfeed.TYPE_WARNING)
    self.accumulator.AssertNoMoreExceptions()


class StopMatchWithShapeTestCase(ValidationTestCase):
  def runTest(self):
    schedule = self.SimpleSchedule()

    shape = transitfeed.Shape("shape_1")
    shape.AddPoint(36.425288, -117.133162, 0)
    shape.AddPoint(36.424288, -117.143142, 1)
    schedule.AddShapeObject(shape)

    trip = schedule.GetRoute("054C").AddTrip(trip_id="054C-00")
    trip.shape_id = "shape_1"

    # Stop 1 is only 600 meters away from shape, which is allowed.
    stop = transitfeed.Stop(36.425288, -117.139162, "Demo Stop 1", "STOP1")
    schedule.AddStopObject(stop)
    trip.AddStopTime(stop, arrival_time="5:11:00", departure_time="5:12:00",
                     stop_sequence=0, shape_dist_traveled=0)
    # Stop 2 is more than 1000 meters away from shape, which is not allowed.
    stop = transitfeed.Stop(36.424288, -117.158142, "Demo Stop 2", "STOP2")
    schedule.AddStopObject(stop)
    trip.AddStopTime(stop, arrival_time="5:15:00", departure_time="5:16:00",
                     stop_sequence=1, shape_dist_traveled=1)

    schedule.Validate(self.problems)
    e = self.accumulator.PopException('StopTooFarFromShapeWithDistTraveled')
    self.assertTrue(e.FormatProblem().find('Demo Stop 2') != -1)
    self.assertTrue(e.FormatProblem().find('1344 meters away') != -1)
    self.accumulator.AssertNoMoreExceptions()


class TripAddStopTimeObjectTestCase(ValidationTestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(problem_reporter=self.problems)
    schedule.AddAgency("\xc8\x8b Fly Agency", "http://iflyagency.com",
                       "America/Los_Angeles")
    service_period = schedule.GetDefaultServicePeriod().SetDateHasService('20070101')
    stop1 = schedule.AddStop(lng=140, lat=48.2, name="Stop 1")
    stop2 = schedule.AddStop(lng=140.001, lat=48.201, name="Stop 2")
    route = schedule.AddRoute("B", "Beta", "Bus")
    trip = route.AddTrip(schedule, "bus trip")
    trip.AddStopTimeObject(transitfeed.StopTime(self.problems, stop1,
                                                arrival_secs=10,
                                                departure_secs=10),
                           schedule=schedule, problems=self.problems)
    trip.AddStopTimeObject(transitfeed.StopTime(self.problems, stop2,
                                                arrival_secs=20,
                                                departure_secs=20),
                           schedule=schedule, problems=self.problems)
    # TODO: Factor out checks or use mock problems object
    self.ExpectOtherProblemInClosure(lambda:
      trip.AddStopTimeObject(transitfeed.StopTime(self.problems, stop1,
                                                  arrival_secs=15,
                                                  departure_secs=15),
                             schedule=schedule, problems=self.problems))
    trip.AddStopTimeObject(transitfeed.StopTime(self.problems, stop1),
                           schedule=schedule, problems=self.problems)
    self.ExpectOtherProblemInClosure(lambda:
        trip.AddStopTimeObject(transitfeed.StopTime(self.problems, stop1,
                                                    arrival_secs=15,
                                                    departure_secs=15),
                               schedule=schedule, problems=self.problems))
    trip.AddStopTimeObject(transitfeed.StopTime(self.problems, stop1,
                                                arrival_secs=30,
                                                departure_secs=30),
                           schedule=schedule, problems=self.problems)
    self.accumulator.AssertNoMoreExceptions()

class DuplicateTripTestCase(ValidationTestCase):
  def runTest(self):

    schedule = transitfeed.Schedule(self.problems)
    schedule._check_duplicate_trips = True;

    agency = transitfeed.Agency('Demo agency', 'http://google.com',
                                'America/Los_Angeles', 'agency1')
    schedule.AddAgencyObject(agency)

    service = schedule.GetDefaultServicePeriod()
    service.SetDateHasService('20070101')

    route1 = transitfeed.Route('Route1', 'route 1', 3, 'route_1', 'agency1')
    schedule.AddRouteObject(route1)
    route2 = transitfeed.Route('Route2', 'route 2', 3, 'route_2', 'agency1')
    schedule.AddRouteObject(route2)

    trip1 = transitfeed.Trip()
    trip1.route_id = 'route_1'
    trip1.trip_id = 't1'
    trip1.trip_headsign = 'via Polish Hill'
    trip1.direction_id = '0'
    trip1.service_id = service.service_id
    schedule.AddTripObject(trip1)

    trip2 = transitfeed.Trip()
    trip2.route_id = 'route_2'
    trip2.trip_id = 't2'
    trip2.trip_headsign = 'New'
    trip2.direction_id = '0'
    trip2.service_id = service.service_id
    schedule.AddTripObject(trip2)

    trip3 = transitfeed.Trip()
    trip3.route_id = 'route_1'
    trip3.trip_id = 't3'
    trip3.trip_headsign = 'New Demo'
    trip3.direction_id = '0'
    trip3.service_id = service.service_id
    schedule.AddTripObject(trip3)

    stop1 = transitfeed.Stop(36.425288, -117.139162, "Demo Stop 1", "STOP1")
    schedule.AddStopObject(stop1)
    trip1.AddStopTime(stop1, arrival_time="5:11:00", departure_time="5:12:00",
                     stop_sequence=0, shape_dist_traveled=0)
    trip2.AddStopTime(stop1, arrival_time="5:11:00", departure_time="5:12:00",
                     stop_sequence=0, shape_dist_traveled=0)
    trip3.AddStopTime(stop1, arrival_time="6:11:00", departure_time="6:12:00",
                     stop_sequence=0, shape_dist_traveled=0)

    stop2 = transitfeed.Stop(36.424288, -117.158142, "Demo Stop 2", "STOP2")
    schedule.AddStopObject(stop2)
    trip1.AddStopTime(stop2, arrival_time="5:15:00", departure_time="5:16:00",
                      stop_sequence=1, shape_dist_traveled=1)
    trip2.AddStopTime(stop2, arrival_time="5:25:00", departure_time="5:26:00",
                      stop_sequence=1, shape_dist_traveled=1)
    trip3.AddStopTime(stop2, arrival_time="6:15:00", departure_time="6:16:00",
                      stop_sequence=1, shape_dist_traveled=1)

    schedule.Validate(self.problems)
    e = self.accumulator.PopException('DuplicateTrip')
    self.assertTrue(e.FormatProblem().find('t1 of route') != -1)
    self.assertTrue(e.FormatProblem().find('t2 of route') != -1)
    self.accumulator.AssertNoMoreExceptions()


class StopBelongsToBothSubwayAndBusTestCase(ValidationTestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(self.problems)

    schedule.AddAgency("Demo Agency", "http://example.com",
                        "America/Los_Angeles")
    route1 = schedule.AddRoute(short_name="route1", long_name="route_1",
                               route_type=3)
    route2 = schedule.AddRoute(short_name="route2", long_name="route_2",
                               route_type=1)

    service = schedule.GetDefaultServicePeriod()
    service.SetDateHasService("20070101")

    trip1 = route1.AddTrip(schedule, "trip1", service, "t1")
    trip2 = route2.AddTrip(schedule, "trip2", service, "t2")

    stop1 = schedule.AddStop(36.425288, -117.133162, "stop1")
    stop2 = schedule.AddStop(36.424288, -117.133142, "stop2")
    stop3 = schedule.AddStop(36.423288, -117.134142, "stop3")

    trip1.AddStopTime(stop1, arrival_time="5:11:00", departure_time="5:12:00")
    trip1.AddStopTime(stop2, arrival_time="5:21:00", departure_time="5:22:00")

    trip2.AddStopTime(stop1, arrival_time="6:11:00", departure_time="6:12:00")
    trip2.AddStopTime(stop3, arrival_time="6:21:00", departure_time="6:22:00")

    schedule.Validate(self.problems)
    e = self.accumulator.PopException("StopWithMultipleRouteTypes")
    self.assertTrue(e.FormatProblem().find("Stop stop1") != -1)
    self.assertTrue(e.FormatProblem().find("subway (ID=1)") != -1)
    self.assertTrue(e.FormatProblem().find("bus line (ID=0)") != -1)
    self.accumulator.AssertNoMoreExceptions()


class TripReplaceStopTimeObjectTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule()
    schedule.AddAgency("\xc8\x8b Fly Agency", "http://iflyagency.com",
                       "America/Los_Angeles")
    service_period = \
      schedule.GetDefaultServicePeriod().SetDateHasService('20070101')
    stop1 = schedule.AddStop(lng=140, lat=48.2, name="Stop 1")
    route = schedule.AddRoute("B", "Beta", "Bus")
    trip = route.AddTrip(schedule, "bus trip")
    stoptime = transitfeed.StopTime(transitfeed.default_problem_reporter, stop1,
                                    arrival_secs=10,
                                    departure_secs=10)
    trip.AddStopTimeObject(stoptime, schedule=schedule)
    stoptimes = trip.GetStopTimes()
    stoptime.departure_secs = 20
    trip.ReplaceStopTimeObject(stoptime, schedule=schedule)
    stoptimes = trip.GetStopTimes()
    self.assertEqual(len(stoptimes), 1)
    self.assertEqual(stoptimes[0].departure_secs, 20)

    unknown_stop = schedule.AddStop(lng=140, lat=48.2, name="unknown")
    unknown_stoptime = transitfeed.StopTime(
        transitfeed.default_problem_reporter, unknown_stop,
        arrival_secs=10,
        departure_secs=10)
    unknown_stoptime.stop_sequence = 5
    # Attempting to replace a non-existent StopTime raises an error
    self.assertRaises(transitfeed.Error, trip.ReplaceStopTimeObject,
        unknown_stoptime, schedule=schedule)

class TripStopTimeAccessorsTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    schedule.NewDefaultAgency(agency_name="Test Agency",
                              agency_url="http://example.com",
                              agency_timezone="America/Los_Angeles")
    route = schedule.AddRoute(short_name="54C", long_name="Polish Hill",
                              route_type=3)

    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetDateHasService("20070101")

    trip = route.AddTrip(schedule, 'via Polish Hill')

    stop1 = schedule.AddStop(36.425288, -117.133162, "Demo Stop 1")
    stop2 = schedule.AddStop(36.424288, -117.133142, "Demo Stop 2")

    trip.AddStopTime(stop1, arrival_time="5:11:00", departure_time="5:12:00")
    trip.AddStopTime(stop2, arrival_time="5:15:00", departure_time="5:16:00")

    # Add some more stop times and test GetEndTime does the correct thing
    self.assertEqual(transitfeed.FormatSecondsSinceMidnight(
        trip.GetStartTime()), "05:11:00")
    self.assertEqual(transitfeed.FormatSecondsSinceMidnight(
        trip.GetEndTime()), "05:16:00")

    trip.AddStopTime(stop1, stop_time="05:20:00")
    self.assertEqual(transitfeed.FormatSecondsSinceMidnight(trip.GetEndTime()),
                     "05:20:00")

    trip.AddStopTime(stop2, stop_time="05:22:00")
    self.assertEqual(transitfeed.FormatSecondsSinceMidnight(trip.GetEndTime()),
                     "05:22:00")
    self.assertEqual(len(trip.GetStopTimesTuples()), 4)
    self.assertEqual(trip.GetStopTimesTuples()[0], (trip.trip_id, "05:11:00",
                                                    "05:12:00", stop1.stop_id,
                                                    1, '', '', '', ''))
    self.assertEqual(trip.GetStopTimesTuples()[3], (trip.trip_id, "05:22:00",
                                                    "05:22:00", stop2.stop_id,
                                                    4, '', '', '', ''))

class TripClearStopTimesTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    schedule.NewDefaultAgency(agency_name="Test Agency",
                              agency_timezone="America/Los_Angeles")
    route = schedule.AddRoute(short_name="54C", long_name="Hill", route_type=3)
    schedule.GetDefaultServicePeriod().SetDateHasService("20070101")
    stop1 = schedule.AddStop(36, -117.1, "Demo Stop 1")
    stop2 = schedule.AddStop(36, -117.2, "Demo Stop 2")
    stop3 = schedule.AddStop(36, -117.3, "Demo Stop 3")

    trip = route.AddTrip(schedule, "via Polish Hill")
    trip.ClearStopTimes()
    self.assertFalse(trip.GetStopTimes())
    trip.AddStopTime(stop1, stop_time="5:11:00")
    self.assertTrue(trip.GetStopTimes())
    trip.ClearStopTimes()
    self.assertFalse(trip.GetStopTimes())
    trip.AddStopTime(stop3, stop_time="4:00:00")  # Can insert earlier time
    trip.AddStopTime(stop2, stop_time="4:15:00")
    trip.AddStopTime(stop1, stop_time="4:21:00")
    old_stop_times = trip.GetStopTimes()
    self.assertTrue(old_stop_times)
    trip.ClearStopTimes()
    self.assertFalse(trip.GetStopTimes())
    for st in old_stop_times:
      trip.AddStopTimeObject(st)
    self.assertEqual(trip.GetStartTime(), 4 * 3600)
    self.assertEqual(trip.GetEndTime(), 4 * 3600 + 21 * 60)


class BasicParsingTestCase(util.TestCase):
  """Checks that we're getting the number of child objects that we expect."""
  def assertLoadedCorrectly(self, schedule):
    """Check that the good_feed looks correct"""
    self.assertEqual(1, len(schedule._agencies))
    self.assertEqual(5, len(schedule.routes))
    self.assertEqual(2, len(schedule.service_periods))
    self.assertEqual(10, len(schedule.stops))
    self.assertEqual(11, len(schedule.trips))
    self.assertEqual(0, len(schedule.fare_zones))

  def assertLoadedStopTimesCorrectly(self, schedule):
    self.assertEqual(5, len(schedule.GetTrip('CITY1').GetStopTimes()))
    self.assertEqual('to airport', schedule.GetTrip('STBA').GetStopTimes()[0].stop_headsign)
    self.assertEqual(2, schedule.GetTrip('CITY1').GetStopTimes()[1].pickup_type)
    self.assertEqual(3, schedule.GetTrip('CITY1').GetStopTimes()[1].drop_off_type)

  def test_MemoryDb(self):
    loader = transitfeed.Loader(
      DataPath('good_feed.zip'),
      problems=GetTestFailureProblemReporter(self),
      extra_validation=True,
      memory_db=True)
    schedule = loader.Load()
    self.assertLoadedCorrectly(schedule)
    self.assertLoadedStopTimesCorrectly(schedule)

  def test_TemporaryFile(self):
    loader = transitfeed.Loader(
      DataPath('good_feed.zip'),
      problems=GetTestFailureProblemReporter(self),
      extra_validation=True,
      memory_db=False)
    schedule = loader.Load()
    self.assertLoadedCorrectly(schedule)
    self.assertLoadedStopTimesCorrectly(schedule)

  def test_NoLoadStopTimes(self):
    problems = GetTestFailureProblemReporter(
        self, ignore_types=("ExpirationDate", "UnusedStop", "OtherProblem"))
    loader = transitfeed.Loader(
      DataPath('good_feed.zip'),
      problems=problems,
      extra_validation=True,
      load_stop_times=False)
    schedule = loader.Load()
    self.assertLoadedCorrectly(schedule)
    self.assertEqual(0, len(schedule.GetTrip('CITY1').GetStopTimes()))


class RepeatedRouteNameTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectInvalidValue('repeated_route_name', 'route_long_name')


class InvalidRouteAgencyTestCase(LoadTestCase):
  def runTest(self):
    self.Load('invalid_route_agency')
    self.accumulator.PopInvalidValue("agency_id", "routes.txt")
    self.accumulator.PopInvalidValue("route_id", "trips.txt")
    self.accumulator.AssertNoMoreExceptions()


class UndefinedStopAgencyTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectInvalidValue('undefined_stop', 'stop_id')


class SameShortLongNameTestCase(LoadTestCase):
  def runTest(self):
    self.ExpectInvalidValue('same_short_long_name', 'route_long_name')


class UnusedStopAgencyTestCase(LoadTestCase):
  def runTest(self):
    self.Load('unused_stop'),
    e = self.accumulator.PopException("UnusedStop")
    self.assertEqual("Bogus Stop (Demo)", e.stop_name)
    self.assertEqual("BOGUS", e.stop_id)
    self.accumulator.AssertNoMoreExceptions()



class OnlyCalendarDatesTestCase(LoadTestCase):
  def runTest(self):
    self.Load('only_calendar_dates'),
    self.accumulator.AssertNoMoreExceptions()


class DuplicateServiceIdDateWarningTestCase(util.MemoryZipTestCase):
  def runTest(self):
    # Two lines with the same value of service_id and date.
    # Test for the warning.
    self.SetArchiveContents(
        'calendar_dates.txt',
        'service_id,date,exception_type\n'
        'FULLW,20100604,1\n'
        'FULLW,20100604,2\n')
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException('DuplicateID')
    self.assertEquals('(service_id, date)', e.column_name)
    self.assertEquals('(FULLW, 20100604)', e.value)


class AddStopTimeParametersTestCase(util.TestCase):
  def runTest(self):
    problem_reporter = GetTestFailureProblemReporter(self)
    schedule = transitfeed.Schedule(problem_reporter=problem_reporter)
    route = schedule.AddRoute(short_name="10", long_name="", route_type="Bus")
    stop = schedule.AddStop(40, -128, "My stop")
    # Stop must be added to schedule so that the call
    # AddStopTime -> AddStopTimeObject -> GetStopTimes -> GetStop can work
    trip = transitfeed.Trip()
    trip.route_id = route.route_id
    trip.service_id = schedule.GetDefaultServicePeriod().service_id
    trip.trip_id = "SAMPLE_TRIP"
    schedule.AddTripObject(trip)

    # First stop must have time
    trip.AddStopTime(stop, arrival_secs=300, departure_secs=360)
    trip.AddStopTime(stop)
    trip.AddStopTime(stop, arrival_time="00:07:00", departure_time="00:07:30")
    trip.Validate(problem_reporter)


class ExpirationDateTestCase(util.TestCase):
  def runTest(self):
    accumulator = RecordingProblemAccumulator(self, ("NoServiceExceptions"))
    problems = transitfeed.ProblemReporter(accumulator)
    schedule = transitfeed.Schedule(problem_reporter=problems)

    now = time.mktime(time.localtime())
    seconds_per_day = 60 * 60 * 24
    two_weeks_ago = time.localtime(now - 14 * seconds_per_day)
    two_weeks_from_now = time.localtime(now + 14 * seconds_per_day)
    two_months_from_now = time.localtime(now + 60 * seconds_per_day)
    date_format = "%Y%m%d"

    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetWeekdayService(True)
    service_period.SetStartDate("20070101")

    service_period.SetEndDate(time.strftime(date_format, two_months_from_now))
    schedule.Validate()  # should have no problems
    accumulator.AssertNoMoreExceptions()

    service_period.SetEndDate(time.strftime(date_format, two_weeks_from_now))
    schedule.Validate()
    e = accumulator.PopException('ExpirationDate')
    self.assertTrue(e.FormatProblem().index('will soon expire'))
    accumulator.AssertNoMoreExceptions()

    service_period.SetEndDate(time.strftime(date_format, two_weeks_ago))
    schedule.Validate()
    e = accumulator.PopException('ExpirationDate')
    self.assertTrue(e.FormatProblem().index('expired'))
    accumulator.AssertNoMoreExceptions()


class FutureServiceStartDateTestCase(util.TestCase):
  def runTest(self):
    accumulator = RecordingProblemAccumulator(self)
    problems = transitfeed.ProblemReporter(accumulator)
    schedule = transitfeed.Schedule(problem_reporter=problems)

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    two_months_from_today = today + datetime.timedelta(days=60)

    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetWeekdayService(True)
    service_period.SetWeekendService(True)
    service_period.SetEndDate(two_months_from_today.strftime("%Y%m%d"))

    service_period.SetStartDate(yesterday.strftime("%Y%m%d"))
    schedule.Validate()
    accumulator.AssertNoMoreExceptions()

    service_period.SetStartDate(today.strftime("%Y%m%d"))
    schedule.Validate()
    accumulator.AssertNoMoreExceptions()

    service_period.SetStartDate(tomorrow.strftime("%Y%m%d"))
    schedule.Validate()
    accumulator.PopException('FutureService')
    accumulator.AssertNoMoreExceptions()


class CalendarTxtIntegrationTestCase(util.MemoryZipTestCase):
  def testBadEndDateFormat(self):
    # A badly formatted end_date used to generate an InvalidValue report from
    # Schedule.Validate and ServicePeriod.Validate. Test for the bug.
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "FULLW,1,1,1,1,1,1,1,20070101,20101232\n"
        "WE,0,0,0,0,0,1,1,20070101,20101231\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopInvalidValue('end_date')
    self.accumulator.AssertNoMoreExceptions()

  def testBadStartDateFormat(self):
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "FULLW,1,1,1,1,1,1,1,200701xx,20101231\n"
        "WE,0,0,0,0,0,1,1,20070101,20101231\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopInvalidValue('start_date')
    self.accumulator.AssertNoMoreExceptions()

  def testNoStartDateAndEndDate(self):
    """Regression test for calendar.txt with empty start_date and end_date.

    See http://code.google.com/p/googletransitdatafeed/issues/detail?id=41
    """
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "FULLW,1,1,1,1,1,1,1,    ,\t\n"
        "WE,0,0,0,0,0,1,1,20070101,20101231\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("MissingValue")
    self.assertEquals(2, e.row_num)
    self.assertEquals("start_date", e.column_name)
    e = self.accumulator.PopException("MissingValue")
    self.assertEquals(2, e.row_num)
    self.assertEquals("end_date", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testNoStartDateAndBadEndDate(self):
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "FULLW,1,1,1,1,1,1,1,,abc\n"
        "WE,0,0,0,0,0,1,1,20070101,20101231\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("MissingValue")
    self.assertEquals(2, e.row_num)
    self.assertEquals("start_date", e.column_name)
    e = self.accumulator.PopInvalidValue("end_date")
    self.assertEquals(2, e.row_num)
    self.accumulator.AssertNoMoreExceptions()

  def testMissingEndDateColumn(self):
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date\n"
        "FULLW,1,1,1,1,1,1,1,20070101\n"
        "WE,0,0,0,0,0,1,1,20070101\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopException("MissingColumn")
    self.assertEquals("end_date", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testDateOutsideValidRange(self):
    """ start_date and end_date values must be in [1900,2100] """
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "FULLW,1,1,1,1,1,1,1,20070101,21101231\n"
        "WE,0,0,0,0,0,1,1,18990101,20101231\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopDateOutsideValidRange('start_date', 'calendar.txt')
    self.assertEquals('18990101', e.value)
    e = self.accumulator.PopDateOutsideValidRange('end_date', 'calendar.txt')
    self.assertEquals('21101231', e.value)
    self.accumulator.AssertNoMoreExceptions()


class CalendarDatesTxtIntegrationTestCase(util.MemoryZipTestCase):
  def testDateOutsideValidRange(self):
    """ exception date values in must be in [1900,2100] """
    self.SetArchiveContents("calendar_dates.txt",
        "service_id,date,exception_type\n"
        "WE,18990815,2\n")
    schedule = self.MakeLoaderAndLoad()
    e = self.accumulator.PopDateOutsideValidRange('date', 'calendar_dates.txt')
    self.assertEquals('18990815', e.value)
    self.accumulator.AssertNoMoreExceptions()


class ScheduleStartAndExpirationDatesTestCase(util.MemoryZipTestCase):

  # Remove "ExpirationDate" from the accumulator _IGNORE_TYPES to get the
  # expiration errors.
  _IGNORE_TYPES = util.MemoryZipTestCase._IGNORE_TYPES[:]
  _IGNORE_TYPES.remove("ExpirationDate")

  # Init dates to be close to now
  now = time.mktime(time.localtime())
  seconds_per_day = 60 * 60 * 24
  date_format = "%Y%m%d"
  two_weeks_ago = time.strftime(date_format,
                                time.localtime(now - 14 * seconds_per_day))
  one_week_ago = time.strftime(date_format,
                               time.localtime(now - 7 * seconds_per_day))
  one_week = time.strftime(date_format,
                            time.localtime(now + 7 * seconds_per_day))
  two_weeks = time.strftime(date_format,
                            time.localtime(now + 14 * seconds_per_day))
  two_months = time.strftime(date_format,
                             time.localtime(now + 60 * seconds_per_day))

  def prepareArchiveContents(self, calendar_start, calendar_end,
                             exception_date, feed_info_start, feed_info_end):
    self.SetArchiveContents(
        "calendar.txt",
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
        "start_date,end_date\n"
        "FULLW,1,1,1,1,1,1,1,%s,%s\n"
        "WE,0,0,0,0,0,1,1,%s,%s\n" % (calendar_start, calendar_end,
                                      calendar_start, calendar_end))
    self.SetArchiveContents(
        "calendar_dates.txt",
        "service_id,date,exception_type\n"
        "FULLW,%s,1\n" % (exception_date))
    from_column = ""
    if feed_info_start:
      from_column = ",feed_start_date"
      feed_info_start = "," + feed_info_start
    until_column = ""
    if feed_info_end:
      until_column = ",feed_end_date"
      feed_info_end = "," + feed_info_end
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang%s%s\n"
        "DTA,http://google.com,en%s%s" % (
          from_column, until_column, feed_info_start, feed_info_end))

  def testNoErrors(self):
    self.prepareArchiveContents(
        self.two_weeks_ago, self.two_months, # calendar
        self.two_weeks,                      # calendar_dates
        "", "")                              # feed_info
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testExpirationDateCausedByServicePeriod(self):
    # test with no validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.two_weeks_ago, self.two_weeks, # calendar
        self.one_week,                      # calendar_dates
        "", "")                             # feed_info
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("ExpirationDate")
    self.assertTrue("calendar.txt" in e.expiration_origin_file)
    self.accumulator.AssertNoMoreExceptions()
    # test with good validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.two_weeks_ago, self.two_weeks,  # calendar
        self.one_week,                       # calendar_dates
        self.two_weeks_ago, self.two_months) # feed_info
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testFutureServiceCausedByServicePeriod(self):
    # test with no validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.one_week, self.two_months, # calendar
        self.two_weeks,                 # calendar_dates
        "", "")                         # feed_info
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("FutureService")
    self.assertTrue("calendar.txt" in e.start_date_origin_file)
    self.accumulator.AssertNoMoreExceptions()
    # Test with good validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.one_week, self.two_months,      # calendar
        self.two_weeks,                      # calendar_dates
        self.two_weeks_ago, self.two_months) # feed_info
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testExpirationDateCausedByServicePeriodDateException(self):
    # Test with no validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.two_weeks_ago, self.one_week, # calendar
        self.two_weeks,                    # calendar_dates
        "", "")                            # feed_info
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("ExpirationDate")
    self.assertTrue("calendar_dates.txt" in e.expiration_origin_file)
    self.accumulator.AssertNoMoreExceptions()
    # Test with good validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.two_weeks_ago, self.one_week,   # calendar
        self.two_weeks,                      # calendar_dates
        self.two_weeks_ago, self.two_months) # feed_info
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testFutureServiceCausedByServicePeriodDateException(self):
    # Test with no validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.two_weeks, self.two_months, # calendar
        self.one_week,                   # calendar_dates
        "", "")                          # feed_info
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("FutureService")
    self.assertTrue("calendar_dates.txt" in e.start_date_origin_file)
    self.accumulator.AssertNoMoreExceptions()
    # Test with good validity dates specified in feed_info.txt
    self.prepareArchiveContents(
        self.two_weeks, self.two_months,     # calendar
        self.one_week,                       # calendar_dates
        self.two_weeks_ago, self.two_months) # feed_info
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testExpirationDateCausedByFeedInfo(self):
    self.prepareArchiveContents(
        self.two_weeks_ago, self.two_months, # calendar
        self.one_week,                       # calendar_dates
        "", self.two_weeks)                  # feed_info
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("ExpirationDate")
    self.assertTrue("feed_info.txt" in e.expiration_origin_file)
    self.accumulator.AssertNoMoreExceptions()

  def testFutureServiceCausedByFeedInfo(self):
    self.prepareArchiveContents(
        self.two_weeks_ago, self.two_months, # calendar
        self.one_week_ago,                   # calendar_dates
        self.one_week, self.two_months)      # feed_info
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("FutureService")
    self.assertTrue("feed_info.txt" in e.start_date_origin_file)
    self.accumulator.AssertNoMoreExceptions()


class DuplicateTripIDValidationTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    schedule.AddAgency("Sample Agency", "http://example.com",
                       "America/Los_Angeles")
    route = transitfeed.Route()
    route.route_id = "SAMPLE_ID"
    route.route_type = 3
    route.route_long_name = "Sample Route"
    schedule.AddRouteObject(route)

    service_period = transitfeed.ServicePeriod("WEEK")
    service_period.SetStartDate("20070101")
    service_period.SetEndDate("20071231")
    service_period.SetWeekdayService(True)
    schedule.AddServicePeriodObject(service_period)

    trip1 = transitfeed.Trip()
    trip1.route_id = "SAMPLE_ID"
    trip1.service_id = "WEEK"
    trip1.trip_id = "SAMPLE_TRIP"
    schedule.AddTripObject(trip1)

    trip2 = transitfeed.Trip()
    trip2.route_id = "SAMPLE_ID"
    trip2.service_id = "WEEK"
    trip2.trip_id = "SAMPLE_TRIP"
    try:
      schedule.AddTripObject(trip2)
      self.fail("Expected Duplicate ID validation failure")
    except transitfeed.DuplicateID, e:
      self.assertEqual("trip_id", e.column_name)
      self.assertEqual("SAMPLE_TRIP", e.value)


class DuplicateStopValidationTestCase(ValidationTestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(problem_reporter=self.problems)
    schedule.AddAgency("Sample Agency", "http://example.com",
                       "America/Los_Angeles")
    route = transitfeed.Route()
    route.route_id = "SAMPLE_ID"
    route.route_type = 3
    route.route_long_name = "Sample Route"
    schedule.AddRouteObject(route)

    service_period = transitfeed.ServicePeriod("WEEK")
    service_period.SetStartDate("20070101")
    service_period.SetEndDate("20071231")
    service_period.SetWeekdayService(True)
    schedule.AddServicePeriodObject(service_period)

    trip = transitfeed.Trip()
    trip.route_id = "SAMPLE_ID"
    trip.service_id = "WEEK"
    trip.trip_id = "SAMPLE_TRIP"
    schedule.AddTripObject(trip)

    stop1 = transitfeed.Stop()
    stop1.stop_id = "STOP1"
    stop1.stop_name = "Stop 1"
    stop1.stop_lat = 78.243587
    stop1.stop_lon = 32.258937
    schedule.AddStopObject(stop1)
    trip.AddStopTime(stop1, arrival_time="12:00:00", departure_time="12:00:00")

    stop2 = transitfeed.Stop()
    stop2.stop_id = "STOP2"
    stop2.stop_name = "Stop 2"
    stop2.stop_lat = 78.253587
    stop2.stop_lon = 32.258937
    schedule.AddStopObject(stop2)
    trip.AddStopTime(stop2, arrival_time="12:05:00", departure_time="12:05:00")
    schedule.Validate()

    stop3 = transitfeed.Stop()
    stop3.stop_id = "STOP3"
    stop3.stop_name = "Stop 3"
    stop3.stop_lat = 78.243587
    stop3.stop_lon = 32.268937
    schedule.AddStopObject(stop3)
    trip.AddStopTime(stop3, arrival_time="12:10:00", departure_time="12:10:00")
    schedule.Validate()
    self.accumulator.AssertNoMoreExceptions()

    stop4 = transitfeed.Stop()
    stop4.stop_id = "STOP4"
    stop4.stop_name = "Stop 4"
    stop4.stop_lat = 78.243588
    stop4.stop_lon = 32.268936
    schedule.AddStopObject(stop4)
    trip.AddStopTime(stop4, arrival_time="12:15:00", departure_time="12:15:00")
    schedule.Validate()
    e = self.accumulator.PopException('StopsTooClose')
    self.accumulator.AssertNoMoreExceptions()


class TempFileTestCaseBase(util.TestCase):
  """
  Subclass of TestCase which sets self.tempfilepath to a valid temporary zip
  file name and removes the file if it exists when the test is done.
  """
  def setUp(self):
    (fd, self.tempfilepath) = tempfile.mkstemp(".zip")
    # Open file handle causes an exception during remove in Windows
    os.close(fd)

  def tearDown(self):
    if os.path.exists(self.tempfilepath):
      os.remove(self.tempfilepath)


class MinimalWriteTestCase(TempFileTestCaseBase):
  """
  This test case simply constructs an incomplete feed with very few
  fields set and ensures that there are no exceptions when writing it out.

  This is very similar to TransitFeedSampleCodeTestCase below, but that one
  will no doubt change as the sample code is altered.
  """
  def runTest(self):
    schedule = transitfeed.Schedule()
    schedule.AddAgency("Sample Agency", "http://example.com",
                       "America/Los_Angeles")
    route = transitfeed.Route()
    route.route_id = "SAMPLE_ID"
    route.route_type = 3
    route.route_short_name = "66"
    route.route_long_name = "Sample Route acute letter e\202"
    schedule.AddRouteObject(route)

    service_period = transitfeed.ServicePeriod("WEEK")
    service_period.SetStartDate("20070101")
    service_period.SetEndDate("20071231")
    service_period.SetWeekdayService(True)
    schedule.AddServicePeriodObject(service_period)

    trip = transitfeed.Trip()
    trip.route_id = "SAMPLE_ID"
    trip.service_period = service_period
    trip.trip_id = "SAMPLE_TRIP"
    schedule.AddTripObject(trip)

    stop1 = transitfeed.Stop()
    stop1.stop_id = "STOP1"
    stop1.stop_name = u'Stop 1 acute letter e\202'
    stop1.stop_lat = 78.243587
    stop1.stop_lon = 32.258937
    schedule.AddStopObject(stop1)
    trip.AddStopTime(stop1, arrival_time="12:00:00", departure_time="12:00:00")

    stop2 = transitfeed.Stop()
    stop2.stop_id = "STOP2"
    stop2.stop_name = "Stop 2"
    stop2.stop_lat = 78.253587
    stop2.stop_lon = 32.258937
    schedule.AddStopObject(stop2)
    trip.AddStopTime(stop2, arrival_time="12:05:00", departure_time="12:05:00")

    schedule.Validate()
    schedule.WriteGoogleTransitFeed(self.tempfilepath)


class TransitFeedSampleCodeTestCase(util.TestCase):
  """
  This test should simply contain the sample code printed on the page:
  http://code.google.com/p/googletransitdatafeed/wiki/TransitFeed
  to ensure that it doesn't cause any exceptions.
  """
  def runTest(self):
    import transitfeed

    schedule = transitfeed.Schedule()
    schedule.AddAgency("Sample Agency", "http://example.com",
                       "America/Los_Angeles")
    route = transitfeed.Route()
    route.route_id = "SAMPLE_ID"
    route.route_type = 3
    route.route_short_name = "66"
    route.route_long_name = "Sample Route"
    schedule.AddRouteObject(route)

    service_period = transitfeed.ServicePeriod("WEEK")
    service_period.SetStartDate("20070101")
    service_period.SetEndDate("20071231")
    service_period.SetWeekdayService(True)
    schedule.AddServicePeriodObject(service_period)

    trip = transitfeed.Trip()
    trip.route_id = "SAMPLE_ID"
    trip.service_period = service_period
    trip.trip_id = "SAMPLE_TRIP"
    trip.direction_id = "0"
    trip.block_id = None
    schedule.AddTripObject(trip)

    stop1 = transitfeed.Stop()
    stop1.stop_id = "STOP1"
    stop1.stop_name = "Stop 1"
    stop1.stop_lat = 78.243587
    stop1.stop_lon = 32.258937
    schedule.AddStopObject(stop1)
    trip.AddStopTime(stop1, arrival_time="12:00:00", departure_time="12:00:00")

    stop2 = transitfeed.Stop()
    stop2.stop_id = "STOP2"
    stop2.stop_name = "Stop 2"
    stop2.stop_lat = 78.253587
    stop2.stop_lon = 32.258937
    schedule.AddStopObject(stop2)
    trip.AddStopTime(stop2, arrival_time="12:05:00", departure_time="12:05:00")

    schedule.Validate()  # not necessary, but helpful for finding problems
    schedule.WriteGoogleTransitFeed("new_feed.zip")


class AgencyIDValidationTestCase(util.TestCase):
  def runTest(self):
    schedule = transitfeed.Schedule(
        problem_reporter=ExceptionProblemReporterNoExpiration())
    route = transitfeed.Route()
    route.route_id = "SAMPLE_ID"
    route.route_type = 3
    route.route_long_name = "Sample Route"
    # no agency defined yet, failure.
    try:
      schedule.AddRouteObject(route)
      self.fail("Expected validation error")
    except transitfeed.InvalidValue, e:
      self.assertEqual('agency_id', e.column_name)
      self.assertEqual(None, e.value)

    # one agency defined, assume that the route belongs to it
    schedule.AddAgency("Test Agency", "http://example.com",
                       "America/Los_Angeles", "TEST_AGENCY")
    schedule.AddRouteObject(route)

    schedule.AddAgency("Test Agency 2", "http://example.com",
                       "America/Los_Angeles", "TEST_AGENCY_2")
    route = transitfeed.Route()
    route.route_id = "SAMPLE_ID_2"
    route.route_type = 3
    route.route_long_name = "Sample Route 2"
    # multiple agencies defined, don't know what omitted agency_id should be
    try:
      schedule.AddRouteObject(route)
      self.fail("Expected validation error")
    except transitfeed.InvalidValue, e:
      self.assertEqual('agency_id', e.column_name)
      self.assertEqual(None, e.value)

    # agency with no agency_id defined, matches route with no agency id
    schedule.AddAgency("Test Agency 3", "http://example.com",
                       "America/Los_Angeles")
    schedule.AddRouteObject(route)


class AddFrequencyValidationTestCase(ValidationTestCase):
  def ExpectInvalidValue(self, start_time, end_time, headway,
                         column_name, value):
    try:
      trip = transitfeed.Trip()
      trip.AddFrequency(start_time, end_time, headway)
      self.fail("Expected InvalidValue error on %s" % column_name)
    except transitfeed.InvalidValue, e:
      self.assertEqual(column_name, e.column_name)
      self.assertEqual(value, e.value)
      self.assertEqual(0, len(trip.GetFrequencyTuples()))

  def ExpectMissingValue(self, start_time, end_time, headway, column_name):
    try:
      trip = transitfeed.Trip()
      trip.AddFrequency(start_time, end_time, headway)
      self.fail("Expected MissingValue error on %s" % column_name)
    except transitfeed.MissingValue, e:
      self.assertEqual(column_name, e.column_name)
      self.assertEqual(0, len(trip.GetFrequencyTuples()))

  def runTest(self):
    # these should work fine
    trip = transitfeed.Trip()
    trip.trip_id = "SAMPLE_ID"
    trip.AddFrequency(0, 50, 1200)
    trip.AddFrequency("01:00:00", "02:00:00", "600")
    trip.AddFrequency(u"02:00:00", u"03:00:00", u"1800")
    headways = trip.GetFrequencyTuples()
    self.assertEqual(3, len(headways))
    self.assertEqual((0, 50, 1200, 0), headways[0])
    self.assertEqual((3600, 7200, 600, 0), headways[1])
    self.assertEqual((7200, 10800, 1800, 0), headways[2])
    self.assertEqual([("SAMPLE_ID", "00:00:00", "00:00:50", "1200", "0"),
                      ("SAMPLE_ID", "01:00:00", "02:00:00", "600", "0"),
                      ("SAMPLE_ID", "02:00:00", "03:00:00", "1800", "0")],
                     trip.GetFrequencyOutputTuples())

    # now test invalid input
    self.ExpectMissingValue(None, 50, 1200, "start_time")
    self.ExpectMissingValue("", 50, 1200, "start_time")
    self.ExpectInvalidValue("midnight", 50, 1200, "start_time",
                                       "midnight")
    self.ExpectInvalidValue(-50, 50, 1200, "start_time", -50)
    self.ExpectMissingValue(0, None, 1200, "end_time")
    self.ExpectMissingValue(0, "", 1200, "end_time")
    self.ExpectInvalidValue(0, "noon", 1200, "end_time", "noon")
    self.ExpectInvalidValue(0, -50, 1200, "end_time", -50)
    self.ExpectMissingValue(0, 600, 0, "headway_secs")
    self.ExpectMissingValue(0, 600, None, "headway_secs")
    self.ExpectMissingValue(0, 600, "", "headway_secs")
    self.ExpectInvalidValue(0, 600, "test", "headway_secs", "test")
    self.ExpectInvalidValue(0, 600, -60, "headway_secs", -60)
    self.ExpectInvalidValue(0, 0, 1200, "end_time", 0)
    self.ExpectInvalidValue("12:00:00", "06:00:00", 1200, "end_time",
                                       21600)


class ScheduleBuilderTestCase(TempFileTestCaseBase):
  """Tests for using a Schedule object to build a GTFS file."""

  def testBuildFeedWithUtf8Names(self):
    problems = GetTestFailureProblemReporter(self)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    schedule.AddAgency("\xc8\x8b Fly Agency", "http://iflyagency.com",
                       "America/Los_Angeles")
    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetDateHasService('20070101')
    # "u020b i with inverted accent breve" encoded in utf-8
    stop1 = schedule.AddStop(lng=140, lat=48.2, name="\xc8\x8b hub")
    # "u020b i with inverted accent breve" as unicode string
    stop2 = schedule.AddStop(lng=140.001, lat=48.201,
                             name=u"remote \u020b station")
    route = schedule.AddRoute(u"\u03b2", "Beta", "Bus")
    trip = route.AddTrip(schedule, u"to remote \u020b station")
    repr(stop1)
    repr(stop2)
    repr(route)
    repr(trip)
    trip.AddStopTime(stop1, schedule=schedule, stop_time='10:00:00')
    trip.AddStopTime(stop2, stop_time='10:10:00')

    schedule.Validate(problems)
    schedule.WriteGoogleTransitFeed(self.tempfilepath)
    read_schedule = \
        transitfeed.Loader(self.tempfilepath, problems=problems,
                           extra_validation=True).Load()
    self.assertEquals(u'\u020b Fly Agency',
                      read_schedule.GetDefaultAgency().agency_name)
    self.assertEquals(u'\u03b2',
                      read_schedule.GetRoute(route.route_id).route_short_name)
    self.assertEquals(u'to remote \u020b station',
                      read_schedule.GetTrip(trip.trip_id).trip_headsign)

  def testBuildSimpleFeed(self):
    """Make a very simple feed using the Schedule class."""
    problems = GetTestFailureProblemReporter(self, ("ExpirationDate",
                                                    "NoServiceExceptions"))
    schedule = transitfeed.Schedule(problem_reporter=problems)

    schedule.AddAgency("Test Agency", "http://example.com",
                       "America/Los_Angeles")

    service_period = schedule.GetDefaultServicePeriod()
    self.assertTrue(service_period.service_id)
    service_period.SetWeekdayService(has_service=True)
    service_period.SetStartDate("20070320")
    service_period.SetEndDate("20071231")

    stop1 = schedule.AddStop(lng=-140.12, lat=48.921,
                             name="one forty at forty eight")
    stop2 = schedule.AddStop(lng=-140.22, lat=48.421, name="west and south")
    stop3 = schedule.AddStop(lng=-140.32, lat=48.121, name="more away")
    stop4 = schedule.AddStop(lng=-140.42, lat=48.021, name="more more away")

    route = schedule.AddRoute(short_name="R", long_name="My Route",
                              route_type="Bus")
    self.assertTrue(route.route_id)
    self.assertEqual(route.route_short_name, "R")
    self.assertEqual(route.route_type, 3)

    trip = route.AddTrip(schedule, headsign="To The End",
                         service_period=service_period)
    trip_id = trip.trip_id
    self.assertTrue(trip_id)
    trip = schedule.GetTrip(trip_id)
    self.assertEqual("To The End", trip.trip_headsign)
    self.assertEqual(service_period, trip.service_period)

    trip.AddStopTime(stop=stop1, arrival_secs=3600*8, departure_secs=3600*8)
    trip.AddStopTime(stop=stop2)
    trip.AddStopTime(stop=stop3, arrival_secs=3600*8 + 60*60,
                     departure_secs=3600*8 + 60*60)
    trip.AddStopTime(stop=stop4, arrival_time="9:13:00",
                     departure_secs=3600*8 + 60*103, stop_headsign="Last stop",
                     pickup_type=1, drop_off_type=3)

    schedule.Validate()
    schedule.WriteGoogleTransitFeed(self.tempfilepath)
    read_schedule = \
        transitfeed.Loader(self.tempfilepath, problems=problems,
                           extra_validation=True).Load()
    self.assertEqual(4, len(read_schedule.GetTrip(trip_id).GetTimeStops()))
    self.assertEqual(1, len(read_schedule.GetRouteList()))
    self.assertEqual(4, len(read_schedule.GetStopList()))

  def testStopIdConflict(self):
    problems = GetTestFailureProblemReporter(self)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    schedule.AddStop(lat=3, lng=4.1, name="stop1", stop_id="1")
    schedule.AddStop(lat=3, lng=4.0, name="stop0", stop_id="0")
    schedule.AddStop(lat=3, lng=4.2, name="stop2")
    schedule.AddStop(lat=3, lng=4.2, name="stop4", stop_id="4")
    # AddStop will try to use stop_id=4 first but it is taken
    schedule.AddStop(lat=3, lng=4.2, name="stop5")
    stop_list = sorted(schedule.GetStopList(), key=lambda s: s.stop_name)
    self.assertEqual("stop0 stop1 stop2 stop4 stop5",
                     " ".join([s.stop_name for s in stop_list]))
    self.assertMatchesRegex(r"0 1 2 4 \d{7,9}",
                            " ".join(s.stop_id for s in stop_list))

  def testRouteIdConflict(self):
    problems = GetTestFailureProblemReporter(self)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    route0 = schedule.AddRoute("0", "Long Name", "Bus")
    route1 = schedule.AddRoute("1", "", "Bus", route_id="1")
    route3 = schedule.AddRoute("3", "", "Bus", route_id="3")
    route_rand = schedule.AddRoute("R", "LNR", "Bus")
    route4 = schedule.AddRoute("4", "GooCar", "Bus")
    route_list = schedule.GetRouteList()
    route_list.sort(key=lambda r: r.route_short_name)
    self.assertEqual("0 1 3 4 R",
                     " ".join(r.route_short_name for r in route_list))
    self.assertMatchesRegex("0 1 3 4 \d{7,9}",
                            " ".join(r.route_id for r in route_list))
    self.assertEqual("Long Name,,,GooCar,LNR",
                     ",".join(r.route_long_name for r in route_list))

  def testTripIdConflict(self):
    problems = GetTestFailureProblemReporter(self)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetDateHasService("20070101")
    route = schedule.AddRoute("0", "Long Name", "Bus")
    route.AddTrip()
    route.AddTrip(schedule=schedule, headsign="hs1",
                  service_period=service_period, trip_id="1")
    route.AddTrip(schedule, "hs2", service_period, "2")
    route.AddTrip(trip_id="4")
    route.AddTrip()  # This will be given a random trip_id
    trip_list = sorted(schedule.GetTripList(), key=lambda t: int(t.trip_id))
    self.assertMatchesRegex("0 1 2 4 \d{7,9}",
                            " ".join(t.trip_id for t in trip_list))
    self.assertEqual(",hs1,hs2,,",
                     ",".join(t["trip_headsign"] for t in trip_list))
    for t in trip_list:
      self.assertEqual(service_period.service_id, t.service_id)
      self.assertEqual(route.route_id, t.route_id)


class WriteSampleFeedTestCase(TempFileTestCaseBase):
  def assertEqualTimeString(self, a, b):
    """Assert that a and b are equal, even if they don't have the same zero
    padding on the hour. IE 08:45:00 vs 8:45:00."""
    if a[1] == ':':
      a = '0' + a
    if b[1] == ':':
      b = '0' + b
    self.assertEqual(a, b)

  def assertEqualWithDefault(self, a, b, default):
    """Assert that a and b are equal. Treat None and default as equal."""
    if a == b:
      return
    if a in (None, default) and b in (None, default):
      return
    self.assertTrue(False, "a=%s b=%s" % (a, b))

  def runTest(self):
    accumulator = RecordingProblemAccumulator(self,
                                              ignore_types=("ExpirationDate",))
    problems = transitfeed.ProblemReporter(accumulator)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    agency = transitfeed.Agency()
    agency.agency_id = "DTA"
    agency.agency_name = "Demo Transit Authority"
    agency.agency_url = "http://google.com"
    agency.agency_timezone = "America/Los_Angeles"
    agency.agency_lang = 'en'
    # Test that unknown columns, such as agency_mission, are preserved
    agency.agency_mission = "Get You There"
    schedule.AddAgencyObject(agency)

    routes = []
    route_data = [
        ("AB", "DTA", "10", "Airport - Bullfrog", 3),
        ("BFC", "DTA", "20", "Bullfrog - Furnace Creek Resort", 3),
        ("STBA", "DTA", "30", "Stagecoach - Airport Shuttle", 3),
        ("CITY", "DTA", "40", "City", 3),
        ("AAMV", "DTA", "50", "Airport - Amargosa Valley", 3)
      ]

    for route_entry in route_data:
      route = transitfeed.Route()
      (route.route_id, route.agency_id, route.route_short_name,
       route.route_long_name, route.route_type) = route_entry
      routes.append(route)
      schedule.AddRouteObject(route)

    shape_data = [
      (36.915760, -116.751709),
      (36.905018, -116.763206),
      (36.902134, -116.777969),
      (36.904091, -116.788185),
      (36.883602, -116.814537),
      (36.874523, -116.795593),
      (36.873302, -116.786491),
      (36.869202, -116.784241),
      (36.868515, -116.784729),
    ]

    shape = transitfeed.Shape("BFC1S")
    for (lat, lon) in shape_data:
      shape.AddPoint(lat, lon)
    schedule.AddShapeObject(shape)

    week_period = transitfeed.ServicePeriod()
    week_period.service_id = "FULLW"
    week_period.start_date = "20070101"
    week_period.end_date = "20071231"
    week_period.SetWeekdayService()
    week_period.SetWeekendService()
    week_period.SetDateHasService("20070604", False)
    schedule.AddServicePeriodObject(week_period)

    weekend_period = transitfeed.ServicePeriod()
    weekend_period.service_id = "WE"
    weekend_period.start_date = "20070101"
    weekend_period.end_date = "20071231"
    weekend_period.SetWeekendService()
    schedule.AddServicePeriodObject(weekend_period)

    stops = []
    stop_data = [
        ("FUR_CREEK_RES", "Furnace Creek Resort (Demo)",
         36.425288, -117.133162, "zone-a", "1234"),
        ("BEATTY_AIRPORT", "Nye County Airport (Demo)",
         36.868446, -116.784682, "zone-a", "1235"),
        ("BULLFROG", "Bullfrog (Demo)", 36.88108, -116.81797, "zone-b", "1236"),
        ("STAGECOACH", "Stagecoach Hotel & Casino (Demo)",
         36.915682, -116.751677, "zone-c", "1237"),
        ("NADAV", "North Ave / D Ave N (Demo)", 36.914893, -116.76821, "", ""),
        ("NANAA", "North Ave / N A Ave (Demo)", 36.914944, -116.761472, "", ""),
        ("DADAN", "Doing AVe / D Ave N (Demo)", 36.909489, -116.768242, "", ""),
        ("EMSI", "E Main St / S Irving St (Demo)",
         36.905697, -116.76218, "", ""),
        ("AMV", "Amargosa Valley (Demo)", 36.641496, -116.40094, "", ""),
      ]
    for stop_entry in stop_data:
      stop = transitfeed.Stop()
      (stop.stop_id, stop.stop_name, stop.stop_lat, stop.stop_lon,
          stop.zone_id, stop.stop_code) = stop_entry
      schedule.AddStopObject(stop)
      stops.append(stop)
    # Add a value to an unknown column and make sure it is preserved
    schedule.GetStop("BULLFROG").stop_sound = "croak!"

    trip_data = [
        ("AB", "FULLW", "AB1", "to Bullfrog", "0", "1", None),
        ("AB", "FULLW", "AB2", "to Airport", "1", "2", None),
        ("STBA", "FULLW", "STBA", "Shuttle", None, None, None),
        ("CITY", "FULLW", "CITY1", None, "0", None, None),
        ("CITY", "FULLW", "CITY2", None, "1", None, None),
        ("BFC", "FULLW", "BFC1", "to Furnace Creek Resort", "0", "1", "BFC1S"),
        ("BFC", "FULLW", "BFC2", "to Bullfrog", "1", "2", None),
        ("AAMV", "WE", "AAMV1", "to Amargosa Valley", "0", None, None),
        ("AAMV", "WE", "AAMV2", "to Airport", "1", None, None),
        ("AAMV", "WE", "AAMV3", "to Amargosa Valley", "0", None, None),
        ("AAMV", "WE", "AAMV4", "to Airport", "1", None, None),
      ]

    trips = []
    for trip_entry in trip_data:
      trip = transitfeed.Trip()
      (trip.route_id, trip.service_id, trip.trip_id, trip.trip_headsign,
       trip.direction_id, trip.block_id, trip.shape_id) = trip_entry
      trips.append(trip)
      schedule.AddTripObject(trip)

    stop_time_data = {
        "STBA": [("6:00:00", "6:00:00", "STAGECOACH", None, None, None, None),
                 ("6:20:00", "6:20:00", "BEATTY_AIRPORT", None, None, None, None)],
        "CITY1": [("6:00:00", "6:00:00", "STAGECOACH", 1.34, 0, 0, "stop 1"),
                  ("6:05:00", "6:07:00", "NANAA", 2.40, 1, 2, "stop 2"),
                  ("6:12:00", "6:14:00", "NADAV", 3.0, 2, 2, "stop 3"),
                  ("6:19:00", "6:21:00", "DADAN", 4, 2, 2, "stop 4"),
                  ("6:26:00", "6:28:00", "EMSI", 5.78, 2, 3, "stop 5")],
        "CITY2": [("6:28:00", "6:28:00", "EMSI", None, None, None, None),
                  ("6:35:00", "6:37:00", "DADAN", None, None, None, None),
                  ("6:42:00", "6:44:00", "NADAV", None, None, None, None),
                  ("6:49:00", "6:51:00", "NANAA", None, None, None, None),
                  ("6:56:00", "6:58:00", "STAGECOACH", None, None, None, None)],
        "AB1": [("8:00:00", "8:00:00", "BEATTY_AIRPORT", None, None, None, None),
                ("8:10:00", "8:15:00", "BULLFROG", None, None, None, None)],
        "AB2": [("12:05:00", "12:05:00", "BULLFROG", None, None, None, None),
                ("12:15:00", "12:15:00", "BEATTY_AIRPORT", None, None, None, None)],
        "BFC1": [("8:20:00", "8:20:00", "BULLFROG", None, None, None, None),
                 ("9:20:00", "9:20:00", "FUR_CREEK_RES", None, None, None, None)],
        "BFC2": [("11:00:00", "11:00:00", "FUR_CREEK_RES", None, None, None, None),
                 ("12:00:00", "12:00:00", "BULLFROG", None, None, None, None)],
        "AAMV1": [("8:00:00", "8:00:00", "BEATTY_AIRPORT", None, None, None, None),
                  ("9:00:00", "9:00:00", "AMV", None, None, None, None)],
        "AAMV2": [("10:00:00", "10:00:00", "AMV", None, None, None, None),
                  ("11:00:00", "11:00:00", "BEATTY_AIRPORT", None, None, None, None)],
        "AAMV3": [("13:00:00", "13:00:00", "BEATTY_AIRPORT", None, None, None, None),
                  ("14:00:00", "14:00:00", "AMV", None, None, None, None)],
        "AAMV4": [("15:00:00", "15:00:00", "AMV", None, None, None, None),
                  ("16:00:00", "16:00:00", "BEATTY_AIRPORT", None, None, None, None)],
      }

    for trip_id, stop_time_list in stop_time_data.items():
      for stop_time_entry in stop_time_list:
        (arrival_time, departure_time, stop_id, shape_dist_traveled,
            pickup_type, drop_off_type, stop_headsign) = stop_time_entry
        trip = schedule.GetTrip(trip_id)
        stop = schedule.GetStop(stop_id)
        trip.AddStopTime(stop, arrival_time=arrival_time,
                         departure_time=departure_time,
                         shape_dist_traveled=shape_dist_traveled,
                         pickup_type=pickup_type, drop_off_type=drop_off_type,
                         stop_headsign=stop_headsign)

    self.assertEqual(0, schedule.GetTrip("CITY1").GetStopTimes()[0].pickup_type)
    self.assertEqual(1, schedule.GetTrip("CITY1").GetStopTimes()[1].pickup_type)

    headway_data = [
        ("STBA", "6:00:00", "22:00:00", 1800),
        ("CITY1", "6:00:00", "7:59:59", 1800),
        ("CITY2", "6:00:00", "7:59:59", 1800),
        ("CITY1", "8:00:00", "9:59:59", 600),
        ("CITY2", "8:00:00", "9:59:59", 600),
        ("CITY1", "10:00:00", "15:59:59", 1800),
        ("CITY2", "10:00:00", "15:59:59", 1800),
        ("CITY1", "16:00:00", "18:59:59", 600),
        ("CITY2", "16:00:00", "18:59:59", 600),
        ("CITY1", "19:00:00", "22:00:00", 1800),
        ("CITY2", "19:00:00", "22:00:00", 1800),
      ]

    headway_trips = {}
    for headway_entry in headway_data:
      (trip_id, start_time, end_time, headway) = headway_entry
      headway_trips[trip_id] = []  # adding to set to check later
      trip = schedule.GetTrip(trip_id)
      trip.AddFrequency(start_time, end_time, headway, 0, problems)
    for trip_id in headway_trips:
      headway_trips[trip_id] = \
          schedule.GetTrip(trip_id).GetFrequencyTuples()

    fare_data = [
        ("p", 1.25, "USD", 0, 0),
        ("a", 5.25, "USD", 0, 0),
      ]

    fares = []
    for fare_entry in fare_data:
      fare = transitfeed.FareAttribute(fare_entry[0], fare_entry[1],
                                       fare_entry[2], fare_entry[3],
                                       fare_entry[4])
      fares.append(fare)
      schedule.AddFareAttributeObject(fare)

    fare_rule_data = [
        ("p", "AB", "zone-a", "zone-b", None),
        ("p", "STBA", "zone-a", None, "zone-c"),
        ("p", "BFC", None, "zone-b", "zone-a"),
        ("a", "AAMV", None, None, None),
      ]

    for fare_id, route_id, orig_id, dest_id, contains_id in fare_rule_data:
      rule = transitfeed.FareRule(
          fare_id=fare_id, route_id=route_id, origin_id=orig_id,
          destination_id=dest_id, contains_id=contains_id)
      schedule.AddFareRuleObject(rule, problems)

    schedule.Validate(problems)
    accumulator.AssertNoMoreExceptions()
    schedule.WriteGoogleTransitFeed(self.tempfilepath)

    read_schedule = \
        transitfeed.Loader(self.tempfilepath, problems=problems,
                           extra_validation=True).Load()
    e = accumulator.PopException("UnrecognizedColumn")
    self.assertEqual(e.file_name, "agency.txt")
    self.assertEqual(e.column_name, "agency_mission")
    e = accumulator.PopException("UnrecognizedColumn")
    self.assertEqual(e.file_name, "stops.txt")
    self.assertEqual(e.column_name, "stop_sound")
    accumulator.AssertNoMoreExceptions()

    self.assertEqual(1, len(read_schedule.GetAgencyList()))
    self.assertEqual(agency, read_schedule.GetAgency(agency.agency_id))

    self.assertEqual(len(routes), len(read_schedule.GetRouteList()))
    for route in routes:
      self.assertEqual(route, read_schedule.GetRoute(route.route_id))

    self.assertEqual(2, len(read_schedule.GetServicePeriodList()))
    self.assertEqual(week_period,
                     read_schedule.GetServicePeriod(week_period.service_id))
    self.assertEqual(weekend_period,
                     read_schedule.GetServicePeriod(weekend_period.service_id))

    self.assertEqual(len(stops), len(read_schedule.GetStopList()))
    for stop in stops:
      self.assertEqual(stop, read_schedule.GetStop(stop.stop_id))
    self.assertEqual("croak!", read_schedule.GetStop("BULLFROG").stop_sound)

    self.assertEqual(len(trips), len(read_schedule.GetTripList()))
    for trip in trips:
      self.assertEqual(trip, read_schedule.GetTrip(trip.trip_id))

    for trip_id in headway_trips:
      self.assertEqual(headway_trips[trip_id],
                       read_schedule.GetTrip(trip_id).GetFrequencyTuples())

    for trip_id, stop_time_list in stop_time_data.items():
      trip = read_schedule.GetTrip(trip_id)
      read_stoptimes = trip.GetStopTimes()
      self.assertEqual(len(read_stoptimes), len(stop_time_list))
      for stop_time_entry, read_stoptime in zip(stop_time_list, read_stoptimes):
        (arrival_time, departure_time, stop_id, shape_dist_traveled,
            pickup_type, drop_off_type, stop_headsign) = stop_time_entry
        self.assertEqual(stop_id, read_stoptime.stop_id)
        self.assertEqual(read_schedule.GetStop(stop_id), read_stoptime.stop)
        self.assertEqualTimeString(arrival_time, read_stoptime.arrival_time)
        self.assertEqualTimeString(departure_time, read_stoptime.departure_time)
        self.assertEqual(shape_dist_traveled, read_stoptime.shape_dist_traveled)
        self.assertEqualWithDefault(pickup_type, read_stoptime.pickup_type, 0)
        self.assertEqualWithDefault(drop_off_type, read_stoptime.drop_off_type, 0)
        self.assertEqualWithDefault(stop_headsign, read_stoptime.stop_headsign, '')

    self.assertEqual(len(fares), len(read_schedule.GetFareAttributeList()))
    for fare in fares:
      self.assertEqual(fare, read_schedule.GetFareAttribute(fare.fare_id))

    read_fare_rules_data = []
    for fare in read_schedule.GetFareAttributeList():
      for rule in fare.GetFareRuleList():
        self.assertEqual(fare.fare_id, rule.fare_id)
        read_fare_rules_data.append((fare.fare_id, rule.route_id,
                                     rule.origin_id, rule.destination_id,
                                     rule.contains_id))

    fare_rule_data.sort()
    read_fare_rules_data.sort()
    self.assertEqual(len(read_fare_rules_data), len(fare_rule_data))
    for rf, f in zip(read_fare_rules_data, fare_rule_data):
      self.assertEqual(rf, f)

    self.assertEqual(1, len(read_schedule.GetShapeList()))
    self.assertEqual(shape, read_schedule.GetShape(shape.shape_id))

# TODO: test GetPattern

class DefaultAgencyTestCase(util.TestCase):
  def freeAgency(self, ex=''):
    agency = transitfeed.Agency()
    agency.agency_id = 'agencytestid' + ex
    agency.agency_name = 'Foo Bus Line' + ex
    agency.agency_url = 'http://gofoo.com/' + ex
    agency.agency_timezone = 'America/Los_Angeles'
    return agency

  def test_SetDefault(self):
    schedule = transitfeed.Schedule()
    agency = self.freeAgency()
    schedule.SetDefaultAgency(agency)
    self.assertEqual(agency, schedule.GetDefaultAgency())

  def test_NewDefaultAgency(self):
    schedule = transitfeed.Schedule()
    agency1 = schedule.NewDefaultAgency()
    self.assertTrue(agency1.agency_id)
    self.assertEqual(agency1.agency_id, schedule.GetDefaultAgency().agency_id)
    self.assertEqual(1, len(schedule.GetAgencyList()))
    agency2 = schedule.NewDefaultAgency()
    self.assertTrue(agency2.agency_id)
    self.assertEqual(agency2.agency_id, schedule.GetDefaultAgency().agency_id)
    self.assertEqual(2, len(schedule.GetAgencyList()))
    self.assertNotEqual(agency1, agency2)
    self.assertNotEqual(agency1.agency_id, agency2.agency_id)

    agency3 = schedule.NewDefaultAgency(agency_id='agency3',
                                        agency_name='Agency 3',
                                        agency_url='http://goagency')
    self.assertEqual(agency3.agency_id, 'agency3')
    self.assertEqual(agency3.agency_name, 'Agency 3')
    self.assertEqual(agency3.agency_url, 'http://goagency')
    self.assertEqual(agency3, schedule.GetDefaultAgency())
    self.assertEqual('agency3', schedule.GetDefaultAgency().agency_id)
    self.assertEqual(3, len(schedule.GetAgencyList()))

  def test_NoAgencyMakeNewDefault(self):
    schedule = transitfeed.Schedule()
    agency = schedule.GetDefaultAgency()
    self.assertTrue(isinstance(agency, transitfeed.Agency))
    self.assertTrue(agency.agency_id)
    self.assertEqual(1, len(schedule.GetAgencyList()))
    self.assertEqual(agency, schedule.GetAgencyList()[0])
    self.assertEqual(agency.agency_id, schedule.GetAgencyList()[0].agency_id)

  def test_AssumeSingleAgencyIsDefault(self):
    schedule = transitfeed.Schedule()
    agency1 = self.freeAgency()
    schedule.AddAgencyObject(agency1)
    agency2 = self.freeAgency('2')  # don't add to schedule
    # agency1 is default because it is the only Agency in schedule
    self.assertEqual(agency1, schedule.GetDefaultAgency())

  def test_MultipleAgencyCausesNoDefault(self):
    schedule = transitfeed.Schedule()
    agency1 = self.freeAgency()
    schedule.AddAgencyObject(agency1)
    agency2 = self.freeAgency('2')
    schedule.AddAgencyObject(agency2)
    self.assertEqual(None, schedule.GetDefaultAgency())

  def test_OverwriteExistingAgency(self):
    schedule = transitfeed.Schedule()
    agency1 = self.freeAgency()
    agency1.agency_id = '1'
    schedule.AddAgencyObject(agency1)
    agency2 = schedule.NewDefaultAgency()
    # Make sure agency1 was not overwritten by the new default
    self.assertEqual(agency1, schedule.GetAgency(agency1.agency_id))
    self.assertNotEqual('1', agency2.agency_id)


class FindUniqueIdTestCase(util.TestCase):
  def test_simple(self):
    d = {}
    for i in range(0, 5):
      d[transitfeed.FindUniqueId(d)] = 1
    k = d.keys()
    k.sort()
    self.assertEqual(('0', '1', '2', '3', '4'), tuple(k))

  def test_AvoidCollision(self):
    d = {'1': 1}
    d[transitfeed.FindUniqueId(d)] = 1
    self.assertEqual(2, len(d))
    self.assertFalse('3' in d, "Ops, next statement should add something to d")
    d['3'] = None
    d[transitfeed.FindUniqueId(d)] = 1
    self.assertEqual(4, len(d))


class DefaultServicePeriodTestCase(util.TestCase):
  def test_SetDefault(self):
    schedule = transitfeed.Schedule()
    service1 = transitfeed.ServicePeriod()
    service1.SetDateHasService('20070101', True)
    service1.service_id = 'SERVICE1'
    schedule.SetDefaultServicePeriod(service1)
    self.assertEqual(service1, schedule.GetDefaultServicePeriod())
    self.assertEqual(service1, schedule.GetServicePeriod(service1.service_id))

  def test_NewDefault(self):
    schedule = transitfeed.Schedule()
    service1 = schedule.NewDefaultServicePeriod()
    self.assertTrue(service1.service_id)
    schedule.GetServicePeriod(service1.service_id)
    service1.SetDateHasService('20070101', True)  # Make service1 different
    service2 = schedule.NewDefaultServicePeriod()
    schedule.GetServicePeriod(service2.service_id)
    self.assertTrue(service1.service_id)
    self.assertTrue(service2.service_id)
    self.assertNotEqual(service1, service2)
    self.assertNotEqual(service1.service_id, service2.service_id)

  def test_NoServicesMakesNewDefault(self):
    schedule = transitfeed.Schedule()
    service1 = schedule.GetDefaultServicePeriod()
    self.assertEqual(service1, schedule.GetServicePeriod(service1.service_id))

  def test_AssumeSingleServiceIsDefault(self):
    schedule = transitfeed.Schedule()
    service1 = transitfeed.ServicePeriod()
    service1.SetDateHasService('20070101', True)
    service1.service_id = 'SERVICE1'
    schedule.AddServicePeriodObject(service1)
    self.assertEqual(service1, schedule.GetDefaultServicePeriod())
    self.assertEqual(service1.service_id, schedule.GetDefaultServicePeriod().service_id)

  def test_MultipleServicesCausesNoDefault(self):
    schedule = transitfeed.Schedule()
    service1 = transitfeed.ServicePeriod()
    service1.service_id = 'SERVICE1'
    service1.SetDateHasService('20070101', True)
    schedule.AddServicePeriodObject(service1)
    service2 = transitfeed.ServicePeriod()
    service2.service_id = 'SERVICE2'
    service2.SetDateHasService('20070201', True)
    schedule.AddServicePeriodObject(service2)
    service_d = schedule.GetDefaultServicePeriod()
    self.assertEqual(service_d, None)


class GetTripTimeTestCase(util.TestCase):
  """Test for GetStopTimeTrips and GetTimeInterpolatedStops"""
  def setUp(self):
    problems = GetTestFailureProblemReporter(self)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    self.schedule = schedule
    schedule.AddAgency("Agency", "http://iflyagency.com",
                       "America/Los_Angeles")
    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetDateHasService('20070101')
    self.stop1 = schedule.AddStop(lng=140.01, lat=0, name="140.01,0")
    self.stop2 = schedule.AddStop(lng=140.02, lat=0, name="140.02,0")
    self.stop3 = schedule.AddStop(lng=140.03, lat=0, name="140.03,0")
    self.stop4 = schedule.AddStop(lng=140.04, lat=0, name="140.04,0")
    self.stop5 = schedule.AddStop(lng=140.05, lat=0, name="140.05,0")
    self.route1 = schedule.AddRoute("1", "One", "Bus")

    self.trip1 = self.route1.AddTrip(schedule, "trip 1", trip_id='trip1')
    self.trip1.AddStopTime(self.stop1, schedule=schedule, departure_secs=100,
                           arrival_secs=100)
    self.trip1.AddStopTime(self.stop2, schedule=schedule)
    self.trip1.AddStopTime(self.stop3, schedule=schedule)
    # loop back to stop2 to test that interpolated stops work ok even when
    # a stop between timepoints is further from the timepoint than the
    # preceding
    self.trip1.AddStopTime(self.stop2, schedule=schedule)
    self.trip1.AddStopTime(self.stop4, schedule=schedule, departure_secs=400,
                           arrival_secs=400)

    self.trip2 = self.route1.AddTrip(schedule, "trip 2", trip_id='trip2')
    self.trip2.AddStopTime(self.stop2, schedule=schedule, departure_secs=500,
                           arrival_secs=500)
    self.trip2.AddStopTime(self.stop3, schedule=schedule, departure_secs=600,
                           arrival_secs=600)
    self.trip2.AddStopTime(self.stop4, schedule=schedule, departure_secs=700,
                           arrival_secs=700)
    self.trip2.AddStopTime(self.stop3, schedule=schedule, departure_secs=800,
                           arrival_secs=800)

    self.trip3 = self.route1.AddTrip(schedule, "trip 3", trip_id='trip3')

  def testGetTimeInterpolatedStops(self):
    rv = self.trip1.GetTimeInterpolatedStops()
    self.assertEqual(5, len(rv))
    (secs, stoptimes, istimepoints) = tuple(zip(*rv))

    self.assertEqual((100, 160, 220, 280, 400), secs)
    self.assertEqual(("140.01,0", "140.02,0", "140.03,0", "140.02,0", "140.04,0"),
                     tuple([st.stop.stop_name for st in stoptimes]))
    self.assertEqual((True, False, False, False, True), istimepoints)

    self.assertEqual([], self.trip3.GetTimeInterpolatedStops())

  def testGetTimeInterpolatedStopsUntimedEnd(self):
    self.trip2.AddStopTime(self.stop3, schedule=self.schedule)
    self.assertRaises(ValueError, self.trip2.GetTimeInterpolatedStops)

  def testGetTimeInterpolatedStopsUntimedStart(self):
    # Temporarily replace the problem reporter so that adding the first
    # StopTime without a time doesn't throw an exception.
    old_problems = self.schedule.problem_reporter
    self.schedule.problem_reporter = GetTestFailureProblemReporter(
        self, ("OtherProblem",))
    self.trip3.AddStopTime(self.stop3, schedule=self.schedule)
    self.schedule.problem_reporter = old_problems
    self.trip3.AddStopTime(self.stop2, schedule=self.schedule,
                           departure_secs=500, arrival_secs=500)
    self.assertRaises(ValueError, self.trip3.GetTimeInterpolatedStops)

  def testGetTimeInterpolatedStopsSingleStopTime(self):
    self.trip3.AddStopTime(self.stop3, schedule=self.schedule,
                           departure_secs=500, arrival_secs=500)
    rv = self.trip3.GetTimeInterpolatedStops()
    self.assertEqual(1, len(rv))
    self.assertEqual(500, rv[0][0])
    self.assertEqual(True, rv[0][2])

  def testGetStopTimeTrips(self):
    stopa = self.schedule.GetNearestStops(lon=140.03, lat=0)[0]
    self.assertEqual("140.03,0", stopa.stop_name)  # Got stop3?
    rv = stopa.GetStopTimeTrips(self.schedule)
    self.assertEqual(3, len(rv))
    (secs, trip_index, istimepoints) = tuple(zip(*rv))
    self.assertEqual((220, 600, 800), secs)
    self.assertEqual(("trip1", "trip2", "trip2"), tuple([ti[0].trip_id for ti in trip_index]))
    self.assertEqual((2, 1, 3), tuple([ti[1] for ti in trip_index]))
    self.assertEqual((False, True, True), istimepoints)

  def testStopTripIndex(self):
    trip_index = self.stop3.trip_index
    trip_ids = [t.trip_id for t, i in trip_index]
    self.assertEqual(["trip1", "trip2", "trip2"], trip_ids)
    self.assertEqual([2, 1, 3], [i for t, i in trip_index])

  def testGetTrips(self):
    self.assertEqual(set([t.trip_id for t in self.stop1.GetTrips(self.schedule)]),
                     set([self.trip1.trip_id]))
    self.assertEqual(set([t.trip_id for t in self.stop2.GetTrips(self.schedule)]),
                     set([self.trip1.trip_id, self.trip2.trip_id]))
    self.assertEqual(set([t.trip_id for t in self.stop3.GetTrips(self.schedule)]),
                     set([self.trip1.trip_id, self.trip2.trip_id]))
    self.assertEqual(set([t.trip_id for t in self.stop4.GetTrips(self.schedule)]),
                     set([self.trip1.trip_id, self.trip2.trip_id]))
    self.assertEqual(set([t.trip_id for t in self.stop5.GetTrips(self.schedule)]),
                     set())


class ApproximateDistanceBetweenStopsTestCase(util.TestCase):
  def testEquator(self):
    stop1 = transitfeed.Stop(lat=0, lng=100,
                             name='Stop one', stop_id='1')
    stop2 = transitfeed.Stop(lat=0.01, lng=100.01,
                             name='Stop two', stop_id='2')
    self.assertAlmostEqual(
        transitfeed.ApproximateDistanceBetweenStops(stop1, stop2),
        1570, -1)  # Compare first 3 digits

  def testWhati(self):
    stop1 = transitfeed.Stop(lat=63.1, lng=-117.2,
                             name='Stop whati one', stop_id='1')
    stop2 = transitfeed.Stop(lat=63.102, lng=-117.201,
                             name='Stop whati two', stop_id='2')
    self.assertAlmostEqual(
        transitfeed.ApproximateDistanceBetweenStops(stop1, stop2),
        228, 0)


class TimeConversionHelpersTestCase(util.TestCase):
  def testTimeToSecondsSinceMidnight(self):
    self.assertEqual(transitfeed.TimeToSecondsSinceMidnight("01:02:03"), 3723)
    self.assertEqual(transitfeed.TimeToSecondsSinceMidnight("00:00:00"), 0)
    self.assertEqual(transitfeed.TimeToSecondsSinceMidnight("25:24:23"), 91463)
    try:
      transitfeed.TimeToSecondsSinceMidnight("10:15:00am")
    except transitfeed.Error:
      pass  # expected
    else:
      self.fail("Should have thrown Error")

  def testFormatSecondsSinceMidnight(self):
    self.assertEqual(transitfeed.FormatSecondsSinceMidnight(3723), "01:02:03")
    self.assertEqual(transitfeed.FormatSecondsSinceMidnight(0), "00:00:00")
    self.assertEqual(transitfeed.FormatSecondsSinceMidnight(91463), "25:24:23")

  def testDateStringToDateObject(self):
    self.assertEqual(transitfeed.DateStringToDateObject("20080901"),
                     datetime.date(2008, 9, 1))
    self.assertEqual(transitfeed.DateStringToDateObject("20080841"), None)


class ValidationUtilsTestCase(util.TestCase):
  def testIsValidURL(self):
    self.assertTrue(transitfeed.IsValidURL("http://www.example.com"))
    self.assertFalse(transitfeed.IsValidURL("ftp://www.example.com"))
    self.assertFalse(transitfeed.IsValidURL(""))

  def testValidateURL(self):
    accumulator = RecordingProblemAccumulator(self)
    problems = transitfeed.ProblemReporter(accumulator)
    self.assertTrue(transitfeed.ValidateURL("", "col", problems))
    accumulator.AssertNoMoreExceptions()
    self.assertTrue(transitfeed.ValidateURL("http://www.example.com", "col",
                                            problems))
    accumulator.AssertNoMoreExceptions()
    self.assertFalse(transitfeed.ValidateURL("ftp://www.example.com", "col",
                                            problems))
    e = accumulator.PopInvalidValue("col")
    accumulator.AssertNoMoreExceptions()

  def testIsValidHexColor(self):
    self.assertTrue(transitfeed.IsValidHexColor("33FF00"))
    self.assertFalse(transitfeed.IsValidHexColor("blue"))
    self.assertFalse(transitfeed.IsValidHexColor(""))

  def testIsValidLanguageCode(self):
    self.assertTrue(transitfeed.IsValidLanguageCode("de"))
    self.assertFalse(transitfeed.IsValidLanguageCode("Swiss German"))
    self.assertFalse(transitfeed.IsValidLanguageCode(""))

  def testValidateLanguageCode(self):
    accumulator = RecordingProblemAccumulator(self)
    problems = transitfeed.ProblemReporter(accumulator)
    self.assertTrue(transitfeed.ValidateLanguageCode("", "col", problems))
    accumulator.AssertNoMoreExceptions()
    self.assertTrue(transitfeed.ValidateLanguageCode("de", "col", problems))
    accumulator.AssertNoMoreExceptions()
    self.assertFalse(transitfeed.ValidateLanguageCode("Swiss German", "col",
                                                      problems))
    e = accumulator.PopInvalidValue("col")
    accumulator.AssertNoMoreExceptions()

  def testIsValidTimezone(self):
    self.assertTrue(transitfeed.IsValidTimezone("America/Los_Angeles"))
    self.assertFalse(transitfeed.IsValidTimezone("Switzerland/Wil"))
    self.assertFalse(transitfeed.IsValidTimezone(""))

  def testValidateTimezone(self):
    accumulator = RecordingProblemAccumulator(self)
    problems = transitfeed.ProblemReporter(accumulator)
    self.assertTrue(transitfeed.ValidateTimezone("", "col", problems))
    accumulator.AssertNoMoreExceptions()
    self.assertTrue(transitfeed.ValidateTimezone("America/Los_Angeles", "col",
                                                 problems))
    accumulator.AssertNoMoreExceptions()
    self.assertFalse(transitfeed.ValidateTimezone("Switzerland/Wil", "col",
                                                  problems))
    e = accumulator.PopInvalidValue("col")
    accumulator.AssertNoMoreExceptions()

  def testIsValidDate(self):
    self.assertTrue(transitfeed.IsValidDate("20100801"))
    self.assertFalse(transitfeed.IsValidDate("20100732"))
    self.assertFalse(transitfeed.IsValidDate(""))

  def testValidateDate(self):
    accumulator = RecordingProblemAccumulator(self)
    problems = transitfeed.ProblemReporter(accumulator)
    self.assertTrue(transitfeed.ValidateDate("", "col", problems))
    accumulator.AssertNoMoreExceptions()
    self.assertTrue(transitfeed.ValidateDate("20100801", "col", problems))
    accumulator.AssertNoMoreExceptions()
    self.assertFalse(transitfeed.ValidateDate("20100732", "col", problems))
    e = accumulator.PopInvalidValue("col")
    accumulator.AssertNoMoreExceptions()


class FloatStringToFloatTestCase(util.TestCase):
  def runTest(self):
    accumulator = RecordingProblemAccumulator(self)
    problems = transitfeed.ProblemReporter(accumulator)

    self.assertAlmostEqual(0, transitfeed.FloatStringToFloat("0", problems))
    self.assertAlmostEqual(0, transitfeed.FloatStringToFloat(u"0", problems))
    self.assertAlmostEqual(1, transitfeed.FloatStringToFloat("1", problems))
    self.assertAlmostEqual(1,
                           transitfeed.FloatStringToFloat("1.00000", problems))
    self.assertAlmostEqual(1.5,
                           transitfeed.FloatStringToFloat("1.500", problems))
    self.assertAlmostEqual(-2, transitfeed.FloatStringToFloat("-2.0", problems))
    self.assertAlmostEqual(-2.5,
                            transitfeed.FloatStringToFloat("-2.5", problems))
    self.assertRaises(ValueError,
                      transitfeed.FloatStringToFloat, ".", problems)
    self.assertRaises(ValueError,
                      transitfeed.FloatStringToFloat, "0x20", problems)
    self.assertRaises(ValueError,
                      transitfeed.FloatStringToFloat, "-0x20", problems)
    self.assertRaises(ValueError,
                      transitfeed.FloatStringToFloat, "0b10", problems)

    # These should issue a warning, but otherwise parse successfully
    self.assertAlmostEqual(0.001,
                           transitfeed.FloatStringToFloat("1E-3", problems))
    e = accumulator.PopException("InvalidFloatValue")
    self.assertAlmostEqual(0.001,
                           transitfeed.FloatStringToFloat(".001", problems))
    e = accumulator.PopException("InvalidFloatValue")
    self.assertAlmostEqual(-0.001,
                           transitfeed.FloatStringToFloat("-.001", problems))
    e = accumulator.PopException("InvalidFloatValue")
    self.assertAlmostEqual(0,
                           transitfeed.FloatStringToFloat("0.", problems))
    e = accumulator.PopException("InvalidFloatValue")

    accumulator.AssertNoMoreExceptions()


class NonNegIntStringToIntTestCase(util.TestCase):
  def runTest(self):
    accumulator = RecordingProblemAccumulator(self)
    problems = transitfeed.ProblemReporter(accumulator)

    self.assertEqual(0, transitfeed.NonNegIntStringToInt("0", problems))
    self.assertEqual(0, transitfeed.NonNegIntStringToInt(u"0", problems))
    self.assertEqual(1, transitfeed.NonNegIntStringToInt("1", problems))
    self.assertEqual(2, transitfeed.NonNegIntStringToInt("2", problems))
    self.assertEqual(10, transitfeed.NonNegIntStringToInt("10", problems))
    self.assertEqual(1234567890123456789,
                     transitfeed.NonNegIntStringToInt("1234567890123456789",
                                                      problems))
    self.assertRaises(ValueError,
                      transitfeed.NonNegIntStringToInt, "", problems)
    self.assertRaises(ValueError,
                      transitfeed.NonNegIntStringToInt, "-1", problems)
    self.assertRaises(ValueError,
                      transitfeed.NonNegIntStringToInt, "0x1", problems)
    self.assertRaises(ValueError,
                      transitfeed.NonNegIntStringToInt, "1.0", problems)
    self.assertRaises(ValueError,
                      transitfeed.NonNegIntStringToInt, "1e1", problems)
    self.assertRaises(ValueError,
                      transitfeed.NonNegIntStringToInt, "0x20", problems)
    self.assertRaises(ValueError,
                      transitfeed.NonNegIntStringToInt, "0b10", problems)
    self.assertRaises(TypeError,
                      transitfeed.NonNegIntStringToInt, 1, problems)
    self.assertRaises(TypeError,
                      transitfeed.NonNegIntStringToInt, None, problems)

    # These should issue a warning, but otherwise parse successfully
    self.assertEqual(1, transitfeed.NonNegIntStringToInt("+1", problems))
    e = accumulator.PopException("InvalidNonNegativeIntegerValue")

    self.assertEqual(1, transitfeed.NonNegIntStringToInt("01", problems))
    e = accumulator.PopException("InvalidNonNegativeIntegerValue")

    self.assertEqual(0, transitfeed.NonNegIntStringToInt("00", problems))
    e = accumulator.PopException("InvalidNonNegativeIntegerValue")

    accumulator.AssertNoMoreExceptions()


class GetFrequencyTimesTestCase(util.TestCase):
  """Test for GetFrequencyStartTimes and GetFrequencyStopTimes"""
  def setUp(self):
    problems = GetTestFailureProblemReporter(self)
    schedule = transitfeed.Schedule(problem_reporter=problems)
    self.schedule = schedule
    schedule.AddAgency("Agency", "http://iflyagency.com",
                       "America/Los_Angeles")
    service_period = schedule.GetDefaultServicePeriod()
    service_period.SetStartDate("20080101")
    service_period.SetEndDate("20090101")
    service_period.SetWeekdayService(True)
    self.stop1 = schedule.AddStop(lng=140.01, lat=0, name="140.01,0")
    self.stop2 = schedule.AddStop(lng=140.02, lat=0, name="140.02,0")
    self.stop3 = schedule.AddStop(lng=140.03, lat=0, name="140.03,0")
    self.stop4 = schedule.AddStop(lng=140.04, lat=0, name="140.04,0")
    self.stop5 = schedule.AddStop(lng=140.05, lat=0, name="140.05,0")
    self.route1 = schedule.AddRoute("1", "One", "Bus")

    self.trip1 = self.route1.AddTrip(schedule, "trip 1", trip_id="trip1")
    # add different types of stop times
    self.trip1.AddStopTime(self.stop1, arrival_time="17:00:00",
        departure_time="17:01:00") # both arrival and departure time
    self.trip1.AddStopTime(self.stop2, schedule=schedule) # non timed
    self.trip1.AddStopTime(self.stop3, stop_time="17:45:00") # only stop_time

    # add headways starting before the trip
    self.trip1.AddFrequency("16:00:00", "18:00:00", 1800) # each 30 min
    self.trip1.AddFrequency("18:00:00", "20:00:00", 2700) # each 45 min

  def testGetFrequencyStartTimes(self):
    start_times = self.trip1.GetFrequencyStartTimes()
    self.assertEqual(
        ["16:00:00", "16:30:00", "17:00:00", "17:30:00",
         "18:00:00", "18:45:00", "19:30:00"],
        [transitfeed.FormatSecondsSinceMidnight(secs) for secs in start_times])
    # GetHeadwayStartTimes is deprecated, but should still return the same
    # result as GetFrequencyStartTimes
    self.assertEqual(start_times,
                     self.trip1.GetFrequencyStartTimes())

  def testGetFrequencyStopTimes(self):
    stoptimes_list = self.trip1.GetFrequencyStopTimes()
    arrival_secs = []
    departure_secs = []
    for stoptimes in stoptimes_list:
      arrival_secs.append([st.arrival_secs for st in stoptimes])
      departure_secs.append([st.departure_secs for st in stoptimes])

    # GetHeadwayStopTimes is deprecated, but should still return the same
    # result as GetFrequencyStopTimes
    # StopTimes are instantiated as they're read from the DB so they can't be
    # compared directly, but checking {arrival,departure}_secs should be enough
    # to catch most errors.
    headway_stoptimes_list = self.trip1.GetFrequencyStopTimes()
    headway_arrival_secs = []
    headway_departure_secs = []
    for stoptimes in stoptimes_list:
      headway_arrival_secs.append([st.arrival_secs for st in stoptimes])
      headway_departure_secs.append([st.departure_secs for st in stoptimes])
    self.assertEqual(arrival_secs, headway_arrival_secs)
    self.assertEqual(departure_secs, headway_departure_secs)

    self.assertEqual(([57600,None,60300],[59400,None,62100],[61200,None,63900],
                      [63000,None,65700],[64800,None,67500],[67500,None,70200],
                      [70200,None,72900]),
                     tuple(arrival_secs))
    self.assertEqual(([57660,None,60300],[59460,None,62100],[61260,None,63900],
                      [63060,None,65700],[64860,None,67500],[67560,None,70200],
                      [70260,None,72900]),
                     tuple(departure_secs))

    # test if stoptimes are created with same parameters than the ones from the original trip
    stoptimes = self.trip1.GetStopTimes()
    for stoptimes_clone in stoptimes_list:
      self.assertEqual(len(stoptimes_clone), len(stoptimes))
      for st_clone, st in zip(stoptimes_clone, stoptimes):
        for name in st.__slots__:
          if name not in ('arrival_secs', 'departure_secs'):
            self.assertEqual(getattr(st, name), getattr(st_clone, name))


class ServiceGapsTestCase(util.MemoryZipTestCase):

  def setUp(self):
    super(ServiceGapsTestCase, self).setUp()
    self.SetArchiveContents("calendar.txt",
                      "service_id,monday,tuesday,wednesday,thursday,friday,"
                      "saturday,sunday,start_date,end_date\n"
                      "FULLW,1,1,1,1,1,1,1,20090601,20090610\n"
                      "WE,0,0,0,0,0,1,1,20090718,20101231\n")
    self.SetArchiveContents("calendar_dates.txt",
                      "service_id,date,exception_type\n"
                      "WE,20090815,2\n"
                      "WE,20090816,2\n"
                      "WE,20090822,2\n"
                      # The following two lines are a 12-day service gap.
                      # Shouldn't issue a warning
                      "WE,20090829,2\n"
                      "WE,20090830,2\n"
                      "WE,20100102,2\n"
                      "WE,20100103,2\n"
                      "WE,20100109,2\n"
                      "WE,20100110,2\n"
                      "WE,20100612,2\n"
                      "WE,20100613,2\n"
                      "WE,20100619,2\n"
                      "WE,20100620,2\n")
    self.SetArchiveContents("trips.txt",
                      "route_id,service_id,trip_id\n"
                      "AB,WE,AB1\n"
                      "AB,FULLW,AB2\n")
    self.SetArchiveContents(
        "stop_times.txt",
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "AB1,10:00:00,10:00:00,BEATTY_AIRPORT,1\n"
        "AB1,10:20:00,10:20:00,BULLFROG,2\n"
        "AB2,10:25:00,10:25:00,STAGECOACH,1\n"
        "AB2,10:55:00,10:55:00,BULLFROG,2\n")
    self.schedule = self.MakeLoaderAndLoad(extra_validation=False)

  # If there is a service gap starting before today, and today has no service,
  # it should be found - even if tomorrow there is service
  def testServiceGapBeforeTodayIsDiscovered(self):
    self.schedule.Validate(today=date(2009, 7, 17),
                           service_gap_interval=13)
    exception = self.accumulator.PopException("TooManyDaysWithoutService")
    self.assertEquals(date(2009, 7, 5),
                      exception.first_day_without_service)
    self.assertEquals(date(2009, 7, 17),
                      exception.last_day_without_service)

    self.AssertCommonExceptions(date(2010, 6, 25))

  # If today has service past service gaps should not appear
  def testNoServiceGapBeforeTodayIfTodayHasService(self):
    self.schedule.Validate(today=date(2009, 7, 18),
                           service_gap_interval=13)

    self.AssertCommonExceptions(date(2010, 6, 25))

  # If the feed starts today NO previous service gap should be found
  # even if today does not have service
  def testNoServiceGapBeforeTodayIfTheFeedStartsToday(self):
    self.schedule.Validate(today=date(2009, 06, 01),
                           service_gap_interval=13)

    # This service gap is the one between FULLW and WE
    exception = self.accumulator.PopException("TooManyDaysWithoutService")
    self.assertEquals(date(2009, 6, 11),
                      exception.first_day_without_service)
    self.assertEquals(date(2009, 7, 17),
                      exception.last_day_without_service)
    # The one-year period ends before the June 2010 gap, so that last
    # service gap should _not_ be found
    self.AssertCommonExceptions(None)

  # If there is a gap at the end of the one-year period we should find it
  def testGapAtTheEndOfTheOneYearPeriodIsDiscovered(self):
    self.schedule.Validate(today=date(2009, 06, 22),
                           service_gap_interval=13)

    # This service gap is the one between FULLW and WE
    exception = self.accumulator.PopException("TooManyDaysWithoutService")
    self.assertEquals(date(2009, 6, 11),
                      exception.first_day_without_service)
    self.assertEquals(date(2009, 7, 17),
                      exception.last_day_without_service)

    self.AssertCommonExceptions(date(2010, 6, 21))

  # If we are right in the middle of a big service gap it should be
  # report as starting on "today - 12 days" and lasting until
  # service resumes
  def testCurrentServiceGapIsDiscovered(self):
    self.schedule.Validate(today=date(2009, 6, 30),
                           service_gap_interval=13)
    exception = self.accumulator.PopException("TooManyDaysWithoutService")
    self.assertEquals(date(2009, 6, 18),
                      exception.first_day_without_service)
    self.assertEquals(date(2009, 7, 17),
                      exception.last_day_without_service)

    self.AssertCommonExceptions(date(2010, 6, 25))

  # Asserts the service gaps that appear towards the end of the calendar
  # and which are common to all the tests
  def AssertCommonExceptions(self, last_exception_date):
    exception = self.accumulator.PopException("TooManyDaysWithoutService")
    self.assertEquals(date(2009, 8, 10),
                      exception.first_day_without_service)
    self.assertEquals(date(2009, 8, 22),
                      exception.last_day_without_service)

    exception = self.accumulator.PopException("TooManyDaysWithoutService")
    self.assertEquals(date(2009, 12, 28),
                      exception.first_day_without_service)
    self.assertEquals(date(2010, 1, 15),
                      exception.last_day_without_service)

    if last_exception_date is not None:
      exception = self.accumulator.PopException("TooManyDaysWithoutService")
      self.assertEquals(date(2010, 6, 7),
                        exception.first_day_without_service)
      self.assertEquals(last_exception_date,
                        exception.last_day_without_service)

    self.accumulator.AssertNoMoreExceptions()


class FeedInfoServiceGapsTestCase(util.MemoryZipTestCase):
  """Test for service gaps introduced by feed_info.txt start end dates."""
  
  def setUp(self):
    super(FeedInfoServiceGapsTestCase, self).setUp()
    self.SetArchiveContents("calendar.txt",
                      "service_id,monday,tuesday,wednesday,thursday,friday,"
                      "saturday,sunday,start_date,end_date\n"
                      "FULLW,1,1,1,1,1,1,1,20090601,20090610\n")
    self.SetArchiveContents("trips.txt",
                      "route_id,service_id,trip_id\n"
                      "AB,FULLW,AB1\n")
    self.SetArchiveContents(
        "stop_times.txt",
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "AB1,10:00:00,10:00:00,BEATTY_AIRPORT,1\n"
        "AB1,10:20:00,10:20:00,BULLFROG,2\n"
        "AB1,10:25:00,10:25:00,STAGECOACH,3\n")
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang,"
        "feed_start_date,feed_end_date\n"
        "DTA,http://google.com,en,20090515,20090620")

    self.schedule = self.MakeLoaderAndLoad(extra_validation=False)

  # If there is a service gap starting before today, and today has no service,
  # it should be found - even if tomorrow there is service
  def testServiceGapBeforeTodayIsDiscovered(self):
    self.schedule.Validate(today=date(2009, 6, 5),
                           service_gap_interval=7)
    exception = self.accumulator.PopException("TooManyDaysWithoutService")
    self.assertEquals(date(2009, 6, 11),
                      exception.first_day_without_service)
    self.assertEquals(date(2009, 6, 19),
                      exception.last_day_without_service)
    self.accumulator.AssertNoMoreExceptions()


class DeprecatedFieldNamesTestCase(util.MemoryZipTestCase):

  # create class extensions and change fields to be deprecated
  class Agency(transitfeed.Agency):
    _DEPRECATED_FIELD_NAMES = transitfeed.Agency._DEPRECATED_FIELD_NAMES[:]
    _DEPRECATED_FIELD_NAMES.append(('agency_url', None))
    _REQUIRED_FIELD_NAMES = transitfeed.Agency._REQUIRED_FIELD_NAMES[:]
    _REQUIRED_FIELD_NAMES.remove('agency_url')
    _FIELD_NAMES = transitfeed.Agency._FIELD_NAMES[:]
    _FIELD_NAMES.remove('agency_url')

  class Stop(transitfeed.Stop):
    _DEPRECATED_FIELD_NAMES = transitfeed.Stop._DEPRECATED_FIELD_NAMES[:]
    _DEPRECATED_FIELD_NAMES.append(('stop_desc', None))
    _FIELD_NAMES = transitfeed.Stop._FIELD_NAMES[:]
    _FIELD_NAMES.remove('stop_desc')

  def setUp(self):
    super(DeprecatedFieldNamesTestCase, self).setUp()
    # init a new gtfs_factory instance and update its class mappings
    self.gtfs_factory = transitfeed.GetGtfsFactory()
    self.gtfs_factory.UpdateClass('Agency', self.Agency)
    self.gtfs_factory.UpdateClass('Stop', self.Stop)

  def testDeprectatedFieldNames(self):
    self.SetArchiveContents(
        "agency.txt",
        "agency_id,agency_name,agency_timezone,agency_url\n"
        "DTA,Demo Agency,America/Los_Angeles,http://google.com\n")
    schedule = self.MakeLoaderAndLoad(self.problems,
                                      gtfs_factory=self.gtfs_factory)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("agency_url", e.column_name)
    self.accumulator.AssertNoMoreExceptions()

  def testDeprecatedFieldDefaultsToNoneIfNotProvided(self):
    # load agency.txt with no 'agency_url', accessing the variable agency_url
    # should default to None instead of raising an AttributeError
    self.SetArchiveContents(
        "agency.txt",
        "agency_id,agency_name,agency_timezone\n"
        "DTA,Demo Agency,America/Los_Angeles\n")
    schedule = self.MakeLoaderAndLoad(self.problems,
                                      gtfs_factory=self.gtfs_factory)
    agency = schedule._agencies.values()[0]
    self.assertTrue(agency.agency_url == None)
    # stop.txt from util.MemoryZipTestCase does not have 'stop_desc', accessing
    # the variable stop_desc should default to None instead of raising an
    # AttributeError
    stop = schedule.stops.values()[0]
    self.assertTrue(stop.stop_desc == None)
    self.accumulator.AssertNoMoreExceptions()


class TestGtfsFactory(util.TestCase):

  def setUp(self):
    self._factory = transitfeed.GetGtfsFactory()

  def testCanUpdateMapping(self):
    self._factory.UpdateMapping("agency.txt",
                                {"required": False,
                                 "classes": ["Foo"]})
    self._factory.RemoveClass("Agency")
    self._factory.AddClass("Foo", transitfeed.Stop)
    self._factory.UpdateMapping("calendar.txt",
                                {"loading_order":-4, "classes": ["Bar"]})
    self._factory.AddClass("Bar", transitfeed.ServicePeriod)
    self.assertFalse(self._factory.IsFileRequired("agency.txt"))
    self.assertFalse(self._factory.IsFileRequired("calendar.txt"))
    self.assertTrue(self._factory.GetLoadingOrder()[0] == "calendar.txt")
    self.assertEqual(self._factory.Foo, transitfeed.Stop)
    self.assertEqual(self._factory.Bar, transitfeed.ServicePeriod)
    self.assertEqual(self._factory.GetGtfsClassByFileName("agency.txt"),
                     transitfeed.Stop)
    self.assertFalse(self._factory.IsFileRequired("agency.txt"))
    known_filenames = self._factory.GetKnownFilenames()
    self.assertTrue("agency.txt" in known_filenames)
    self.assertTrue("calendar.txt" in known_filenames)

  def testCanAddMapping(self):
    self._factory.AddMapping("newrequiredfile.txt",
                             { "required":True, "classes": ["NewRequiredClass"],
                               "loading_order":-20})
    self._factory.AddClass("NewRequiredClass", transitfeed.Stop)
    self._factory.AddMapping("newfile.txt",
                             { "required": False, "classes": ["NewClass"],
                               "loading_order":-10})
    self._factory.AddClass("NewClass", transitfeed.FareAttribute)
    self.assertEqual(self._factory.NewClass, transitfeed.FareAttribute)
    self.assertEqual(self._factory.NewRequiredClass, transitfeed.Stop)
    self.assertTrue(self._factory.IsFileRequired("newrequiredfile.txt"))
    self.assertFalse(self._factory.IsFileRequired("newfile.txt"))
    known_filenames = self._factory.GetKnownFilenames()
    self.assertTrue("newfile.txt" in known_filenames)
    self.assertTrue("newrequiredfile.txt" in known_filenames)
    loading_order = self._factory.GetLoadingOrder()
    self.assertTrue(loading_order[0] == "newrequiredfile.txt")
    self.assertTrue(loading_order[1] == "newfile.txt")

  def testThrowsExceptionWhenAddingDuplicateMapping(self):
    self.assertRaises(transitfeed.DuplicateMapping,
                      self._factory.AddMapping,
                      "agency.txt",
                      {"required": True, "classes": ["Stop"],
                       "loading_order":-20})

  def testThrowsExceptionWhenAddingInvalidMapping(self):
    self.assertRaises(transitfeed.InvalidMapping,
                      self._factory.AddMapping,
                      "foo.txt",
                      {"required": True,
                       "loading_order":-20})

  def testThrowsExceptionWhenUpdatingNonexistentMapping(self):
    self.assertRaises(transitfeed.NonexistentMapping,
                      self._factory.UpdateMapping,
                      'doesnotexist.txt',
                      {'required': False})


  def testCanRemoveFileFromLoadingOrder(self):
    self._factory.UpdateMapping("agency.txt",
                                {"loading_order": None})
    self.assertTrue("agency.txt" not in self._factory.GetLoadingOrder())

  def testCanRemoveMapping(self):
    self._factory.RemoveMapping("agency.txt")
    self.assertFalse("agency.txt" in self._factory.GetKnownFilenames())
    self.assertFalse("agency.txt" in self._factory.GetLoadingOrder())
    self.assertEqual(self._factory.GetGtfsClassByFileName("agency.txt"),
                     None)
    self.assertFalse(self._factory.IsFileRequired("agency.txt"))

  def testIsFileRequired(self):
    self.assertTrue(self._factory.IsFileRequired("agency.txt"))
    self.assertTrue(self._factory.IsFileRequired("stops.txt"))
    self.assertTrue(self._factory.IsFileRequired("routes.txt"))
    self.assertTrue(self._factory.IsFileRequired("trips.txt"))
    self.assertTrue(self._factory.IsFileRequired("stop_times.txt"))

    # We don't have yet a way to specify that one or the other (or both
    # simultaneously) might be provided, so we don't consider them as required
    # for now
    self.assertFalse(self._factory.IsFileRequired("calendar.txt"))
    self.assertFalse(self._factory.IsFileRequired("calendar_dates.txt"))

    self.assertFalse(self._factory.IsFileRequired("fare_attributes.txt"))
    self.assertFalse(self._factory.IsFileRequired("fare_rules.txt"))
    self.assertFalse(self._factory.IsFileRequired("shapes.txt"))
    self.assertFalse(self._factory.IsFileRequired("frequencies.txt"))
    self.assertFalse(self._factory.IsFileRequired("transfers.txt"))

  def testFactoryReturnsClassesAndNotInstances(self):
    for filename in ("agency.txt", "fare_attributes.txt",
        "fare_rules.txt", "frequencies.txt", "stops.txt", "stop_times.txt",
        "transfers.txt", "routes.txt", "trips.txt"):
      class_object = self._factory.GetGtfsClassByFileName(filename)
      self.assertTrue(isinstance(class_object,
                                 (types.TypeType, types.ClassType)),
                      "The mapping from filenames to classes must return "
                      "classes and not instances. This is not the case for " +
                      filename)

  def testCanFindClassByClassName(self):
    self.assertEqual(transitfeed.Agency, self._factory.Agency)
    self.assertEqual(transitfeed.FareAttribute, self._factory.FareAttribute)
    self.assertEqual(transitfeed.FareRule, self._factory.FareRule)
    self.assertEqual(transitfeed.Frequency, self._factory.Frequency)
    self.assertEqual(transitfeed.Route, self._factory.Route)
    self.assertEqual(transitfeed.ServicePeriod, self._factory.ServicePeriod)
    self.assertEqual(transitfeed.Shape, self._factory.Shape)
    self.assertEqual(transitfeed.ShapePoint, self._factory.ShapePoint)
    self.assertEqual(transitfeed.Stop, self._factory.Stop)
    self.assertEqual(transitfeed.StopTime, self._factory.StopTime)
    self.assertEqual(transitfeed.Transfer, self._factory.Transfer)
    self.assertEqual(transitfeed.Trip, self._factory.Trip)

  def testCanFindClassByFileName(self):
    self.assertEqual(transitfeed.Agency,
                     self._factory.GetGtfsClassByFileName('agency.txt'))
    self.assertEqual(transitfeed.FareAttribute,
                     self._factory.GetGtfsClassByFileName(
                         'fare_attributes.txt'))
    self.assertEqual(transitfeed.FareRule,
                     self._factory.GetGtfsClassByFileName('fare_rules.txt'))
    self.assertEqual(transitfeed.Frequency,
                     self._factory.GetGtfsClassByFileName('frequencies.txt'))
    self.assertEqual(transitfeed.Route,
                     self._factory.GetGtfsClassByFileName('routes.txt'))
    self.assertEqual(transitfeed.ServicePeriod,
                     self._factory.GetGtfsClassByFileName('calendar.txt'))
    self.assertEqual(transitfeed.ServicePeriod,
                     self._factory.GetGtfsClassByFileName('calendar_dates.txt'))
    self.assertEqual(transitfeed.Stop,
                     self._factory.GetGtfsClassByFileName('stops.txt'))
    self.assertEqual(transitfeed.StopTime,
                     self._factory.GetGtfsClassByFileName('stop_times.txt'))
    self.assertEqual(transitfeed.Transfer,
                     self._factory.GetGtfsClassByFileName('transfers.txt'))
    self.assertEqual(transitfeed.Trip,
                     self._factory.GetGtfsClassByFileName('trips.txt'))

  def testClassFunctionsRaiseExceptions(self):
    self.assertRaises(transitfeed.NonexistentMapping,
                      self._factory.RemoveClass,
                      "Agenci")
    self.assertRaises(transitfeed.DuplicateMapping,
                      self._factory.AddClass,
                      "Agency", transitfeed.Agency)
    self.assertRaises(transitfeed.NonStandardMapping,
                      self._factory.GetGtfsClassByFileName,
                      'shapes.txt')
    self.assertRaises(transitfeed.NonexistentMapping,
                      self._factory.UpdateClass,
                      "Agenci", transitfeed.Agency)


class TestGtfsFactoryUser(util.TestCase):
  def AssertDefaultFactoryIsReturnedIfNoneIsSet(self, instance):
    self.assertTrue(isinstance(instance.GetGtfsFactory(),
                               transitfeed.GtfsFactory))

  def AssertFactoryIsSavedAndReturned(self, instance, factory):
    instance.SetGtfsFactory(factory)
    self.assertEquals(factory, instance.GetGtfsFactory())

  def testClasses(self):
    class FakeGtfsFactory(object):
      pass

    factory = transitfeed.GetGtfsFactory()
    gtfs_class_instances = [
        factory.Shape("id"),
        factory.ShapePoint(),
    ]
    gtfs_class_instances += [factory.GetGtfsClassByFileName(filename)() for
                             filename in factory.GetLoadingOrder()]

    for instance in gtfs_class_instances:
      self.AssertDefaultFactoryIsReturnedIfNoneIsSet(instance)
      self.AssertFactoryIsSavedAndReturned(instance, FakeGtfsFactory())


class TooManyConsecutiveStopTimesWithSameTime(util.TestCase):
  """Check for too many consecutive stop times with same time"""

  def setUp(self):

    # We ignore the lack of service dates ("OtherProblem")
    self.accumulator = RecordingProblemAccumulator(
        self, ("OtherProblem"))
    self.problems = transitfeed.ProblemReporter(self.accumulator)

    self.schedule = transitfeed.Schedule(problem_reporter=self.problems)
    self.schedule.AddAgency("Demo Transit Authority", "http://dta.org",
                            "America/Los_Angeles")

    self.stop1 = self.schedule.AddStop(lng=-116.75167,
                                       lat=36.915682,
                                       name="Stagecoach Hotel & Casino",
                                       stop_id="S1")

    self.stop2 = self.schedule.AddStop(lng=-116.76218,
                                       lat=36.905697,
                                       name="E Main St / S Irving St",
                                       stop_id="S2")

    route = self.schedule.AddRoute("", "City", "Bus", route_id="CITY")

    self.trip = route.AddTrip(self.schedule, trip_id="CITY1")

  def testTooManyConsecutiveStopTimesWithSameTime(self):
    trip = self.trip
    trip.AddStopTime(self.stop1, stop_time="6:00:00")
    for _ in range(6):
      trip.AddStopTime(self.stop2, stop_time="6:05:00")
    trip.AddStopTime(self.stop1, stop_time="6:10:00")

    self.schedule.Validate(self.problems)

    e = self.accumulator.PopException('TooManyConsecutiveStopTimesWithSameTime')
    self.assertEqual(e.trip_id, 'CITY1')
    self.assertEqual(e.number_of_stop_times, 6)
    self.assertEqual(e.stop_time, '06:05:00')

    self.assertEqual(e.FormatProblem(),
        "Trip CITY1 has 6 consecutive stop times all with the same " \
        "arrival/departure time: 06:05:00.")

    self.accumulator.AssertNoMoreExceptions()

  def testNotTooManyConsecutiveStopTimesWithSameTime(self):
    trip = self.trip
    trip.AddStopTime(self.stop1, stop_time="6:00:00")
    for _ in range(5):
      trip.AddStopTime(self.stop2, stop_time="6:05:00")
    trip.AddStopTime(self.stop1, stop_time="6:10:00")

    self.schedule.Validate(self.problems)

    self.accumulator.AssertNoMoreExceptions()

  def testTooManyConsecutiveStopTimesWithSameTimeAtStart(self):
    trip = self.trip
    for _ in range(6):
      trip.AddStopTime(self.stop2, stop_time="6:05:00")
    trip.AddStopTime(self.stop1, stop_time="6:10:00")

    self.schedule.Validate(self.problems)

    e = self.accumulator.PopException('TooManyConsecutiveStopTimesWithSameTime')
    self.assertEqual(e.trip_id, 'CITY1')
    self.assertEqual(e.number_of_stop_times, 6)
    self.assertEqual(e.stop_time, '06:05:00')

    self.accumulator.AssertNoMoreExceptions()

  def testTooManyConsecutiveStopTimesWithSameTimeAtEnd(self):
    trip = self.trip
    trip.AddStopTime(self.stop1, stop_time="6:00:00")
    for _ in range(6):
      trip.AddStopTime(self.stop2, stop_time="6:05:00")

    self.schedule.Validate(self.problems)

    e = self.accumulator.PopException('TooManyConsecutiveStopTimesWithSameTime')
    self.assertEqual(e.trip_id, 'CITY1')
    self.assertEqual(e.number_of_stop_times, 6)
    self.assertEqual(e.stop_time, '06:05:00')

    self.accumulator.AssertNoMoreExceptions()

  def testTooManyConsecutiveStopTimesWithUnspecifiedTimes(self):
    trip = self.trip
    trip.AddStopTime(self.stop1, stop_time="6:05:00")
    for _ in range(4):
      trip.AddStopTime(self.stop2)
    trip.AddStopTime(self.stop1, stop_time="6:05:00")

    self.schedule.Validate(self.problems)

    e = self.accumulator.PopException('TooManyConsecutiveStopTimesWithSameTime')
    self.assertEqual(e.trip_id, 'CITY1')
    self.assertEqual(e.number_of_stop_times, 6)
    self.assertEqual(e.stop_time, '06:05:00')

    self.accumulator.AssertNoMoreExceptions()

  def testNotTooManyConsecutiveStopTimesWithUnspecifiedTimes(self):
    trip = self.trip
    trip.AddStopTime(self.stop1, stop_time="6:00:00")
    for _ in range(4):
      trip.AddStopTime(self.stop2)
    trip.AddStopTime(self.stop1, stop_time="6:05:00")

    self.schedule.Validate(self.problems)

    self.accumulator.AssertNoMoreExceptions()


class FeedInfoTestCase(util.MemoryZipTestCase):

  def setUp(self):
    super(FeedInfoTestCase, self).setUp()
    # Modify agency.txt for all tests in this test case
    self.SetArchiveContents("agency.txt",
        "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
        "DTA,Demo Agency,http://google.com,America/Los_Angeles,en\n")

  def testNoErrors(self):
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang\n"
        "DTA,http://google.com,en")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testDifferentLanguage(self):
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang\n"
        "DTA,http://google.com,pt")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.PopInvalidValue("feed_lang")
    self.accumulator.AssertNoMoreExceptions()

  def testInvalidPublisherUrl(self):
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang\n"
        "DTA,htttp://google.com,en")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.PopInvalidValue("feed_publisher_url")
    self.accumulator.AssertNoMoreExceptions()

  def testValidityDatesNoErrors(self):
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang,"
        "feed_start_date,feed_end_date\n"
        "DTA,http://google.com,en,20101201,20101231")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testValidityDatesInvalid(self):
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang,"
        "feed_start_date,feed_end_date\n"
        "DTA,http://google.com,en,10/01/12,10/31/12")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.PopInvalidValue("feed_start_date")
    self.accumulator.PopInvalidValue("feed_end_date")
    self.accumulator.AssertNoMoreExceptions()

  def testValidityDatesInverted(self):
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_lang,"
        "feed_start_date,feed_end_date\n"
        "DTA,http://google.com,en,20101231,20101201")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.PopInvalidValue("feed_end_date")
    self.accumulator.AssertNoMoreExceptions()

  def testDeprectatedFieldNames(self):
    self.SetArchiveContents("feed_info.txt",
        "feed_publisher_name,feed_publisher_url,feed_timezone,feed_lang,"
        "feed_valid_from,feed_valid_until\n"
        "DTA,http://google.com,America/Los_Angeles,en,20101201,20101231")
    self.MakeLoaderAndLoad(self.problems)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("feed_valid_from", e.column_name)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("feed_valid_until", e.column_name)
    e = self.accumulator.PopException("DeprecatedColumn")
    self.assertEquals("feed_timezone", e.column_name)        
    self.accumulator.AssertNoMoreExceptions()


class MultiAgencyTimeZoneTestCase(util.MemoryZipTestCase):
  
  def testNoErrorsWithAgenciesHavingSameTimeZone(self):
    self.SetArchiveContents("agency.txt",
        "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
        "DTA,Demo Agency,http://google.com,America/Los_Angeles,en\n"
        "DTA2,Demo Agency 2,http://google.com,America/Los_Angeles,en\n")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.AssertNoMoreExceptions()

  def testAgenciesWithDifferentTimeZone(self):
    self.SetArchiveContents("agency.txt",
        "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
        "DTA,Demo Agency,http://google.com,America/Los_Angeles,en\n"
        "DTA2,Demo Agency 2,http://google.com,America/New_York,en\n")
    self.MakeLoaderAndLoad(self.problems)
    self.accumulator.PopInvalidValue("agency_timezone")
    self.accumulator.AssertNoMoreExceptions()


if __name__ == '__main__':
  unittest.main()
