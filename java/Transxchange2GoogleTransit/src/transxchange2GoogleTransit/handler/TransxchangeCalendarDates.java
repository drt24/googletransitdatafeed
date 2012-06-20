/*
 * Copyright 2007, 2008, 2009, 2010, 2011, 2012 GoogleTransitDataFeed
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */

package transxchange2GoogleTransit.handler;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.GregorianCalendar;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.logging.Logger;

import org.xml.sax.Attributes;
import org.xml.sax.SAXParseException;

import transxchange2GoogleTransit.CalendarDate;
import transxchange2GoogleTransit.EXCEPTION;
import transxchange2GoogleTransit.Util;

/*
 * This class handles the TransXChange xml input file under the aspect of
 * 	calendar dates which might have been excluded from or added to a service
 */
public class TransxchangeCalendarDates extends TransxchangeDataAspect {

  private static class KeyCalendar{
    public final String key = "Service";
    public final String keyType;
    public final String operationMode;
    public final String qualifier;
    public final EXCEPTION exception;
    public KeyCalendar(String keyType, String operationMode, String qualifier, EXCEPTION exception){
      this.keyType = keyType;
      this.operationMode = operationMode;
      this.qualifier = qualifier;
      this.exception = exception;
    }
  }
  private static final Logger log = Logger.getLogger(TransxchangeCalendarDates.class.getCanonicalName());
	// xml keys and output field fillers
	static final String[] key_calendar_dates__service_id = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	static final String[] key_calendar_dates__date = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	static final String[] key_calendar_dates__exception_type = new String[] {"__transxchange2GTFS_drawDefault", "", ""};

	// Parsed data
	Set<CalendarDate> entries = new TreeSet<CalendarDate>();
	List<ValueList> listCalendar_OOL_start_date = null; // Out-of-line date range start date. A out-of-line date range is a date range which is not associated to a service
	List<ValueList> listCalendar_OOL_end_date = null;  // Out-of-line date range end date
	List<EXCEPTION> listCalendar_OOL_exception_type = null;  // Out-of-line date range end date

	// XML markups
	static final KeyCalendar dates_start = new KeyCalendar("SpecialDaysOperation", "DaysOfOperation", "StartDate", EXCEPTION.ADD);
	static final KeyCalendar dates_end = new KeyCalendar("SpecialDaysOperation", "DaysOfOperation", "EndDate", EXCEPTION.ADD);
	static final KeyCalendar no_dates_start = new KeyCalendar("SpecialDaysOperation", "DaysOfNonOperation", "StartDate", EXCEPTION.REMOVE);
	static final KeyCalendar no_dates_end = new KeyCalendar("SpecialDaysOperation", "DaysOfNonOperation", "EndDate", EXCEPTION.REMOVE);

	// Bank holiday XML markups
	static final KeyCalendar bankholiday_operation_spring = new KeyCalendar("BankHolidayOperation", "DaysOfOperation", "SpringHoliday", EXCEPTION.ADD);
	static final KeyCalendar bankholiday_nooperation_all = new KeyCalendar("BankHolidayOperation", "DaysOfNonOperation", "AllBankHolidays", EXCEPTION.REMOVE);
	static final KeyCalendar bankholiday_operation_all = new KeyCalendar("BankHolidayOperation", "DaysOfOperation", "AllBankHolidays", EXCEPTION.ADD);

	// Parse keys
	String keyOperationDays = "";
	String keyOperationDaysStart = "";
	String keyOperationDaysBank = ""; // key for bank holidays
	String keyOperationDaysType = "";

	// Some support variables
	String calendarDateOperationDayStart = "";
	boolean dayOfNoOperation = false;

	// Bank holidays support map
	/**
	 * Map of year to map of holiday name to holiday date
	 */
	Map<Integer, Map<String, String>> years = new HashMap<Integer, Map<String, String>>(); //  years as HashMap to maintain unique entries
//V1.6.3 ArrayList to dynamically create the years covered by the service
 //private ArrayList<?> bankHolidays;
	List<Integer> yearsList = new ArrayList<Integer>(); // years as list to allow iterating through years

