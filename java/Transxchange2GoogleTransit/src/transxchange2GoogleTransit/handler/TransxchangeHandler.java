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
import java.util.Set;
import java.util.StringTokenizer;
import java.util.TreeMap;

import javax.xml.parsers.ParserConfigurationException;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;

import org.xml.sax.SAXException;
import org.xml.sax.SAXParseException;

import transxchange2GoogleTransit.Agency;
import transxchange2GoogleTransit.Configuration;
import transxchange2GoogleTransit.Route;
import transxchange2GoogleTransit.Stop;

/*
 * This class extends DefaultHandler to parse a TransXChange v2.1 xml file,
 * 	build corresponding GTFS data structures
 *  and write these to a GTFS (9-Apr-2007) compliant file set
 */
public class TransxchangeHandler {

	static List<TransxchangeHandlerEngine> parseHandlers = null;

	private Map<String,Stop> stops = new TreeMap<String,Stop>();
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
			int naptanHelperStopColumn, Map<String, Stop> naptanStops,
			Map<String, String> agencyMap)
	    throws SAXException, SAXParseException, IOException, ParserConfigurationException
	{
	  Configuration config = new Configuration();
	  config.setInputFileName(filename);
	  config.setUrl(url);
	  config.setTimezone(timezone);
	  config.setDefaultRouteType(defaultRouteType);
	  config.setRootDirectory(rootDirectory);
	  config.setOutputDirectory(workDirectory);
	  config.setStopFile(stopFile);
	  config.setLang(lang);
	  config.setPhone(phone);
	  config.setUseAgencyShortName(useAgencyShortName);
	  config.setSkipEmptyService(skipEmptyService);
	  config.setSkipOrphanStops(skipOrphanStops);
	  config.setGeocodeMissingStops(geocodeMissingStops);
	  config.setNaptanHelperStopColumn(naptanHelperStopColumn);
	  config.setNaptanStops(naptanStops);
	  config.setAgencyMap(agencyMap);
	  parse(config);
	}

  public void parse(Configuration config) throws ParserConfigurationException, SAXException {
    try {
      // Prepare output files
      TransxchangeHandlerEngine.prepareOutput(config.getQualifiedOutputDirectory());

      // Read stopfile
      String stopFile = config.getStopFile();
      if (stopFile != null && stopFile.length() > 0)
        TransxchangeStops.readStopfile(stopFile, config.getStopColumns());

      // Roll single as well as zipped infiles into a unified data structure for later transparent
      // processing (stops only, rest goes straight to output files)
      parseHandlers = new ArrayList<TransxchangeHandlerEngine>();

      for (InputStream stream : config.getInputStreams()) {

        TransxchangeHandlerEngine parseHandler = new TransxchangeHandlerEngine(config);

        if (agencyOverride != null && agencyOverride.length() > 0)
          parseHandler.setAgencyOverride(agencyOverride);

        SAXParserFactory parserFactory = SAXParserFactory.newInstance();
        SAXParser parser = parserFactory.newSAXParser();

        parser.parse(stream, parseHandler);
        // Dump data structure with exception of stops which need later consolidation over all input
        // files
        parseHandler.getStops().export(stops);// saves on memory
        parseHandler.writeOutputSansAgenciesStopsRoutes();
        parseHandler.clearDataSansAgenciesStopsRoutes(); // No need to keep the data structures

        parseHandlers.add(parseHandler);
      }
    } catch (IOException e) {
      System.err.println("TransxchangeHandler Parse Exception: " + e.getMessage());
    }
  }

	/**
   * Create GTFS file set from GTFS data structures
   */
	public String writeOutput(Configuration config) throws IOException{
		TransxchangeHandlerEngine.closeStopTimes();

        // if empty service skipping requested: Filter out trips that do not refer to an active service
		if (config.skipEmptyService()) {
    		File outdir = config.getQualifiedOutputDirectory();
    		String infileName = TransxchangeHandlerEngine.stop_timesFilename + "_tmp" + /* "_" + serviceStartDate + */ TransxchangeHandlerEngine.extension;
        	File infile = new File(outdir, infileName);
        	String outfileName = TransxchangeHandlerEngine.stop_timesFilename + /* "_" + serviceStartDate + */ TransxchangeHandlerEngine.extension;
        	File outfile = new File(outdir, outfileName);
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
    				parser = parsers.next();
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
    						TransxchangeStops.flagStop(inStop); // Flag as included in service for later rollout in skiporphanstop
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
				  TransxchangeStops.flagAllStops("1");
			}
        }
		Map<String,Agency> agencies = consolidateAgencies(); // Eliminiate possible duplicates from multiple input files in zip archive
		Set<String> usedStops = TransxchangeStopTimes.getUsedStops();
    for (String stopId : usedStops) {
      if (!stops.containsKey(stopId)) {
        Stop stop = config.getNaptanStop(stopId);
        if (stop != null) {
          stops.put(stopId, stop);
        }
      }
    }
    usedStops.clear();// reset
		Map<String,Route> routes = consolidateRoutes(); // Eliminiate possible duplicates from multiple input files in zip archive
		
		TransxchangeHandlerEngine.writeOutputStops(stops, config);
		TransxchangeHandlerEngine.writeOutputAgencies(agencies);
		TransxchangeHandlerEngine.writeOutputRoutes(routes);
		parseHandlers = null;// Help GC
		TransxchangeStops.clearStops();
		return TransxchangeHandlerEngine.closeOutput(config.getOutputDirectory());
	}

	/**
	 * Eliminate possible duplicates from multiple input files in zip archive
	 */
  public Map<String, Agency> consolidateAgencies() {
    // Use TreeMap so that we get output sorted by key
    Map<String, Agency> agencyMap = new TreeMap<String, Agency>();// map of agency id to Agency
    for (TransxchangeHandlerEngine parser : parseHandlers) {
      parser.getAgencies().export(agencyMap);
    }
    return agencyMap;
  }

  /**
   * Eliminate possible duplicates from multiple input files in zip archive
   */
  public Map<String, Route> consolidateRoutes() {
    // Use TreeMap so that we get output sorted by key
    Map<String, Route> routeMap = new TreeMap<String, Route>();// map of agency id to Agency
    for (TransxchangeHandlerEngine parser : parseHandlers) {
      parser.getRoutes().export(routeMap);
    }
    return routeMap;
  }
}
