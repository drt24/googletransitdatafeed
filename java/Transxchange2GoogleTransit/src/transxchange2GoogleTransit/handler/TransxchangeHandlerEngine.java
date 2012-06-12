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

import java.io.*;

import org.xml.sax.*;
import org.xml.sax.helpers.*;

import java.util.zip.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.StringTokenizer;

import java.net.URL;
import java.net.URLEncoder;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;

import org.w3c.dom.Document;
import org.w3c.dom.NodeList;
import org.w3c.dom.Node;

import transxchange2GoogleTransit.Configuration;
import transxchange2GoogleTransit.LatLong;
import transxchange2GoogleTransit.Stop;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;
import javax.xml.xpath.XPathConstants;

/*
 * This class extends DefaultHandler to parse a TransXChange v2.1 xml file,
 * 	build corresponding GTFS data structures
 *  and write these to a GTFS (9-Apr-2007) compliant file set
 */
public class TransxchangeHandlerEngine extends DefaultHandler {

	// GTFS structures
	TransxchangeAgency agencies;
	TransxchangeStops stops;
	TransxchangeRoutes routes;
	TransxchangeTrips trips;
	TransxchangeStopTimes stopTimes;
	TransxchangeCalendar calendar;
	TransxchangeCalendarDates calendarDates;

	// Parse comments
	static String parseError = "";
	static String parseInfo = "";

	// GTFS file names
	static final String agencyFilename = "agency";
	static final String stopsFilename = "stops";
	static final String routesFilename = "routes";
	static final String tripsFilename = "trips";
	static final String stop_timesFilename = "stop_times";
	static final String calendarFilename = "calendar";
	static final String calendar_datesFilename = "calendar_dates";
	static final String extension = ".txt";
	static final String gtfsZipfileName = "google_transit.zip";

	// output files
	static PrintWriter agenciesOut = null;
	static PrintWriter stopsOut = null;
	static PrintWriter routesOut = null;
	static PrintWriter tripsOut = null;
//	static PrintWriter stop_timesOut = null;
	static PrintWriter calendarsOut = null;
	static PrintWriter calendarDatesOut = null;

	static List<String> filenames = null;
	static String outdir = "";

	Map<String, String> calendarServiceIds = null;
	Map<String, String> calendarDatesServiceIds = null;
	Map<String, String> tripServiceIds = null;
  private Configuration config;

	static String agencyOverride = "";

	/*
	 * Utility methods to set and get attribute values
	 */
	public String getUrl() {
		return config.getUrl();
	}
	public String getTimezone() {
		return config.getTimezone();
	}
	public String getDefaultRouteType() {
		return config.getDefaultRouteType();
	}
	public String getLang() {
		return config.getLang();
	}
	public String getPhone() {
		return config.getPhone();
	}
	public TransxchangeAgency getAgencies() {
		return agencies;
	}
	public TransxchangeStops getStops() {
		return stops;
	}
	public TransxchangeRoutes getRoutes() {
		return routes;
	}
	public TransxchangeTrips getTrips() {
		return trips;
	}
	public TransxchangeStopTimes getStopTimes() {
		return stopTimes;
	}
	public TransxchangeCalendar getCalendar() {
		return calendar;
	}
	public TransxchangeCalendarDates getCalendarDates() {
		return calendarDates;
	}
	public void setParseError(String txt) {
		parseError = txt;
	}
	public String getStopfilecolumnseparator() {
		return config.getStopfileColumnSeparator();
	}
	public int getNaptanHelperStopColumn() {
		return config.getNaptanHelperStopColumn();
	}
	/**
	 * Get the stop for the given atcoCode or null if we don't have one
	 * @param atcoCode
	 * @return the stop or null
	 */
	public Stop getStop(String atcoCode){
	  Map<String,Stop> naptanStops = config.getNaptanStops();
	  if (null == naptanStops){
	    return null;
	  } else {
	    return naptanStops.get(atcoCode);
	  }
	}
	public String getNaPTANStopname(String atcoCode) {
	  Map<String,Stop> naptanStops = config.getNaptanStops();
		if (naptanStops == null || atcoCode == null){
			return "";
		}
		String name = naptanStops.get(atcoCode).getName();
		if (null == name){
			return "";
		}
		return name;
	}