	/*
	 * Utility methods to retrieve GTFS feed structures
	 */

  /**
   * 
   * @return the entries in for the calendar dates table
   */
  public Set<CalendarDate> getCalendarDates() {
    return entries;
  }

	/** Out-of-line dates start*/
	public List<ValueList> getListOOLDates_start() {
		return listCalendar_OOL_start_date;
	}

	/** Out-of-line dates end */
	public List<ValueList> getListOOLDates_end() {
		return listCalendar_OOL_end_date;
	}

	/** Reset out-of-line date list */
	public void resetOOLDates_start() {
		listCalendar_OOL_start_date = null;
	}

	/** Reset out-of-line date list */
	public void resetOOLDates_end() {
		listCalendar_OOL_end_date = null;
	}

   	@Override
	public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException {

	    super.startElement(uri, name, qName, atts);
	    if (qName.equals(dates_start.key)) // also covers no_dates and bank holidays
			key = dates_start.key;
	    if (key.equals(dates_start.key) && qName.equals(dates_start.keyType) && keyOperationDays.length() == 0) {
	    	keyNested = dates_start.keyType;
	    }
	    if (key.equals(dates_start.key) && keyNested.equals(dates_start.keyType) && qName.equals(dates_start.operationMode)) {
	    	keyOperationDays = dates_start.operationMode;
	    }
	    if (key.equals(dates_start.key) && keyNested.equals(dates_start.keyType) && keyOperationDays.equals(dates_start.operationMode) && qName.equals(dates_start.qualifier)) {
	    	keyOperationDaysStart = dates_start.qualifier;
	    	niceString = "";
	    	dayOfNoOperation = false;
	    }
	    if (key.equals(dates_end.key) && keyNested.equals(dates_end.keyType) && keyOperationDays.equals(dates_end.operationMode) && qName.equals(dates_end.qualifier)) {
	    	keyOperationDaysStart = dates_end.qualifier;
	    	niceString = "";
	    }
	    if (key.equals(no_dates_start.key) && keyNested.equals(no_dates_start.keyType) && qName.equals(no_dates_start.operationMode)) {
	    	keyOperationDays = no_dates_start.operationMode;
	    }
	    if (key.equals(no_dates_start.key) && keyNested.equals(no_dates_start.keyType) && keyOperationDays.equals(no_dates_start.operationMode) && qName.equals(no_dates_start.qualifier)) {
	    	keyOperationDaysStart = no_dates_start.qualifier; // equals operation day
	    	niceString = "";
	    	dayOfNoOperation = true;
	    }
	    if (key.equals(no_dates_end.key) && keyNested.equals(no_dates_end.keyType) && keyOperationDays.equals(no_dates_end.operationMode) && qName.equals(no_dates_end.qualifier)) {
	    	keyOperationDaysStart = no_dates_end.qualifier; // equals operation day
	    	niceString = "";
	    }

	    // Bank holiday keys
	    // Non Operation (All Holidays)
	    if (key.equals(bankholiday_nooperation_all.key) && qName.equals(bankholiday_nooperation_all.keyType)) // also covers all other bank holiday cases
	    	keyNested = bankholiday_nooperation_all.keyType;
	    if (key.equals(bankholiday_nooperation_all.key) && keyNested.equals(bankholiday_nooperation_all.keyType) && qName.equals(bankholiday_nooperation_all.operationMode))
	    	keyOperationDaysBank = bankholiday_nooperation_all.operationMode;

	    // Operation (Spring Holidays)
	    if (key.equals(bankholiday_operation_spring.key) && keyNested.equals(bankholiday_operation_spring.keyType) && qName.equals(bankholiday_operation_spring.operationMode)){
	    	keyOperationDaysBank = bankholiday_operation_spring.operationMode;
	    	if (qName.equals(bankholiday_operation_all.operationMode)){
	    	  // Otherwise this will never be reached as the first three elements of _key_calendar_bankholiday_oper_key_calendar_bankholiday_operation_spring[0]ation_spring and _key_calendar_bankholiday_operation_all are the same
	    	  keyOperationDaysType = bankholiday_operation_all.qualifier;
	    	}
	    } else {
		    // Operation (All Holidays)
		    if (key.equals(bankholiday_operation_all.key) && qName.equals(bankholiday_operation_all.keyType))
		    	keyNested = bankholiday_operation_all.keyType;
		    if (key.equals(bankholiday_operation_all.key) && keyNested.equals(bankholiday_operation_all.keyType) && qName.equals(bankholiday_operation_all.operationMode))
		    	keyOperationDaysBank = bankholiday_operation_all.operationMode;
		    if (key.equals(bankholiday_operation_all.key) && keyNested.equals(bankholiday_operation_all.keyType)
		    		&& keyOperationDaysBank.equals(bankholiday_operation_all.operationMode)
		    		&& qName.equals(bankholiday_operation_all.qualifier))
		    	keyOperationDaysType = bankholiday_operation_all.qualifier;
	    }
	}

