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

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.StringTokenizer;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

import javax.xml.parsers.ParserConfigurationException;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;

import org.xml.sax.SAXException;
import org.xml.sax.SAXParseException;

/*
 * This class extends DefaultHandler to parse a TransXChange v2.1 xml file,
 * 	build corresponding GTFS data structures
 *  and write these to a GTFS (9-Apr-2007) compliant file set
 */
public class TransxchangeHandler {

	static TransxchangeHandlerEngine parseHandler = null;
	static List<TransxchangeHandlerEngine> parseHandlers = null;

	String agencyOverride = null;


	/*
	 * Utility methods to set and get attribute values
	 */
	public void setAgencyOverride(String agency) {
		agencyOverride = agency;
	}

	/*
	 * Generate GTFS structures
	 */
	public void parse(String filename, String url, String timezone, String defaultRouteType,
			String rootDirectory, String workDirectory, String stopFile,
			String lang, String phone,
			boolean useAgencyShortName, boolean skipEmptyService, boolean skipOrphanStops, boolean geocodeMissingStops,
			Map<String, String> modeList, List<String> stopColumns, String stopfilecolumnseparator,
			int naptanHelperStopColumn, Map<String, String> naptanStopnames,
			Map<String, String> agencyMap)
	    throws SAXException, SAXParseException, IOException, ParserConfigurationException
	{
		ZipFile zipfile = null;
		boolean zipinput = true; // Handle zip files
		boolean processing = true;
		java.util.Enumeration<? extends ZipEntry> enumer = null;

		// Open infile, zip or single xml
		try { // Try to open filename as zip file
			zipfile = new ZipFile(filename);
		} catch (IOException e) {
			zipinput = false; // Opening file as zip file crashed; assume it is a single XML file
		}

		try {

			// Prepare output files
			TransxchangeHandlerEngine.prepareOutput(rootDirectory, workDirectory);

			// Read stopfile
			if (stopFile != null && stopFile.length() > 0)
				TransxchangeStops.readStopfile(stopFile, stopColumns);

			// Roll single as well as zipped infiles into a unified data structure for later transparent processing (stops only, rest goes straight to output files)
			parseHandlers = new ArrayList<TransxchangeHandlerEngine>();
			if (zipinput)
				enumer = zipfile.entries();
			do {
				parseHandler = new TransxchangeHandlerEngine();
				parseHandler.setUrl(url);
				parseHandler.setTimezone(timezone);
				parseHandler.setDefaultRouteType(defaultRouteType);
				parseHandler.setLang(lang);
				parseHandler.setPhone(phone);
				parseHandler.setUseAgencyShortname(useAgencyShortName);
				parseHandler.setSkipEmptyService(skipEmptyService);
				parseHandler.setSkipOrphanStops(skipOrphanStops);
				parseHandler.setGeocodeMissingStops(geocodeMissingStops);
				parseHandler.setModeList(modeList);
				parseHandler.setStopColumns(stopColumns);
				parseHandler.setStopfilecolumnseparator(stopfilecolumnseparator);
				parseHandler.setNaptanHelperStopColumn(naptanHelperStopColumn);
				parseHandler.setNaPTANStopnames(naptanStopnames);
				parseHandler.setRootDirectory(rootDirectory);
				parseHandler.setWorkDirectory(workDirectory);
				parseHandler.setAgencyMap(agencyMap);
				if (agencyOverride != null && agencyOverride.length() > 0)
					parseHandler.setAgencyOverride(agencyOverride);

				SAXParserFactory parserFactory = SAXParserFactory.newInstance();
				SAXParser parser = parserFactory.newSAXParser();

				if (zipinput) {
					if (processing = enumer.hasMoreElements()) {
						ZipEntry zipentry = (ZipEntry)enumer.nextElement();
						System.out.println(zipentry.getName());
						InputStream in = zipfile.getInputStream(zipentry);
						parser.parse(in, parseHandler);
						parseHandler.writeOutputSansAgenciesStopsRoutes(); // Dump data structure with exception of stops which need later consolidation over all input files
						parseHandler.clearDataSansAgenciesStopsRoutes(); // No need to keep the data structures
					}
				} else {
					parser.parse(new File(filename), parseHandler);
					parseHandler.writeOutputSansAgenciesStopsRoutes(); // Dump data structure with exception of stops which need later consolidation over all input files
					processing = false;
				}
				parseHandlers.add(parseHandler);
			} while (processing);
		} catch (IOException e) {
        	System.out.println("TransxchangeHandler Parse Exception: " + e.getMessage());
		}
	}