	public Map<String, String> getModeList() {
		return config.getModeList();
	}
	public List<String> getStopColumns() {
		return config.getStopColumns();
	}

	public String getRootDirectory() {
		return config.getRootDirectory();
	}
	public String getWorkDirectory() {
		return config.getOutputDirectory();
	}

	public String getParseError() {
		return parseError;
	}

	public void setParseInfo(String txt) {
		parseInfo = txt;
	}

	public String getParseInfo() {
		return parseInfo;
	}

	public boolean isAgencyShortName() {
		return config.useAgencyShortName();
	}
	public boolean isSkipEmptyService() {
		return config.skipEmptyService();
	}
	public boolean isSkipOrphanStops() {
		return config.skipOrphanStops();
	}
	public boolean isGeocodeMissingStops() {
		return config.geocodeMissingStops();
	}

	public void addFilename(String fileName) {
		if (fileName == null || filenames == null)
			return;
		filenames.add(fileName);
	}

	public void addTripServiceId(String tripId, String serviceId) {
		if (tripServiceIds == null)
			tripServiceIds = new HashMap<String, String>();
		tripServiceIds.put(tripId, serviceId);
	}
	public boolean hasTripServiceId(String testId) {
		if (tripServiceIds == null || testId == null || testId.length() == 0)
			return false;
		return tripServiceIds.containsKey(testId);
	}
	public String getTripServiceId(String tripId) {
		if (tripServiceIds == null || tripId == null || tripId.length() == 0)
			return "";
		return tripServiceIds.get(tripId);

	}

	public boolean hasCalendarServiceId(String testId) {
		if (testId == null || calendarServiceIds == null)
			return false;
		return (calendarServiceIds.containsKey(testId));
	}
	public boolean hasCalendarDatesServiceId(String testId) {
		if (testId == null || calendarDatesServiceIds == null)
			return false;
		return (calendarDatesServiceIds.containsKey(testId));
	}

	public void setAgencyOverride(String agency) {
		agencyOverride = agency;
	}
	public String getAgencyOverride() {
		return agencyOverride;
	}
	public Map<String, String> getAgencyMap() {
		return config.getAgencyMap();
	}

	/*
	 * Start element. Called by parser when start of element found <element>
	 */
	@Override
  public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException {
	    agencies.startElement(uri, name, qName, atts);
	    stops.startElement(uri, name, qName, atts);
	    routes.startElement(uri, name, qName, atts);
	    trips.startElement(uri, name, qName, atts);
	    stopTimes.startElement(uri, name, qName, atts);
	    calendar.startElement(uri, name, qName, atts);
	    calendarDates.startElement(uri, name, qName, atts);
	}

	/*
	 * Parse element. Called to extract contents of elements <element>contents</element>
	 */
	@Override
  public void characters (char ch[], int start, int length) {
		agencies.characters(ch, start, length);
		stops.characters(ch, start, length);
		routes.characters(ch, start, length);
		trips.characters(ch, start, length);
		stopTimes.characters(ch, start, length);
		calendar.characters(ch, start, length);
		calendarDates.characters(ch, start, length);
	}

	/*
 	 * End element. Called by parser when end of element reached </element>
 	 */
	@Override
  public void endElement (String uri, String name, String qName) {

		// take care of element
		agencies.endElement(uri, name, qName);
		stops.endElement(uri, name, qName);
		routes.endElement(uri, name, qName);
		trips.endElement(uri, name, qName);
		stopTimes.endElement(uri, name, qName);
		calendar.endElement(uri, name, qName);
		calendarDates.endElement(uri, name, qName);

		// clear keys
		agencies.clearKeys(qName);
		stops.clearKeys(qName);
		routes.clearKeys(qName);
		trips.clearKeys(qName);
		stopTimes.clearKeys(qName);
		calendar.clearKeys(qName);
		calendarDates.clearKeys(qName);
	}