   	@Override
   	public void endElement (String uri, String name, String qName) {

   	  if (niceString == null || niceString.length() > 0) {

   	    if (key.equals(dates_start.key) && keyNested.equals(dates_start.keyType) && (keyOperationDays.equals(dates_start.operationMode) || keyOperationDays.equals(no_dates_end.operationMode)) && keyOperationDaysStart.equals(dates_start.qualifier))
   	      calendarDateOperationDayStart = niceString;
   	    if (key.equals(dates_end.key) && keyNested.equals(dates_end.keyType) && (keyOperationDays.equals(dates_end.operationMode) || keyOperationDays.equals(no_dates_end.operationMode)) && keyOperationDaysStart.equals(dates_end.qualifier)) {
   	      try {
   	        SimpleDateFormat sdfIn = new SimpleDateFormat("yyyy-MM-dd", Locale.US); // US - determined by location of Google Labs, not transit operator
   	        sdfIn.setCalendar(Calendar.getInstance());
   	        Date calendarDatesOperationDay = sdfIn.parse(calendarDateOperationDayStart);
   	        Date calendarDateOperationDayEnd = sdfIn.parse(niceString);
   	        GregorianCalendar gcOperationDay = new GregorianCalendar();
   	        gcOperationDay.setTime(calendarDatesOperationDay);
   	        String service = handler.getCalendar().getService();
   	        if (service.length() == 0) { // Out-of-line OperatingProfile? E.g. special operations days for a single vehicle journey as opposed for a service.
   	          if (listCalendar_OOL_start_date == null)
   	            listCalendar_OOL_start_date = new ArrayList<ValueList>(); // If previously found OOL dates were read and reset some place else, recreate list
   	          if (listCalendar_OOL_end_date == null)
   	            listCalendar_OOL_end_date = new ArrayList<ValueList>();
   	          if (listCalendar_OOL_exception_type == null)
   	            listCalendar_OOL_exception_type = new ArrayList<EXCEPTION>();
   	          ValueList newCalendar_OOL_start_date = new ValueList(dates_start.key);
   	          listCalendar_OOL_start_date.add(newCalendar_OOL_start_date);
   	          newCalendar_OOL_start_date.addValue(Util.formatDate(gcOperationDay.get(Calendar.YEAR), gcOperationDay.get(Calendar.MONTH) + 1, gcOperationDay.get(Calendar.DAY_OF_MONTH)));
   	          gcOperationDay.setTime(calendarDateOperationDayEnd);
   	          ValueList newCalendar_OOL_end_date = new ValueList(dates_end.key);
   	          listCalendar_OOL_end_date.add(newCalendar_OOL_end_date);
   	          newCalendar_OOL_end_date.addValue(Util.formatDate(gcOperationDay.get(Calendar.YEAR), gcOperationDay.get(Calendar.MONTH) + 1, gcOperationDay.get(Calendar.DAY_OF_MONTH)));
   	          
   	          if (dayOfNoOperation)
   	           listCalendar_OOL_exception_type.add(no_dates_start.exception);
   	          else
   	           listCalendar_OOL_exception_type.add(dates_start.exception);
          } else {
            while (calendarDatesOperationDay.compareTo(calendarDateOperationDayEnd) <= 0) {
              EXCEPTION exceptionType = null;
              if (dayOfNoOperation) {
                exceptionType = no_dates_start.exception;
              } else {
                exceptionType = dates_start.exception;
              }
              CalendarDate entry =
                  new CalendarDate(service, Util.formatDate(gcOperationDay.get(Calendar.YEAR),
                      gcOperationDay.get(Calendar.MONTH) + 1, gcOperationDay.get(Calendar.DAY_OF_MONTH)), exceptionType);
              entries.add(entry);
              gcOperationDay.add(Calendar.DAY_OF_YEAR, 1);
              calendarDatesOperationDay = gcOperationDay.getTime();
            }
          }
   	      } catch (Exception e) {
   	        handler.setParseError(e);
   	      }
   	    }
   	  } else {

   	    // v1.6.3: Roll out years covered by the service
   	    TransxchangeCalendar calendar = handler.getCalendar();
   	    int startYear = calendar.getStartYear();
   	    int endYear = calendar.getEndYear();
   	    if (startYear != -1 && endYear != -1 && endYear >= startYear && yearsList.size() == 0) {
   	      for (int year = startYear; year <= endYear; year++)
   	        if (!years.containsKey(year)) {
   	          years.put(year, createHolidays(year));
   	          yearsList.add(year);
   	        }
   	    }

   	    String service = calendar.getService();

   	    // v.1.7.4: Bug fix: correctly dereference service ID if not determined in global call above
   	    if (service == null || service.length() == 0) {
   	      List<ValueList> serviceIds = calendar.getListCalendar__service_id();
   	      service = "";
   	      if (serviceIds.size() > 0) {
   	        service = serviceIds.get(0).getValue(0);//TODO(drt24) fairly confident that this must be a bug
   	      }
   	    }

   	    if (!service.equals("")) {
   	      Map<String, String> holidays;
   	      for (int year : yearsList) {
   	        holidays = years.get(year);
   	        // Non Operating Holidays
   	        if (key.equals(bankholiday_nooperation_all.key) && keyNested.equals(bankholiday_nooperation_all.keyType) && keyOperationDaysBank.equals(bankholiday_nooperation_all.operationMode))
   	          createBankHolidaysAll(service, holidays, bankholiday_nooperation_all.exception);

   	        // Operating Holidays
   	        if (key.equals(bankholiday_operation_all.key) && keyNested.equals(bankholiday_operation_all.keyType)
   	            && keyOperationDaysBank.equals(bankholiday_operation_all.operationMode)
   	            && keyOperationDaysType.equals(bankholiday_operation_all.qualifier)) {
   	          createBankHolidaysAll(service, holidays, bankholiday_operation_all.exception);
   	        } else {
   	          if (key.equals(bankholiday_operation_spring.key) && keyNested.equals(bankholiday_operation_spring.keyType) && keyOperationDaysBank.equals(bankholiday_operation_spring.operationMode))
   	            createBankHoliday(service, qName, holidays, bankholiday_operation_spring.exception);
   	        }
   	      }
   	    }
   	  }
   	}