	/*
	 * Create GTFS file set from GTFS data structures
	 */
	public String writeOutput(String rootDirectory, String workDirectory)
		throws IOException
	{
		parseHandler.closeStopTimes();

        // if empty service skipping requested: Filter out trips that do not refer to an active service
		if (parseHandler.isSkipEmptyService()) {
    		String outdir = parseHandler.getRootDirectory() + parseHandler.getWorkDirectory();
    		String infileName = TransxchangeHandlerEngine.stop_timesFilename + "_tmp" + /* "_" + serviceStartDate + */ TransxchangeHandlerEngine.extension;
        	File infile = new File(outdir + /* "/" + serviceStartDate + */ "/" + infileName);
        	String outfileName = TransxchangeHandlerEngine.stop_timesFilename + /* "_" + serviceStartDate + */ TransxchangeHandlerEngine.extension;
        	File outfile = new File(outdir + /* "/" + serviceStartDate + */ "/" + outfileName);
        	BufferedReader stop_timesIn = new BufferedReader(new FileReader(infile));

            PrintWriter stop_timesOut = new PrintWriter(new FileWriter(outfile));
    		stop_timesOut.println("trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,pickup_type,drop_off_type,shape_dist_traveled");
    		String line = null;
    		String inTrip, inService, inStop;
    		Iterator<TransxchangeHandlerEngine> parsers;
    		TransxchangeHandlerEngine parser;
    		StringTokenizer st;
    		while ((line = stop_timesIn.readLine()) != null) {
    			parsers = parseHandlers.iterator();
    			while (parsers.hasNext()) {
    				parser = (TransxchangeHandlerEngine)parsers.next();
    				if (parser != null) {
    					st = new StringTokenizer(line, ",");
    					inTrip = st.nextToken(); // trip id is first column
//    					inService = parser.getTrips().getService(inTrip);
    					inService = parser.getTripServiceId(inTrip);
    					st.nextToken();
    					st.nextToken();
    					inStop = st.nextToken();
    					if (parser.hasCalendarDatesServiceId(inService) || parser.hasCalendarServiceId(inService)) {
    						stop_timesOut.println(line);
        					parser.getStops().flagStop(inStop); // Flag as included in service for later rollout in skiporphanstop
        				}
    				}
    			}
    		}
    		stop_timesOut.close();
    		stop_timesIn.close();
    		infile.delete();
        } else {
			Iterator<TransxchangeHandlerEngine> parsers = parseHandlers.iterator();
			while (parsers.hasNext()) {
				TransxchangeHandlerEngine parser = (TransxchangeHandlerEngine)parsers.next();
				if (parser != null)
					parser.getStops().flagAllStops("1");
			}
        }
		consolidateAgencies(); // Eliminiate possible duplicates from multiple input files in zip archive
		consolidateStops(); // Eliminiate possible duplicates from multiple input files in zip archive
		consolidateRoutes(); // Eliminiate possible duplicates from multiple input files in zip archive
		Iterator<TransxchangeHandlerEngine> parsers = parseHandlers.iterator();
		while (parsers.hasNext())
			((TransxchangeHandlerEngine)parsers.next()).writeOutputAgenciesStopsRoutes(); // Now write agencies, stops
		return parseHandler.closeOutput(rootDirectory, workDirectory);
	}