	/*
	 * Complete (and dump) GTFS data structures. Called when end of TransXChange input file is reached
	 */
	@Override
  public void endDocument() {

		// wrap up document parsing
		try {
			agencies.endDocument();
			stops.endDocument();
			routes.endDocument();
			trips.endDocument();
			stopTimes.endDocument();
			calendar.endDocument();
			calendarDates.endDocument();
		} catch (IOException e) {
			System.err.println("transxchange2GTFS endDocument() exception: " + e.getMessage());
			System.exit(1);
		}

		// Complete data structures (by filling in default values if necessary)
		agencies.completeData();
		stops.completeData();
		routes.completeData();
		trips.completeData();
		stopTimes.completeData();
		calendar.completeData();
		calendarDates.completeData();

		// Dump parsed data to System.out
/*
		agencies.dumpValues();
		stops.dumpValues();
		routes.dumpValues();
		trips.dumpValues();
		stopTimes.dumpValues();
		calendar.dumpValues();
		calendarDates.dumpValues();
*/
	}


	/*
	 * Prepare GTFS file set files
	 */
	protected static void prepareOutput(String outputDirectory)
	throws IOException
	{
		outdir = outputDirectory;
		filenames = new ArrayList<String>();

		// Delete existing GTFS files in output directory
		new File(outdir + "/" + agencyFilename + extension).delete();
		new File(outdir + "/" + stopsFilename + extension).delete();
		new File(outdir + "/" + routesFilename + extension).delete();
		new File(outdir + "/" + tripsFilename + extension).delete();
		new File(outdir + "/" + stop_timesFilename + extension).delete();
		new File(outdir + "/" + calendarFilename + extension).delete();
		new File(outdir + "/" + calendar_datesFilename + extension).delete();
		new File(outdir + "/" + gtfsZipfileName).delete();

		// Create output directory
		// Note service start date not any longer used to determine directory name for outfiles
		new File(outdir /* + "/" + serviceStartDate*/ ).mkdirs();
	}