   	@Override
	public void clearKeys (String qName) {
	    if (key.equals(dates_end.key) && keyNested.equals(dates_end.keyType) && (keyOperationDays.equals(dates_end.operationMode) || keyOperationDays.equals(no_dates_end.operationMode))&& keyOperationDaysStart.equals(dates_end.qualifier))
	    	keyOperationDaysStart = "";
	    	else
	    		if (key.equals(dates_end.key) && keyNested.equals(dates_end.keyType) && (keyOperationDays.equals(dates_end.operationMode) || keyOperationDays.equals(no_dates_end.operationMode)) && keyOperationDaysStart.length() == 0 && (qName.equals(dates_start.operationMode) || qName.equals(no_dates_start.operationMode)))
	    			keyOperationDays = "";

	    if (key.equals(bankholiday_nooperation_all.key) && keyNested.equals(bankholiday_nooperation_all.keyType) && keyOperationDaysBank.equals(bankholiday_nooperation_all.operationMode)) {
   			keyOperationDaysBank = "";
   			keyOperationDaysType= "";
	    }
	    if (key.equals(bankholiday_operation_spring.key) && keyNested.equals(bankholiday_operation_spring.keyType) && keyOperationDaysBank.equals(bankholiday_operation_spring.operationMode)) {
   			keyOperationDaysBank = "";
   			keyOperationDaysType = "";
	    } else
		    if (key.equals(bankholiday_operation_all.key) && keyNested.equals(bankholiday_operation_all.keyType) && keyOperationDaysBank.equals(bankholiday_operation_all.operationMode)) {
	   			keyOperationDaysBank = "";
	   			keyOperationDaysType = "";
		    }
	}