	/*
	 * Eliminate possible duplicates from multiple input files in zip archive
	 */
	public void consolidateStops() {
		Iterator<TransxchangeHandlerEngine> parsers = parseHandlers.iterator();
		int parseHandlersCount = 0;
		int j;
		String curStopId;
		List<ValueList> followStopIds;
		TransxchangeStops followStops;
		Iterator<TransxchangeHandlerEngine> followParser;

		while (parsers.hasNext()) {
			TransxchangeStops stops = ((TransxchangeHandlerEngine)parsers.next()).getStops();
			parseHandlersCount += 1;
			List<ValueList> stopIds = stops.getListStops__stop_id();
			for (int i = 0; i < stopIds.size(); i++) {
				followParser = parseHandlers.iterator(); // Set follow parser to parsed input files following current; Iterator is not Cloneable; need to create a new Iterator and step forward to get to the right position (anybody know a more elegant solution?)
				j = 0;
				while (j < parseHandlersCount && followParser.hasNext()) {
					j++;
					followParser.next();
				}
				curStopId = (stopIds.get(i)).getValue(0);
				while (followParser.hasNext()) { // Run through stops of following parsed input files and eliminate duplicates there
					followStops = ((TransxchangeHandlerEngine)followParser.next()).getStops();
					followStopIds = followStops.getListStops__stop_id();
					for (j = 0; j < followStopIds.size(); j++) {
						if (curStopId.equals((followStopIds.get(j)).getValue(0))) {
							(followStopIds.get(j)).setValue(0, "");
						}
					}
				}
			}
		}
	}

	/*
	 * Eliminate possible duplicates from multiple input files in zip archive
	 */
	public void consolidateAgencies() {
		Iterator<TransxchangeHandlerEngine> parsers = parseHandlers.iterator();
		int parseHandlersCount = 0;
		int j;
		String curAgencyId;
		List<ValueList> followAgencyIds;
		TransxchangeAgency followAgencies;
		Iterator<TransxchangeHandlerEngine> followParser;

		while (parsers.hasNext()) {
			TransxchangeAgency agencies = ((TransxchangeHandlerEngine)parsers.next()).getAgencies();
			parseHandlersCount += 1;
			List<ValueList> agencyIds = agencies.getListAgency__agency_id();
			for (int i = 0; i < agencyIds.size(); i++) {
				followParser = parseHandlers.iterator(); // Set follow parser to parsed input files following current; Iterator is not Cloneable; need to create a new Iterator and step forward to get to the right position (anybody know a more elegant solution?)
				j = 0;
				while (j < parseHandlersCount && followParser.hasNext()) {
					j++;
					followParser.next();
				}
				curAgencyId = (agencyIds.get(i)).getValue(0);
				while (followParser.hasNext()) { // Run through stops of following parsed input files and eliminate duplicates there
					followAgencies = ((TransxchangeHandlerEngine)followParser.next()).getAgencies();
					followAgencyIds = followAgencies.getListAgency__agency_id();
					for (j = 0; j < followAgencyIds.size(); j++) {
						if (curAgencyId.equals(followAgencyIds.get(j).getValue(0))) {
							followAgencyIds.get(j).setValue(0, "");
						}
					}
				}
			}
		}
	}

	/*
	 * Eliminate possible duplicates from multiple input files in zip archive
	 */
	public void consolidateRoutes() {
		Iterator<TransxchangeHandlerEngine> parsers = parseHandlers.iterator();
		int parseHandlersCount = 0;
		int j;
		String curRouteId;
		List<ValueList> followRouteIds;
		TransxchangeRoutes followRoutes;
		Iterator<TransxchangeHandlerEngine> followParser;

		while (parsers.hasNext()) {
			TransxchangeRoutes routes = ((TransxchangeHandlerEngine)parsers.next()).getRoutes();
			parseHandlersCount += 1;
			List<ValueList> routeIds = routes.getListRoutes__route_id();
			for (int i = 0; i < routeIds.size(); i++) {
				followParser = parseHandlers.iterator(); // Set follow parser to parsed input files following current; Iterator is not Cloneable; need to create a new Iterator and step forward to get to the right position (anybody know a more elegant solution?)
				j = 0;
				while (j < parseHandlersCount && followParser.hasNext()) {
					j++;
					followParser.next();
				}
				curRouteId = (routeIds.get(i)).getValue(0);
				while (followParser.hasNext()) { // Run through stops of following parsed input files and eliminate duplicates there
					followRoutes = ((TransxchangeHandlerEngine)followParser.next()).getRoutes();
					followRouteIds = followRoutes.getListRoutes__route_id();
					for (j = 0; j < followRouteIds.size(); j++) {
						if (curRouteId.equals(followRouteIds.get(j).getValue(0))) {
							(followRouteIds.get(j)).setValue(0, "");
						}
					}
				}
			}
		}
	}
}