	/*
	 * Create GTFS file set from GTFS data structures except for stops
	 */
	public void writeOutputSansAgenciesStopsRoutes()
	throws IOException
	{
		String outfileName = "";
		File outfile = null;

        // calendar.txt
        String daytypesJourneyPattern;
        String daytypesService;
        String serviceId;

        if (calendarsOut == null) {
            outfileName = calendarFilename + /* "_" + serviceStartDate + */ extension;
            outfile = new File(outdir + /* "/" + serviceStartDate + */ "/" + outfileName);
            filenames.add(outfileName);
            calendarsOut = new PrintWriter(new FileWriter(outfile));
            calendarsOut.println("service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date");
        }
        calendarServiceIds = new HashMap<String, String>();

        boolean skipEmptyService = config.skipEmptyService();
        String outLine;
        for (int i = 0; i < this.getCalendar().getListCalendar__service_id().size(); i++) {
        	outLine = "";
        	serviceId = ((this.getCalendar().getListCalendar__service_id().get(i))).getValue(0);
        	// Service ID added to calendar data structure in class TransxchangeCalendar.
        	// If match and no journey pattern associated with daytype,
        	// then daytype applies to service, not journey pattern. Otherwise daytpe is set to 0 as daytype applies to journey pattern, not service

        	// Monday
        	daytypesJourneyPattern = (this.getCalendar().getListCalendar__monday().get(i)).getValue(1);
        	daytypesService = (this.getCalendar().getListCalendar__monday().get(i)).getValue(2);
        	if (daytypesService == null)
        		daytypesService = "";
        	if (daytypesService.equals(serviceId) && daytypesJourneyPattern.length() == 0)
        		outLine += (this.getCalendar().getListCalendar__monday().get(i)).getValue(0);
        	else
        		outLine += "0";
        	outLine += ",";

        	// Tuesday
           	daytypesJourneyPattern = (this.getCalendar().getListCalendar__tuesday().get(i)).getValue(1);
        	daytypesService = (this.getCalendar().getListCalendar__tuesday().get(i)).getValue(2);
        	if (daytypesService == null)
        		daytypesService = "";
        	if (daytypesService.equals(serviceId) && daytypesJourneyPattern.length() == 0)
        		outLine += (this.getCalendar().getListCalendar__tuesday().get(i)).getValue(0);
        	else
        		outLine += "0";
        	outLine += ",";

        	// Wednesday
           	daytypesJourneyPattern = (this.getCalendar().getListCalendar__wednesday().get(i)).getValue(1);
        	daytypesService = (this.getCalendar().getListCalendar__wednesday().get(i)).getValue(2);
        	if (daytypesService == null)
        		daytypesService = "";
        	if (daytypesService.equals(serviceId) && daytypesJourneyPattern.length() == 0)
        		outLine += (this.getCalendar().getListCalendar__wednesday().get(i)).getValue(0);
        	else
        		outLine += "0";
        	outLine += ",";

        	// Thursday
           	daytypesJourneyPattern = (this.getCalendar().getListCalendar__thursday().get(i)).getValue(1);
        	daytypesService = (this.getCalendar().getListCalendar__thursday().get(i)).getValue(2);
        	if (daytypesService == null)
        		daytypesService = "";
        	if (daytypesService.equals(serviceId) && daytypesJourneyPattern.length() == 0)
        		outLine += (this.getCalendar().getListCalendar__thursday().get(i)).getValue(0);
        	else
        		outLine += "0";
        	outLine += ",";

        	// Friday
          	daytypesJourneyPattern = (this.getCalendar().getListCalendar__friday().get(i)).getValue(1);
        	daytypesService = (this.getCalendar().getListCalendar__friday().get(i)).getValue(2);
        	if (daytypesService == null)
        		daytypesService = "";
        	if (daytypesService.equals(serviceId) && daytypesJourneyPattern.length() == 0)
        		outLine += (this.getCalendar().getListCalendar__friday().get(i)).getValue(0);
        	else
        		outLine += "0";
        	outLine += ",";

        	// Saturday
          	daytypesJourneyPattern = (this.getCalendar().getListCalendar__saturday().get(i)).getValue(1);
        	daytypesService = (this.getCalendar().getListCalendar__saturday().get(i)).getValue(2);
        	if (daytypesService == null)
        		daytypesService = "";
        	if (daytypesService.equals(serviceId) && daytypesJourneyPattern.length() == 0)
        		outLine += (this.getCalendar().getListCalendar__saturday().get(i)).getValue(0);
        	else
        		outLine += "0";
        	outLine += ",";

        	// Sunday
          	daytypesJourneyPattern = (this.getCalendar().getListCalendar__sunday().get(i)).getValue(1);
        	daytypesService = (this.getCalendar().getListCalendar__sunday().get(i)).getValue(2);
        	if (daytypesService == null)
        		daytypesService = "";
        	if (daytypesService.equals(serviceId) && daytypesJourneyPattern.length() == 0)
        		outLine += (this.getCalendar().getListCalendar__sunday().get(i)).getValue(0);
        	else
        		outLine += "0";
        	outLine += ",";

        	// Start and end dates
        	if (outLine.contains("1") || !skipEmptyService) {
	        	calendarsOut.print(serviceId);
	        	calendarsOut.print(",");
	        	calendarsOut.print(outLine);
	        	calendarsOut.print((this.getCalendar().getListCalendar__start_date().get(i)).getValue(0));
	        	calendarsOut.print(",");
	        	calendarsOut.print((this.getCalendar().getListCalendar__end_date().get(i)).getValue(0));
	        	calendarsOut.println();
	        	if (skipEmptyService)
	        		calendarServiceIds.put(serviceId, serviceId);
            }
        }

        // calendar_dates.txt
        // Create file only if there are exceptions or additions
        if (this.getCalendarDates().getListCalendarDates__service_id().size() > 0) {
        	if (calendarDatesOut == null) {
            	outfileName = calendar_datesFilename + /* "_" + serviceStartDate + */ extension;
            	outfile = new File(outdir + /* "/" + serviceStartDate + */ "/" + outfileName);
            	calendarDatesOut = new PrintWriter(new FileWriter(outfile));
            	filenames.add(outfileName);
            	calendarDatesOut.println("service_id,date,exception_type");
        	}
        	calendarDatesServiceIds = new HashMap<String, String>();
        	String calendarDateServiceId;
        	String calendarDateExceptionType;
        	HashMap<String, String> calendarExceptions = new HashMap<String, String>();
        	for (int i = 0; i < this.getCalendarDates().getListCalendarDates__service_id().size(); i++) {
        		calendarDateServiceId = (this.getCalendarDates().getListCalendarDates__service_id().get(i)).getValue(0);
        		calendarDateExceptionType = (this.getCalendarDates().getListCalendarDates__exception_type().get(i)).getValue(0);
        		if (this.hasCalendarServiceId(calendarDateServiceId) || !calendarDateExceptionType.equals("2") || !config.skipEmptyService()) {
        			outLine = calendarDateServiceId + "," +
        				(this.getCalendarDates().getListCalendarDates__date().get(i)).getValue(0) + "," +
        				calendarDateExceptionType;
        			if (!calendarExceptions.containsKey(outLine)) {
//	        		calendarDatesOut.print(calendarDateServiceId);
//	        		calendarDatesOut.print(",");
//	        		calendarDatesOut.print((this.getCalendarDates().getListCalendarDates__date().get(i)).getValue(0));
//	        		calendarDatesOut.print(",");
//	        		calendarDatesOut.println(calendarDateExceptionType);
	        			calendarDatesOut.println(outLine);
	        			calendarExceptions.put(outLine, "");
        			}

	        		if (skipEmptyService)
	        			calendarDatesServiceIds.put(calendarDateServiceId, calendarDateServiceId);
            	}
        	}
        }

        // trips.txt
		if (tripsOut == null) {
	        outfileName = tripsFilename + /* "_" + serviceStartDate + */ extension;
	        outfile = new File(outdir + /* "/" + serviceStartDate + */ "/" + outfileName);
	        filenames.add(outfileName);
	        tripsOut = new PrintWriter(new FileWriter(outfile));
	        tripsOut.println("route_id,service_id,trip_id,trip_headsign,direction_id,block_id,shape_id");
		}
		String tripsRouteId;
		String tripsServiceId;
		String tripsDirectionId; // v.1.7.3
		String tripsRouteRef; // v.1.7.3
        for (int i = 0; i < this.getTrips().getListTrips__route_id().size(); i++) {
        	tripsServiceId = (this.getTrips().getListTrips__service_id().get(i)).getValue(0);
        	tripsDirectionId = (this.getTrips().getListTrips__direction_id().get(i)).getValue(0); // v.1.7.3
        	tripsRouteRef = (this.getTrips().getListTrips__routeref().get(i)).getValue(0); // v.1.7.3
        	if (!skipEmptyService || this.hasCalendarServiceId(tripsServiceId) || this.hasCalendarDatesServiceId(tripsServiceId)) {
        		tripsRouteId = (this.getTrips().getListTrips__route_id().get(i)).getValue(0);
	        	tripsOut.print(tripsRouteId);
	        	tripsOut.print(",");
	        	tripsOut.print(tripsServiceId);
	        	tripsOut.print(",");
	        	tripsOut.print((this.getTrips().getListTrips__trip_id().get(i)).getKeyName());
	        	tripsOut.print(",");
	        	String tripHeadsign = this.getRoutes().getRouteDescription(tripsRouteRef);
	        	if (tripHeadsign.contains(",")) // v1.7.5: csv-proof output
	        		tripHeadsign = "\"" + tripHeadsign + "\"";
	        	tripsOut.print(tripHeadsign); // v.1.7.3: Route Description
//	        	tripsOut.print((this.getRoutes().getHeadsign(tripsRouteId, tripsDirectionId.equals("1")))); // v.1.7.3: Consider direction in selecting destination
	        	tripsOut.print(",");
	        	tripsOut.print(tripsDirectionId); // v1.7.3
	        	tripsOut.print(",");
	        	tripsOut.print((this.getTrips().getListTrips__block_id().get(i)).getValue(0));
	        	tripsOut.print(",");
	        	tripsOut.println();
            }
        }
   	}