  @Override
  public void dumpValues() {
    System.out.println("*** Calendar dates");
    for (CalendarDate calendarDate : entries) {
      System.out.println(calendarDate);
    }
  }

	private Map<String, String> createHolidays(int year) {

		HashMap<String, String> bankHolidays = new HashMap<String, String>();

		// NewYearsDay - consider replacement holiday of January 1st falls on Saturday or Sunday
		Calendar newyearsDay = Calendar.getInstance();
		newyearsDay.set(year, 0, 1); // Java starts counting months at 0
		int dayOfWeek = newyearsDay.get(Calendar.DAY_OF_WEEK);
		String theDay;
		switch (dayOfWeek) {
			case Calendar.SATURDAY:
			theDay = "0103";
			break;
			case Calendar.SUNDAY:
			theDay = "0102";
			break;
			default:
			theDay = "0101";
			break;
		}
		bankHolidays.put("NewYearsDay", year + theDay);

		// GoodFriday and EasterMonday
		int a = year % 19;
		int b = year / 100;
		int c = year % 100;
		int d = b / 4;
		int e = b % 4;
		int f = ( b + 8 ) / 25;
		int g = ( b - f + 1 ) / 3;
		int h = ( 19 * a + b - d - g + 15 ) % 30;
		int i = c / 4;
		int k = c % 4;
		int l = (32 + 2 * e + 2 * i - h - k) % 7;
		int m = (a + 11 * h + 22 * l) / 451;
		int p = (h + l - 7 * m + 114) % 31;
		int month = ( h + l - 7 * m + 114 ) / 31;
		int day = p + 1;
		Calendar gc = Calendar.getInstance();
		gc.set(year, month, day);
		long easterSunday = gc.getTimeInMillis();
		long easterFriday = easterSunday - 2 * 24 * 60 * 60 * 1000; // Two days before Easter Sunday
		long easterMonday = easterSunday + 24 * 60 * 60 * 1000; // One day after Easter Sunday
		Calendar easterHoliday = Calendar.getInstance();
		easterHoliday.setTimeInMillis(easterFriday);
		bankHolidays.put("GoodFriday", Util.formatDate(easterHoliday.get(Calendar.YEAR), easterHoliday.get(Calendar.MONTH), easterHoliday.get(Calendar.DAY_OF_MONTH)));
		easterHoliday.setTimeInMillis(easterMonday);
		bankHolidays.put("EasterMonday", Util.formatDate(easterHoliday.get(Calendar.YEAR), easterHoliday.get(Calendar.MONTH), easterHoliday.get(Calendar.DAY_OF_MONTH)));

		// MayDay: First Monday in May
		Calendar mayDayHoliday = Calendar.getInstance();
		mayDayHoliday.set(Calendar.YEAR, year);
		mayDayHoliday.set(Calendar.MONTH, Calendar.MAY);
		mayDayHoliday.set(Calendar.DAY_OF_MONTH, 1);

		long mayDay = mayDayHoliday.getTimeInMillis();
		dayOfWeek = mayDayHoliday.get(Calendar.DAY_OF_WEEK);
		switch (dayOfWeek) {
			case Calendar.TUESDAY:
			mayDay += 6 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.WEDNESDAY:
			mayDay += 5 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.THURSDAY:
			mayDay += 4 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.FRIDAY:
			mayDay += 3 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.SATURDAY:
			mayDay += 2 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.SUNDAY:
			mayDay += 24 * 60 * 60 * 1000;
			break;
		}
		mayDayHoliday.setTimeInMillis(mayDay);
		bankHolidays.put("MayDay", Util.formatDate(mayDayHoliday.get(Calendar.YEAR),
			mayDayHoliday.get(Calendar.MONTH) + 1, // Java starts counting months at 0
			mayDayHoliday.get(Calendar.DAY_OF_MONTH)));

		// SpringBank: last Monday in May
		Calendar springBankHoliday = Calendar.getInstance();
		springBankHoliday.set(Calendar.YEAR, year);
		springBankHoliday.set(Calendar.MONTH, Calendar.MAY);
		springBankHoliday.set(Calendar.DAY_OF_MONTH, 31);

		long springBank = springBankHoliday.getTimeInMillis();
		dayOfWeek = springBankHoliday.get(Calendar.DAY_OF_WEEK);
		switch (dayOfWeek) {
			case Calendar.SUNDAY:
			springBank -= 6 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.SATURDAY:
			springBank -= 5 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.FRIDAY:
			springBank -= 4 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.THURSDAY:
			springBank -= 3 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.WEDNESDAY:
			springBank -= 2 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.TUESDAY:
			springBank -= 24 * 60 * 60 * 1000;
			break;
		}
		springBankHoliday.setTimeInMillis(springBank);
		bankHolidays.put("SpringBank", Util.formatDate(springBankHoliday.get(Calendar.YEAR),
			springBankHoliday.get(Calendar.MONTH) + 1, // Java starts counting months at 0
			springBankHoliday.get(Calendar.DAY_OF_MONTH)));

		// LateSummerHolidayNotScotland : last Monday in August
		Calendar lateSummerHoliday = Calendar.getInstance();
		lateSummerHoliday.set(Calendar.YEAR, year);
		lateSummerHoliday.set(Calendar.MONTH, Calendar.AUGUST);
		lateSummerHoliday.set(Calendar.DAY_OF_MONTH, 31);

		long summerHoliday = lateSummerHoliday.getTimeInMillis();
		dayOfWeek = lateSummerHoliday.get(Calendar.DAY_OF_WEEK);
		switch (dayOfWeek) {
			case Calendar.SUNDAY:
			summerHoliday -= 6 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.SATURDAY:
			summerHoliday -= 5 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.FRIDAY:
			summerHoliday -= 4 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.THURSDAY:
			summerHoliday -= 3 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.WEDNESDAY:
			summerHoliday -= 2 * 24 * 60 * 60 * 1000;
			break;
			case Calendar.TUESDAY:
			summerHoliday -= 24 * 60 * 60 * 1000;
			break;
		}
		lateSummerHoliday.setTimeInMillis(summerHoliday);
		bankHolidays.put("LateSummerBankHolidayNotScotland", Util.formatDate(lateSummerHoliday.get(Calendar.YEAR),
			lateSummerHoliday.get(Calendar.MONTH) + 1, // Java starts counting months at 0
			lateSummerHoliday.get(Calendar.DAY_OF_MONTH)));

		// ChristmasDay - consider replacement holiday for Christmas Day if it falls on a Saturday or Sunday
		Calendar christmasDay = Calendar.getInstance();
		christmasDay.set(year, 11, 25); // Java starts counting months at 0
		dayOfWeek = christmasDay.get(Calendar.DAY_OF_WEEK);
		switch (dayOfWeek) {
			case Calendar.SATURDAY:
			theDay = "1227";
			break;
			case Calendar.SUNDAY:
			theDay = "1227";
			break;
			default:
			theDay = "1225";
			break;
		}
		bankHolidays.put("ChristmasDay", year + theDay);

		// BoxingDay
		// ChristmasDay - consider replacement holiday for Boxing Day if it falls on a Saturday or Sunday
		Calendar boxingDay = Calendar.getInstance();
		boxingDay.set(year, 11, 26); // Java starts counting months at 0
		dayOfWeek = boxingDay.get(Calendar.DAY_OF_WEEK);
		switch (dayOfWeek) {
			case Calendar.SATURDAY:
			theDay = "1228";
			break;
			case Calendar.SUNDAY:
			theDay = "1228";
			break;
			default:
			theDay = "1226";
			break;
		}
		bankHolidays.put("BoxingDay", year + theDay);

		return bankHolidays;
	}