	/*
	 * Create GTFS file set from GTFS data structures except for stops
	 */
	public void writeOutputAgenciesStopsRoutes()
	throws IOException
	{
		String outfileName = "";
		File outfile = null;

		// agencies.txt
		if (agenciesOut == null) {
			outfileName = agencyFilename + /* "_" + serviceStartDate + */ extension;
			outfile = new File(outdir + /* "/" + serviceStartDate + */ "/"  + outfileName);
			filenames.add(outfileName);
			agenciesOut = new PrintWriter(new FileWriter(outfile));
			agenciesOut.println("agency_id,agency_name,agency_url,agency_timezone,agency_lang,agency_phone");
		}
		for (int i = 0; i < this.getAgencies().getListAgency__agency_name().size(); i++) {
			if ((((this.getAgencies().getListAgency__agency_id().get(i))).getValue(0)).length() > 0) {
				agenciesOut.print((this.getAgencies().getListAgency__agency_id().get(i)).getValue(0));
				agenciesOut.print(",");
				agenciesOut.print((this.getAgencies().getListAgency__agency_name().get(i)).getValue(0));
				agenciesOut.print(",");
				agenciesOut.print((this.getAgencies().getListAgency__agency_url().get(i)).getValue(0));
				agenciesOut.print(",");
				agenciesOut.print((this.getAgencies().getListAgency__agency_timezone().get(i)).getValue(0));
				agenciesOut.print(",");
				agenciesOut.print((this.getAgencies().getListAgency__agency_lang().get(i)).getValue(0));
				agenciesOut.print(",");
				agenciesOut.print((this.getAgencies().getListAgency__agency_phone().get(i)).getValue(0));
				agenciesOut.println();
	        }
        }

        // stops.txt
		if (stopsOut == null) {
	        outfileName = stopsFilename + /* "_" + serviceStartDate + */ extension;
	        outfile = new File(outdir + /* "/" + serviceStartDate + */ "/" + outfileName);
	        filenames.add(outfileName);
	        stopsOut = new PrintWriter(new FileWriter(outfile));
	        stopsOut.println("stop_id,stop_name,stop_desc,stop_lat,stop_lon,zone_id,stop_url");
		}
		String stopId, stopName;
		TransxchangeStops stops = this.getStops();
		for (int i = 0; i < stops.getListStops__stop_id().size(); i++) {
			stopId = (stops.getListStops__stop_id().get(i)).getValue(0);
			if (stopId.length() > 0 && (!config.skipOrphanStops() || stops.hasStop(stopId))) {
				stopName = (stops.getListStops__stop_name().get(i)).getValue(0);
				LatLong coordinates = new LatLong((stops.getListStops__stop_lat().get(i)).getValue(0),
					(stops.getListStops__stop_lon().get(i)).getValue(0) );

				// If requested, geocode lat/lon
				if (isGeocodeMissingStops() && (coordinates.latitude == null || coordinates.longitude == null)) {
					try {
						System.out.println("Geocoding stop (id / name): " + stopId + " / " + stopName);
						geocodeMissingStop(stopName);
					} catch (Exception e) {
						System.out.println("Geocoding exception: " + e.getMessage() + " for stop: " + stopName);
					}
				}

				stopsOut.print(stopId);
				stopsOut.print(",");
				stopsOut.print(stopName);
				stopsOut.print(",");
				stopsOut.print((this.getStops().getListStops__stop_desc().get(i)).getValue(0));
				stopsOut.print(",");
				stopsOut.print(coordinates.latitude);
				stopsOut.print(",");
				stopsOut.print(coordinates.longitude);
				stopsOut.print(","); // no zone id
				stopsOut.print(","); // no stop URL
				stopsOut.println();
// Below a number of attributes (stop_street to stop_country) which have been deprecated in the GTFS (9-Apr-2007 release of the spec)
//        		stopsOut.print((this.getStops().getListStops__stop_street().get(i)).getValue(0));
//        		stopsOut.print(",");
//        		stopsOut.print((this.getStops().getListStops__stop_city().get(i)).getValue(0));
//        		stopsOut.print(",");
//        		stopsOut.print((this.getStops().getListStops__stop_postcode().get(i)).getValue(0));
//        		stopsOut.print(",");
//        		stopsOut.print((this.getStops().getListStops__stop_region().get(i)).getValue(0));
//        		stopsOut.print(",");
//        		stopsOut.print((this.getStops().getListStops__stop_country().get(i)).getValue(0));
//				stopsOut.println();
			}
		}

		// routes.txt
		if (routesOut == null) {
	        outfileName = routesFilename + /* "_" + serviceStartDate + */ extension;
	        outfile = new File(outdir + /* "/" + serviceStartDate + */ "/" + outfileName);
	        filenames.add(outfileName);
	        routesOut = new PrintWriter(new FileWriter(outfile));
	        routesOut.println("route_id,agency_id,route_short_name,route_long_name,route_desc,route_type,route_url,route_color,route_text_color");
		}
		for (int i = 0; i < this.getRoutes().getListRoutes__route_id().size(); i++) {
			if ((((this.getRoutes().getListRoutes__route_id().get(i))).getValue(0)).length() > 0) {
				routesOut.print((this.getRoutes().getListRoutes__route_id().get(i)).getValue(0));
				routesOut.print(",");
				routesOut.print((this.getRoutes().getListRoutes__agency_id().get(i)).getValue(0));
				routesOut.print(",");
				String routeShortname = (this.getRoutes().getListRoutes__route_short_name().get(i)).getValue(0);
				routesOut.print(routeShortname);
				routesOut.print(",");
				String routeLongname = (this.getRoutes().getListRoutes__route_long_name().get(i)).getValue(0);
				routesOut.print(routeLongname);
				routesOut.print(",");
				String routeDesc = (this.getRoutes().getListRoutes__route_desc().get(i)).getValue(0); // v1.7.5: Do not write route description if equal to route short or long name
				if (routeDesc != null && !(routeDesc.equals(routeShortname) || routeDesc.equals(routeLongname)))
					routesOut.print(routeDesc);
				routesOut.print(",");
				routesOut.print((this.getRoutes().getListRoutes__route_type().get(i)).getValue(0));
				routesOut.print(","); // no route url
				routesOut.print(","); // no route color
				routesOut.print(","); // no route text color
				routesOut.println();
	        }
        }
	}

	/*
	 * Clear data structures except for stops
	 */
	public void clearDataSansAgenciesStopsRoutes() {
		trips = null;
		stopTimes = null;
		calendar = null;
		calendarDates = null;
	}

	public void closeStopTimes() {
		stopTimes.closeStopTimesOutput();
	}

	/*
	 * Close GTFS file set from GTFS data structures
	 */
	public String closeOutput(String rootDirectory, String workDirectory)
	throws IOException
	{
		// Close out PrintWriter's
		agenciesOut.close();
		stopsOut.close();
		routesOut.close();
		tripsOut.close();
//		stop_timesOut.close();
		calendarsOut.close();
		if (calendarDatesOut != null) // calendar_dates is optional; might not have been created
			calendarDatesOut.close();

		agenciesOut = null;
		stopsOut = null;
		routesOut = null;
		tripsOut = null;
//		stop_timesOut = null;
		calendarsOut = null;
		calendarDatesOut = null;

		// Compress the files
        ZipOutputStream zipOut = new ZipOutputStream(new FileOutputStream(outdir + /* "/" + serviceStartDate + */ "/" + gtfsZipfileName));
        byte[] buf = new byte[1024]; // Create a buffer for reading the files
        for (int i = 0; i < filenames.size(); i++) {
            FileInputStream in = new FileInputStream(outdir + /* "/" + serviceStartDate + */ "/" + filenames.get(i));

            // Add ZIP entry to output stream.
            zipOut.putNextEntry(new ZipEntry(filenames.get(i)));

            // Transfer bytes from the file to the ZIP file
            int len;
            while ((len = in.read(buf)) > 0) {
                zipOut.write(buf, 0, len);
            }

            // Complete the entry
            zipOut.closeEntry();
            in.close();
        }

        // Complete the ZIP file
        zipOut.close();

        // Return path and name of GTFS zip file
        return workDirectory + /* "/" + serviceStartDate + */ "/" + "google_transit.zip";
	}