	public void calendarDatesRolloutOOLDates(String serviceId) {

		SimpleDateFormat sdfIn = new SimpleDateFormat("yyyyMMdd", Locale.US); // US - determined by location of Google Labs, not transit operator
		sdfIn.setCalendar(Calendar.getInstance());
		GregorianCalendar gcOperationDay = new GregorianCalendar();
		EXCEPTION exceptionType;

		// for all SpecialOperationDays of VehicleJourey
		for (int i = 0; i < listCalendar_OOL_start_date.size(); i++) {

			try {
			  Date now = new Date();
			  final long YEAR = 1000L*60L*60L*24L*365L;
			  final long BEFORE = YEAR*1L;
			  final long AFTER = YEAR*5L;
			  Date earliest = new Date(now.getTime() - BEFORE);//2 years ago
			  Date latest = new Date(now.getTime()+AFTER);
				Date calendarDatesOperationDay = sdfIn.parse(((listCalendar_OOL_start_date.get(i)).getValue(0)));
				if (calendarDatesOperationDay.before(earliest)){
				  gcOperationDay.setTime(now);
				  int year = gcOperationDay.get(Calendar.YEAR) - 1;
				  gcOperationDay.setTime(calendarDatesOperationDay);
				  gcOperationDay.set(Calendar.YEAR, year);
				  calendarDatesOperationDay = gcOperationDay.getTime();
				}
				Date calendarDateOperationDayEnd = sdfIn.parse(((listCalendar_OOL_end_date.get(i)).getValue(0)));
				if (calendarDateOperationDayEnd.after(latest)){
				  gcOperationDay.setTime(now);
          int year = gcOperationDay.get(Calendar.YEAR) + 5;
          gcOperationDay.setTime(calendarDateOperationDayEnd);
          gcOperationDay.set(Calendar.YEAR, year);
				  calendarDateOperationDayEnd = gcOperationDay.getTime();
				}
				gcOperationDay.setTime(calendarDatesOperationDay);

				exceptionType = listCalendar_OOL_exception_type.get(i);
				if (calendarDateOperationDayEnd.getTime() - calendarDatesOperationDay.getTime() > YEAR * 10){
				  log.warning("Iterating over more than 10 years creating dates: " + calendarDatesOperationDay + " to " + calendarDateOperationDayEnd);
				}

				while (calendarDatesOperationDay.compareTo(calendarDateOperationDayEnd) <= 0) {
				  CalendarDate entry = new CalendarDate(serviceId, Util.formatDate(gcOperationDay.get(Calendar.YEAR), gcOperationDay.get(Calendar.MONTH) + 1, gcOperationDay.get(Calendar.DAY_OF_MONTH)), exceptionType);
				  entries.add(entry);
					gcOperationDay.add(Calendar.DAY_OF_YEAR, 1);
					calendarDatesOperationDay = gcOperationDay.getTime();
				}
			} catch (Exception e) {
				handler.setParseError(e);
			}
		}
	}

	public TransxchangeCalendarDates(TransxchangeHandlerEngine owner) {
		super(owner);

		/*
		 * v1.6.3: Dynamically initialize bank holiday maps
		 */
		//bankHolidays = new ArrayList<Object>();

	}

	/*
	 * Create all bank holidays
	 */
	private void createBankHolidaysAll(String bankService, Map<String, String> bankHolidayMap, EXCEPTION exceptionType) {

		for (String holidayDate : bankHolidayMap.values()) {
		  CalendarDate entry = new CalendarDate(bankService,holidayDate,exceptionType);
		  entries.add(entry);
		}
	}

	/*
	 * Create a particular bank holiday
	 */
	private void createBankHoliday(String bankService, String holidayName, Map<String, String> bankHolidayMap, EXCEPTION exceptionType) {

	  String holidayDate = bankHolidayMap.get(holidayName);
    if (null==holidayDate){
      log.warning("Null holiday date for holiday:" + holidayName);
    }
	  CalendarDate entry = new CalendarDate(bankService, holidayDate, exceptionType);
	  entries.add(entry);
	}
}