	private LatLong geocodeMissingStop(String stopname)
		throws MalformedURLException, UnsupportedEncodingException, XPathExpressionException, IOException, ParserConfigurationException, SAXException
	{
		float[] coordFloat = {-999999, -999999};
		String broadenedStopname;
		String token;
		StringTokenizer st;

		geocodeStop(stopname, coordFloat);

		// If no result: Broaden search. First try: remove cross street
		if ((coordFloat[0] == -999999 || coordFloat[1] == -999999) && stopname.contains("/")) {
			broadenedStopname = "";
			st = new StringTokenizer(stopname, ",");
			while (st.hasMoreTokens()) {
				token = st.nextToken();
				if (token.contains("/"))
					token = token.substring(0, token.indexOf("/"));
				if (broadenedStopname.length() > 0)
					broadenedStopname += ", ";
				broadenedStopname += token;
			}
			if (!broadenedStopname.equals(stopname)) {
				stopname = broadenedStopname;
				geocodeStop(stopname, coordFloat);
			}
		}

		// Next try: Remove qualifiers in brackets
		if ((coordFloat[0] == -999999 || coordFloat[1] == -999999) && stopname.contains("(")) {
			broadenedStopname = "";
			st = new StringTokenizer(stopname, ",");
			while (st.hasMoreTokens()) {
				token = st.nextToken();
				if (token.contains("("))
					token = token.substring(0, token.indexOf("("));
				if (broadenedStopname.length() > 0)
					broadenedStopname += ", ";
				broadenedStopname += token;
			}
			if (!broadenedStopname.equals(stopname)) {
				stopname = broadenedStopname;
				geocodeStop(stopname, coordFloat);
			}
		}

		// Go for broke: remove elements from least specific to broadest
		while ((coordFloat[0] == -999999 || coordFloat[1] == -999999) && stopname.lastIndexOf(",") >= 0) {
			stopname = stopname.substring(0, stopname.lastIndexOf(","));
			geocodeStop(stopname, coordFloat);
		}

		String latitude = null;
		if (coordFloat[0] != -999999){
		  latitude = "" + coordFloat[0];
		}
		String longitude = null;
		if (coordFloat[1] != -999999){
		  longitude = "" + coordFloat[1];
		}

		return new LatLong(latitude,longitude);
	}
	private void geocodeStop(String stopname, float[] coordinates)
		throws MalformedURLException, UnsupportedEncodingException, XPathExpressionException, IOException, ParserConfigurationException, SAXException
	{
		final String geocoderPrefix = "http://maps.google.com/maps/api/geocode/xml?address=";
		final String geocoderPostfix = "&sensor=false";

		if (stopname == null || coordinates == null || coordinates.length != 2)
			return;
		String geoaddress = geocoderPrefix + stopname + geocoderPostfix;
		System.out.println("	Trying: " + geoaddress);
		URL url = new URL(geocoderPrefix + URLEncoder.encode(stopname, "UTF-8") + geocoderPostfix);
	    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
	    conn.connect();
	    InputSource inputStream = new InputSource(conn.getInputStream());
	    Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(inputStream);

	    XPath xp = XPathFactory.newInstance().newXPath();
	    NodeList geocodedNodes = (NodeList) xp.evaluate("/GeocodeResponse/result[1]/geometry/location/*", doc, XPathConstants.NODESET);
	    float lat = -999999;
	    float lon = -999999;
	    Node node;
	    for (int i = 0; i < geocodedNodes.getLength(); i++) {
	    	node = geocodedNodes.item(i);
	    	if("lat".equals(node.getNodeName()))
	    		lat = Float.parseFloat(node.getTextContent());
	    	if("lng".equals(node.getNodeName()))
	    		lon = Float.parseFloat(node.getTextContent());
	    }
	    coordinates[0] = lat;
	    coordinates[1] = lon;
	}

	/*
	 * Initialize GTFS data structures
	 */
	public TransxchangeHandlerEngine ()
		throws UnsupportedEncodingException, IOException {
		agencies = new TransxchangeAgency(this);
		stops = new TransxchangeStops(this);
		routes = new TransxchangeRoutes(this);
		trips = new TransxchangeTrips(this);
		stopTimes = new TransxchangeStopTimes(this);
		calendar = new TransxchangeCalendar(this);
		calendarDates = new TransxchangeCalendarDates(this);
	}
  public TransxchangeHandlerEngine(Configuration config) throws UnsupportedEncodingException, IOException {
    this();
    this.config = config;
  }
}