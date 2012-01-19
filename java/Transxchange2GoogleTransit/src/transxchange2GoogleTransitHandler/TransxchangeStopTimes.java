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

package transxchange2GoogleTransitHandler;

import java.io.*;

import java.util.ArrayList;
import java.util.List;

import org.xml.sax.Attributes;
import org.xml.sax.SAXParseException;

/* 
 * This class handles the TransXChange xml input file under the aspect of 
 * 	stop times in trips
 */
public class TransxchangeStopTimes extends TransxchangeDataAspect {

	// xml keys and output field fillers
	static final String[] key_stop_times__trip_id = new String[] {"__tdD", "", "OpenRequired"}; // GTFS required
	static final String[] key_stop_times__arrival_time = new String[] {"__tdD", "", "OpenRequired"}; // GTFS required
	static final String[] key_stop_times__departure_time = new String[] {"__tdD", "", "OpenRequired"}; // GTFS required
	static final String[] key_stop_times__stop_id = new String[] {"StopPointRef", "OpenRequired"}; // GTFS required
	static final String[] key_stop_times__stop_sequence = new String[] {"__tdD", "OpenRequired"}; // GTFS required
	static final String[] key_stop_times__pickup_type = new String[] {"NStp", "", "0"}; // GTFS required
	static final String[] key_stop_times__drop_off_type = new String[] {"__tdD", "", "0"}; // GTFS required
	
	// Parsed data 
	List listStoptimes__trip_id;
	ValueList newStoptimes__trip_id;
	List listStoptimes__arrival_time;
	ValueList newStoptimes__arrival_time;
	List listStoptimes__departure_time;
	ValueList newStoptimes__departure_time;
	List listStoptimes__stop_id;
	ValueList newStoptimes__stop_id;
	List listStoptimes__stop_sequence;
	ValueList newStoptimes__stop_sequence;
	List listStoptimes__pickup_type;
	ValueList newStoptimes__pickup_type;
	List listStoptimes__drop_off_type;
	ValueList newStoptimes__drop_off_type;

	// in support of: activity in VehicleJourny at timing point, e.g. pass timing point
	static final String[] _key_trips_activity_pass = new String [] {"VehicleJourney", "JourneyPatternTimingLinkRef", "To", "Activity", "pass"};
	static final String[] _key_trips_activity_pickup = new String [] {"VehicleJourney", "JourneyPatternTimingLinkRef", "From", "Activity", "pickUp"};
	static final String[] _key_trips_activity_setdown = new String [] {"VehicleJourney", "JourneyPatternTimingLinkRef", "To", "Activity", "setDown"};
	String _journeyPatternTimingLinkRefPass = "";
	List _listTripsJourneyPatternTimingLinkRefPass;
	ValueList newTripsJourneyPatternTimingLinkRefPass;
	String _journeyPatternTimingLinkRefPickup = "";
	List _listTripsJourneyPatternTimingLinkRefPickup;
	ValueList newTripsJourneyPatternTimingLinkRefPickup;
	String _journeyPatternTimingLinkRefSetdown = "";
	List _listTripsJourneyPatternTimingLinkRefSetdown;
	ValueList newTripsJourneyPatternTimingLinkRefSetdown;
	String keyNestedActivity = "";

	// in support of: override runtimes of timing links for individual vehiclejourney
	static final String[] _key_trips_vehicle_journey_runtime = new String [] {"VehicleJourney", "JourneyPatternTimingLinkRef", "RunTime"};
	String _journeyPatternTimingLinkRefRunTime = "";
	List _listTripsTimingLinkRunTime;
	ValueList newTripsTimingLinkRunTime;

	// in support of: unroll stop times in individual trips
	static final String[] _key_journeypattern_section = {"JourneyPatternSection"};
	static final String[] _key_journeypattern_section_key = {"JPS"};
	static final String[] _key_journeypattern_timinglink = {"JourneyPatternSection", "JourneyPatternTimingLink"};
	static final String[] _key_journeypattern_timinglink_key = {"JPTL"};
	static final String[] _key_stoptimes_from = new String [] {"JourneyPatternTimingLink", "From", "StopPointRef"};
	static final String[] _key_stoptimes_waittimeto = new String [] {"JourneyPatternTimingLink", "To", "WaitTime"}; 
	static final String[] _key_stoptimes_waittimefrom = new String [] {"JourneyPatternTimingLink", "From", "WaitTime"};
	static final String[] _key_stoptimes_to = new String [] {"JourneyPatternTimingLink", "To", "StopPointRef"};
	static final String[] _key_stoptimes_runtime = new String [] {"JourneyPatternTimingLink", "RunTime"};
	boolean inJourneyPatternSection = false;
	String keyNestedRunTime = "";
	String runTime = "";
	String waitTimeTo = "";
	String waitTimeToDeferred = ""; // waitTimeTo - required to correecly assign wait time leading TO timing link, i.e. next TimingLink
	String waitTimeFrom = ""; 
	String journeyPatternTimingLink = "";
	String journeyPatternSection = "";
	List _listTimingLinksJourneyPatternTimingLink;
	ValueList newTimingLinksJourneyPatternTimingLink;
	List _listTimingLinksJourneyPatternSection;
	ValueList newTimingLinksJourneyPatternSection;
	List _listTimingLinksFromStop;
	ValueList newTimingLinksFromStop;
	List _listTimingLinksToStop;
	ValueList newTimingLinksToStop;
	List _listTimingLinksRunTime;
	ValueList newTimingLinksRunTime;

	boolean capturedJourneyPatternTimingLinkRef = false;
	String stopPointFrom = "";
	String stopPointTo = "";
	
	int qualifierIx;
	String _vehicleJourneyCode;
	String _departureTime;
	
	static PrintWriter stop_timesOut = null;
	
	public List getListStoptimes__trip_id() {
		return listStoptimes__trip_id;
	}
	public List getListStoptimes__arrival_time() {
		return listStoptimes__arrival_time;
	}
	public List getListStoptimes__departure_time() {
		return listStoptimes__departure_time;
	}
	public List getListStoptimes__stop_id() {
		return listStoptimes__stop_id;
	}
	public List getListStoptimes__stop_sequence() {
		return listStoptimes__stop_sequence;
	}
	public List getListStoptimes__pickup_type() {
		return listStoptimes__pickup_type;
	}
	public List getListStoptimes__drop_off_type() {
		return listStoptimes__drop_off_type;
	}
	public void closeStopTimesOutput() {
		if (stop_timesOut == null)
			return;
		stop_timesOut.close();
		stop_timesOut = null;
	}
	
   	@Override
   	public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException {
		
	    super.startElement(uri, name, qName, atts);
		if (key.equals(_key_trips_activity_pass[0]) && qName.equals(_key_trips_activity_pass[1]))
			keyNested = _key_trips_activity_pass[1];
		if (key.equals(_key_trips_activity_pass[0]) && keyNested.equals(_key_trips_activity_pass[1]) && qName.equals(_key_trips_activity_pass[2]))
			keyNestedActivity = _key_trips_activity_pass[2];
		if (key.equals(_key_trips_activity_pickup[0]) && qName.equals(_key_trips_activity_pickup[1])) 
			keyNested = _key_trips_activity_pickup[1];
		if (key.equals(_key_trips_activity_pickup[0]) && keyNested.equals(_key_trips_activity_pickup[1]) && qName.equals(_key_trips_activity_pickup[2])) 
			keyNestedActivity = _key_trips_activity_pickup[2];
		if (key.equals(_key_trips_activity_pickup[0]) && keyNested.equals(_key_trips_activity_pickup[1]) && keyNestedActivity.equals(_key_trips_activity_pickup[2]) && qName.equals(_key_trips_activity_pickup[3]))
			key = _key_trips_activity_pickup[0];
		if (key.equals(_key_trips_activity_setdown[0]) && qName.equals(_key_trips_activity_setdown[1])) {
			keyNested = _key_trips_activity_setdown[1];
			capturedJourneyPatternTimingLinkRef = false;
		}
		if (key.equals(_key_trips_activity_setdown[0]) && keyNested.equals(_key_trips_activity_setdown[1]) && qName.equals(_key_trips_activity_setdown[2]))
			keyNestedActivity = _key_trips_activity_setdown[2];
		if (qName.equals(_key_trips_vehicle_journey_runtime[0]))
			key = _key_trips_vehicle_journey_runtime[0];
		if (key.equals(_key_trips_vehicle_journey_runtime[0]) && qName.equals(_key_trips_vehicle_journey_runtime[1]))
			keyNested = _key_trips_vehicle_journey_runtime[1];
		if (key.equals(_key_trips_vehicle_journey_runtime[0]) && keyNested.equals(_key_trips_vehicle_journey_runtime[1]) && qName.equals(_key_trips_vehicle_journey_runtime[2]))
			keyNestedActivity = _key_trips_vehicle_journey_runtime[2];

		// Journey pattern runtimes from and to stop points
		if (qName.equals(_key_journeypattern_section[0])) {
			inJourneyPatternSection = !inJourneyPatternSection;
	        qualifierIx = atts.getIndex("id");
	        journeyPatternSection = atts.getValue(qualifierIx);      
		}
		if (inJourneyPatternSection && qName.equals(_key_journeypattern_timinglink[1])) {
	        qualifierIx = atts.getIndex("id");
	        journeyPatternTimingLink = atts.getValue(qualifierIx);      
		}
		if (key.equals(_key_stoptimes_from[0]) && (keyNested.equals(_key_stoptimes_from[1])) && qName.equals(_key_stoptimes_from[2]))
			keyNestedRunTime = _key_stoptimes_from[2];
		if (key.equals(_key_stoptimes_waittimeto[0]) && (keyNested.equals(_key_stoptimes_waittimeto[1])) && qName.equals(_key_stoptimes_waittimeto[2]))
			keyNestedRunTime = _key_stoptimes_waittimeto[2];
		if (key.equals(_key_stoptimes_waittimefrom[0]) && (keyNested.equals(_key_stoptimes_waittimefrom[1])) && qName.equals(_key_stoptimes_waittimefrom[2]))
			keyNestedRunTime = _key_stoptimes_waittimefrom[2];
		if (key.equals(_key_stoptimes_to[0]) && (keyNested.equals(_key_stoptimes_to[1])) && qName.equals(_key_stoptimes_to[2]))
			keyNestedRunTime = _key_stoptimes_to[2];
		if (key.equals(_key_stoptimes_to[0]) && qName.equals(_key_stoptimes_to[1]))
			keyNested = _key_stoptimes_to[1];
		if (key.equals(_key_stoptimes_from[0]) && qName.equals(_key_stoptimes_from[1]))
			keyNested = _key_stoptimes_from[1];
		if (key.equals(_key_stoptimes_waittimeto[0]) && qName.equals(_key_stoptimes_waittimeto[1]))
			keyNested = _key_stoptimes_waittimeto[1];
		if (key.equals(_key_stoptimes_waittimefrom[0]) && qName.equals(_key_stoptimes_waittimefrom[1]))
			keyNested = _key_stoptimes_waittimefrom[1];
		if (key.equals(_key_stoptimes_runtime[0]) && qName.equals(_key_stoptimes_runtime[1]))
			keyNested = _key_stoptimes_runtime[1];
		if (qName.equals(_key_stoptimes_from[0])) 	// this also covers _runtime and _waittime
			key = _key_stoptimes_from[0];
	}
	

   	@Override
	public void endElement (String uri, String name, String qName) {
		if (niceString == null || niceString.length() == 0)
			return;
		
	_vehicleJourneyCode = handler.getTrips().getVehicleJourneyCode();
	_departureTime = handler.getTrips().getDepartureTime();
	if (_vehicleJourneyCode.length() > 0)
	    if (key.equals(_key_trips_activity_pass[0]) && keyNested.equals(_key_trips_activity_pass[1]) && keyNestedActivity.length() == 0) 
	    	_journeyPatternTimingLinkRefPass = niceString;       	
	    if (key.equals(_key_trips_activity_pickup[0]) && keyNested.equals(_key_trips_activity_pickup[1]) && keyNestedActivity.length() == 0) 
	    	_journeyPatternTimingLinkRefPickup = niceString;       	
	    if (key.equals(_key_trips_activity_setdown[0]) && keyNested.equals(_key_trips_activity_setdown[1]) && keyNestedActivity.length() == 0 && !capturedJourneyPatternTimingLinkRef)
	   		_journeyPatternTimingLinkRefSetdown = niceString;
	    if (key.equals(_key_trips_vehicle_journey_runtime[0]) && keyNested.equals(_key_trips_vehicle_journey_runtime[1]) && keyNestedActivity.length() == 0) 
	    	_journeyPatternTimingLinkRefRunTime = niceString;       	
	    if (key.equals(_key_trips_activity_pass[0]) && keyNested.equals(_key_trips_activity_pass[1]) && keyNestedActivity.equals(_key_trips_activity_pass[2]) && niceString.equals(_key_trips_activity_pass[4])
	    		&& _vehicleJourneyCode.length() > 0) {
	    	newTripsJourneyPatternTimingLinkRefPass = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    	_listTripsJourneyPatternTimingLinkRefPass.add(newTripsJourneyPatternTimingLinkRefPass);
	    	newTripsJourneyPatternTimingLinkRefPass.addValue(_journeyPatternTimingLinkRefPass);
	    }
	    if (key.equals(_key_trips_activity_pickup[0]) && keyNested.equals(_key_trips_activity_pickup[1]) && keyNestedActivity.equals(_key_trips_activity_pickup[2]) && niceString.equals(_key_trips_activity_pickup[4])
	    		&& _vehicleJourneyCode.length() > 0) {
	    	newTripsJourneyPatternTimingLinkRefPickup = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    	_listTripsJourneyPatternTimingLinkRefPickup.add(newTripsJourneyPatternTimingLinkRefPickup);
	    	newTripsJourneyPatternTimingLinkRefPickup.addValue(_journeyPatternTimingLinkRefPickup);
	    }
	    if (key.equals(_key_trips_activity_setdown[0]) && keyNested.equals(_key_trips_activity_setdown[1]) && keyNestedActivity.equals(_key_trips_activity_setdown[2]) && niceString.equals(_key_trips_activity_setdown[4])
	    		&& _vehicleJourneyCode.length() > 0) {
	    	newTripsJourneyPatternTimingLinkRefSetdown = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    	_listTripsJourneyPatternTimingLinkRefSetdown.add(newTripsJourneyPatternTimingLinkRefSetdown);
	    	newTripsJourneyPatternTimingLinkRefSetdown.addValue(_journeyPatternTimingLinkRefSetdown);
			_journeyPatternTimingLinkRefSetdown = "";
	    }
	    if (key.equals(_key_trips_vehicle_journey_runtime[0]) && keyNested.equals(_key_trips_vehicle_journey_runtime[1]) && keyNestedActivity.equals(_key_trips_vehicle_journey_runtime[2])
	    		&& _vehicleJourneyCode.length() > 0) {
	    	newTripsTimingLinkRunTime = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    	_listTripsTimingLinkRunTime.add(newTripsTimingLinkRunTime);
	    	newTripsTimingLinkRunTime.addValue(_journeyPatternTimingLinkRefRunTime);
	    	newTripsTimingLinkRunTime.addValue(niceString);
	    }

		// Journey pattern runtimes from and to stop points
	    if (key.equals(_key_stoptimes_from[0]) && keyNested.equals(_key_stoptimes_from[1])&& keyNestedRunTime.equals(_key_stoptimes_from[2])) {
	    	stopPointFrom = niceString; 
	    	keyNestedRunTime = "";
	    }
	    if (key.equals(_key_stoptimes_waittimeto[0]) && keyNested.equals(_key_stoptimes_waittimeto[1])&& keyNestedRunTime.equals(_key_stoptimes_waittimeto[2])) {
	    	waitTimeTo = niceString; 
	    	keyNestedRunTime = "";
	    }
	    if (key.equals(_key_stoptimes_waittimefrom[0]) && keyNested.equals(_key_stoptimes_waittimefrom[1])&& keyNestedRunTime.equals(_key_stoptimes_waittimefrom[2])) {
	    	waitTimeFrom = niceString; 
	    	keyNestedRunTime = "";
	    }
	    if (key.equals(_key_stoptimes_to[0]) && keyNested.equals(_key_stoptimes_to[1])&& keyNestedRunTime.equals(_key_stoptimes_to[2])) {
	    	stopPointTo = niceString; 
	    	keyNestedRunTime = "";
	    	keyNested = "";
	    }
	    if (key.equals(_key_stoptimes_runtime[0]) && keyNested.equals(_key_stoptimes_runtime[1])) {  
	    	runTime = niceString;
	    }
	    if (key.equals(_key_stoptimes_runtime[0]) && keyNested.equals(_key_stoptimes_runtime[1]) && stopPointFrom.length() > 0) {        
	    	newTimingLinksFromStop = new ValueList(_key_stoptimes_from[1]);
	    	_listTimingLinksFromStop.add(newTimingLinksFromStop);
	    	newTimingLinksFromStop.addValue(stopPointFrom);
	    	newTimingLinksToStop = new ValueList(_key_stoptimes_to[1]);
	    	_listTimingLinksToStop.add(newTimingLinksToStop);
	    	newTimingLinksToStop.addValue(stopPointTo);
	    	newTimingLinksRunTime = new ValueList(stopPointFrom);
	    	_listTimingLinksRunTime.add(newTimingLinksRunTime);
	    	newTimingLinksRunTime.addValue(niceString);
	    	if (waitTimeToDeferred.length() > 0) {
	        	newTimingLinksRunTime.addValue(waitTimeToDeferred);
	        	waitTimeToDeferred = "";
	      	}
	    	waitTimeToDeferred = waitTimeTo; // Defer current wait time
	    	waitTimeTo = "";
	    	if (waitTimeFrom.length() > 0) {
	        	newTimingLinksRunTime.addValue(waitTimeFrom);
	        	waitTimeFrom = "";
	      	}
	    	stopPointFrom = "";
	    	newTimingLinksJourneyPatternSection = new ValueList(_key_journeypattern_section_key[0]);
	    	_listTimingLinksJourneyPatternSection.add(newTimingLinksJourneyPatternSection);
	    	newTimingLinksJourneyPatternSection.addValue(journeyPatternSection);
	    	newTimingLinksJourneyPatternTimingLink = new ValueList(_key_journeypattern_timinglink_key[0]); // _key_journeypattern_timinglink[0]);
	    	_listTimingLinksJourneyPatternTimingLink.add(newTimingLinksJourneyPatternTimingLink);
	    	newTimingLinksJourneyPatternTimingLink.addValue(journeyPatternTimingLink);
	    }		
	}

   	@Override
	public void clearKeys (String qName) {
		if (key.equals(_key_trips_activity_pass[0]) && keyNested.equals(_key_trips_activity_pass[1]) && keyNestedActivity.equals(_key_trips_activity_pass[2])) {
			keyNestedActivity = "";
			_journeyPatternTimingLinkRefSetdown = "";
		}
		if (key.equals(_key_trips_activity_pickup[0]) && keyNested.equals(_key_trips_activity_pickup[1]) && keyNestedActivity.equals(_key_trips_activity_pickup[2])) { 
			keyNestedActivity = "";
		}
		if (key.equals(_key_trips_activity_setdown[0]) && qName.equals(_key_trips_activity_setdown[1]))
			capturedJourneyPatternTimingLinkRef = true;
		if (key.equals(_key_trips_vehicle_journey_runtime[0]) && keyNested.equals(_key_trips_vehicle_journey_runtime[1]) && keyNestedActivity.equals(_key_trips_vehicle_journey_runtime[2]))
			keyNestedActivity = "";
	    
		// VehicleJourneys
		if (keyNestedRunTime.equals(_key_stoptimes_from[2]))
			keyNestedRunTime = "";
		if (qName.equals(_key_journeypattern_section[0])) {
			inJourneyPatternSection = !inJourneyPatternSection;
			journeyPatternSection = "";
			key = "";
		}		
	}
	
   	@Override
	public void endDocument() throws IOException {
	    List _listJourneyPatternRef;
	    List _listJourneyPatternSectionRefs;
	    List listTrips__trip_id;
	    int i, j, k, l, jp;
	    int sequenceNumber;
       	int stopTimehhmmss[] = {-1, -1, -1};
	    ValueList iterator, jterator, jpterator;
	    String journeyPatternRef, journeyPatternSectionRef = "", setDownTimingLink, vehicleJourneyRef, pickupTimingLink, passTimingLink;
	    boolean hot, jps, setDownReached, pickedUp, notPassed = true, timingLinkOverrideFound;
	    int waitTimeAdd, runTimeAdd, lastStopOnPattern = 0;
	    int stopTimeInSeconds;
		Integer sn;
		int listSize, listSizeOuter, listSizeInner;

		String outfileName = "";
		File outfile = null;
		String outdir = handler.getRootDirectory() + handler.getWorkDirectory();
	    
        if (stop_timesOut == null) {
    		outfileName = TransxchangeHandlerEngine.stop_timesFilename + /* "_" + serviceStartDate + */ TransxchangeHandlerEngine.extension;
            handler.addFilename(outfileName);
        	if (handler.isSkipEmptyService())
        		outfileName = TransxchangeHandlerEngine.stop_timesFilename + "_tmp" + /* "_" + serviceStartDate + */ TransxchangeHandlerEngine.extension;
            outfile = new File(outdir + /* "/" + serviceStartDate + */ "/"  + outfileName);
            stop_timesOut = new PrintWriter(new FileWriter(outfile));
        	if (!handler.isSkipEmptyService())
        		stop_timesOut.println("trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,pickup_type,drop_off_type,shape_dist_traveled");        	
        }
        
        // Roll out stop times
	    _listJourneyPatternRef = handler.getTrips().getListJourneyPatternRef();
	    _listJourneyPatternSectionRefs = handler.getTrips().getListJourneyPatternSectionRefs();
	    listTrips__trip_id = handler.getTrips().getListTrips__trip_id();
	    for (i = 0; i < _listJourneyPatternRef.size(); i++) { // for all trips
	    	iterator = (ValueList)_listJourneyPatternRef.get(i);
	    	journeyPatternRef = (String)iterator.getValue(0);

	    	jp = 0;
	       	sequenceNumber = 1;     	
	       	stopTimehhmmss[0] = -1;
	       	stopTimehhmmss[1] = -1;
	       	stopTimehhmmss[2] = -1;
	       	listSizeOuter = _listJourneyPatternSectionRefs.size();
	       	while (jp < listSizeOuter) { // for all referenced journeyPatternSections (stop sequence with timing links)
	        	jps = true;
	        	jpterator = (ValueList)_listJourneyPatternSectionRefs.get(jp);
	       		if (jpterator.getKeyName().equals(journeyPatternRef)) {
	       			journeyPatternSectionRef = (String)jpterator.getValue(0);
	       			jps = false;
	       		}
	       		jp++;
	       		if (!jps) { // JourneyPatternSection found 
	       			j = 0; // Find out if this vehicle journey (as identified by iterator.geyKeyName())has a setDown (= premature end) and store link in setDownTimingLink
	       			hot = true;
	       			setDownTimingLink = "";
	       			listSize = _listTripsJourneyPatternTimingLinkRefSetdown.size();
	       			while (hot && j < listSize) {
	       				vehicleJourneyRef = (String)((ValueList)_listTripsJourneyPatternTimingLinkRefSetdown.get(j)).getKeyName();
	       				if (iterator.getKeyName().equals(vehicleJourneyRef)) {
	       					hot = false;
	       					setDownTimingLink = (String)((ValueList)_listTripsJourneyPatternTimingLinkRefSetdown.get(j)).getValue(0);
	       				} else
	       					j++;
	       			}

	       			j = 0; // Find out if this vehicle journey has a late pickup and store link in pickUpTimingLink
	       			hot = true;
	       			pickupTimingLink = "";
	       			listSize = _listTripsJourneyPatternTimingLinkRefPickup.size();
	       			while (hot && j < listSize) {
	       				vehicleJourneyRef = (String)((ValueList)_listTripsJourneyPatternTimingLinkRefPickup.get(j)).getKeyName();
	       				if (iterator.getKeyName().equals(vehicleJourneyRef)) {
	       					hot = false;
	       					pickupTimingLink = (String)((ValueList)_listTripsJourneyPatternTimingLinkRefPickup.get(j)).getValue(0);
	       				} else
	       					j++;
	       			}
	       	
	       			j = 0;
	       			setDownReached = false;
	       			pickedUp = (pickupTimingLink.length() == 0); // If no late pickup in vehicle journey, then start at first stop
	       			listSize = _listTimingLinksJourneyPatternSection.size();
	       			while (!setDownReached && j < listSize) { // Unroll stop sequence in trip
	       				jterator = (ValueList)_listTimingLinksJourneyPatternSection.get(j);
	       				if (jterator.getValue(0).equals(journeyPatternSectionRef)) {
	       					if (sequenceNumber == 1)
	       						readTransxchangeTime(stopTimehhmmss, (String)((ValueList)listTrips__trip_id.get(i)).getValue(0));
	       					hot = true;
	       					k = 0; // Find out if this stop is being passed
	       					listSizeInner = _listTripsJourneyPatternTimingLinkRefPass.size();
	       					while (hot && k < listSizeInner) {
	       						passTimingLink = (String)((ValueList)_listTripsJourneyPatternTimingLinkRefPass.get(k)).getValue(0);
	       						vehicleJourneyRef = (String)((ValueList)_listTripsJourneyPatternTimingLinkRefPass.get(k)).getKeyName();
	       						if (iterator.getKeyName().equals(vehicleJourneyRef) && passTimingLink.equals((String)((ValueList)_listTimingLinksJourneyPatternTimingLink.get(j)).getValue(0)))
	       							hot = false;
	       						else
	       							k++;
	       					}
	       					// Find out if we reached late pickup stop
	       					if (!pickedUp && pickupTimingLink.equals((String)((ValueList)_listTimingLinksJourneyPatternTimingLink.get(j)).getValue(0)))
	       						pickedUp = true;
	       					if (pickedUp) {
	       						newStoptimes__trip_id = new ValueList(iterator.getKeyName());
	       						listStoptimes__trip_id.add(newStoptimes__trip_id);
	       						newStoptimes__trip_id.addValue(journeyPatternRef);			
	       						newStoptimes__arrival_time = new ValueList(iterator.getKeyName());
	       						listStoptimes__arrival_time.add(newStoptimes__arrival_time);
	       						if (sequenceNumber > 1 && notPassed && !setDownReached) // Arrival time if not first stop and not a pass
	       							newStoptimes__arrival_time.addValue(TransxchangeDataAspect.formatTime(stopTimehhmmss[0], stopTimehhmmss[1]));
	       						else { 
	       							
	       							// Conformance with GTFS revision 20-Nov-2007: If first stop, arrival time = departure time
	       							if (sequenceNumber == 1)
	       								newStoptimes__arrival_time.addValue(TransxchangeDataAspect.formatTime(stopTimehhmmss[0], stopTimehhmmss[1]));
	       							else
	       								newStoptimes__arrival_time.addValue("");
	       						}
	       						if (((ValueList)_listTimingLinksRunTime.get(j)).getValue(1) != null) { // add wait time #1 ?
	       							waitTimeAdd = readTransxchangeFrequency((String)((ValueList)_listTimingLinksRunTime.get(j)).getValue(1));
	       			        		stopTimeInSeconds = stopTimehhmmss[2] + stopTimehhmmss[1] * 60 + stopTimehhmmss[0] * 3600;
	       			        		stopTimeInSeconds += waitTimeAdd;
	       			        		stopTimehhmmss[0] = stopTimeInSeconds / 3600;
	       			        		stopTimehhmmss[1] = (stopTimeInSeconds / 60) % 60;
	       			        		stopTimehhmmss[2] = stopTimeInSeconds % 60;

	       						}
	       						if (((ValueList)_listTimingLinksRunTime.get(j)).getValue(2) != null) { // add wait time # 2 ?
	       							waitTimeAdd = readTransxchangeFrequency((String)((ValueList)_listTimingLinksRunTime.get(j)).getValue(2));
	       			        		stopTimeInSeconds = stopTimehhmmss[2] + stopTimehhmmss[1] * 60 + stopTimehhmmss[0] * 3600;
	       			        		stopTimeInSeconds += waitTimeAdd;
	       			        		stopTimehhmmss[0] = stopTimeInSeconds / 3600;
	       			        		stopTimehhmmss[1] = (stopTimeInSeconds / 60) % 60;
	       			        		stopTimehhmmss[2] = stopTimeInSeconds % 60;
	       						}
	       						newStoptimes__departure_time = new ValueList(iterator.getKeyName());
	       						listStoptimes__departure_time.add(newStoptimes__departure_time);
	       						if (notPassed && !setDownReached) // Departure time if no pass, else empty
	       							newStoptimes__departure_time.addValue(TransxchangeDataAspect.formatTime(stopTimehhmmss[0], stopTimehhmmss[1]));
	       						else
	       							newStoptimes__departure_time.addValue("");
	       						newStoptimes__stop_id = new ValueList(journeyPatternSectionRef); 
	       						listStoptimes__stop_id.add(newStoptimes__stop_id);
	       						newStoptimes__stop_id.addValue((String)((ValueList)_listTimingLinksFromStop.get(j)).getValue(0));
	       						handler.getStops().addStop((String)((ValueList)_listTimingLinksFromStop.get(j)).getValue(0));
	       						newStoptimes__stop_sequence = new ValueList(journeyPatternSectionRef); 
	       						listStoptimes__stop_sequence.add(newStoptimes__stop_sequence);
								sn = new Integer(sequenceNumber);
								newStoptimes__stop_sequence.addValue(sn.toString());
								sn = null;
	       						sequenceNumber++;
	            	
	       						// Find out if timing link runtime is overridden by vehicle journey specific run times
	       						l = 0;
	       						timingLinkOverrideFound = false;
	       						listSizeInner = _listTripsTimingLinkRunTime.size();
	       						while (!timingLinkOverrideFound && l < listSizeInner) {
	       							if (iterator.getKeyName().equals((String)((ValueList)_listTripsTimingLinkRunTime.get(l)).getKeyName()) && ((String)((ValueList)_listTimingLinksJourneyPatternTimingLink.get(j)).getValue(0)).equals((String)((ValueList)_listTripsTimingLinkRunTime.get(l)).getValue(0))) 
	       								timingLinkOverrideFound = true;
	       							else
	       								l++;
	       						}
	       						if (timingLinkOverrideFound)
	       							runTimeAdd = readTransxchangeFrequency((String)((ValueList)_listTripsTimingLinkRunTime.get(l)).getValue(1));
	       						else
	       							runTimeAdd = readTransxchangeFrequency((String)((ValueList)_listTimingLinksRunTime.get(j)).getValue(0));
       			        		stopTimeInSeconds = stopTimehhmmss[2] + stopTimehhmmss[1] * 60 + stopTimehhmmss[0] * 3600;
       			        		stopTimeInSeconds += runTimeAdd;
       			        		stopTimehhmmss[0] = stopTimeInSeconds / 3600;
       			        		stopTimehhmmss[1] = (stopTimeInSeconds / 60) % 60;
       			        		stopTimehhmmss[2] = stopTimeInSeconds % 60;
	       						newStoptimes__pickup_type = new ValueList(key_stop_times__pickup_type[0]);
	       						listStoptimes__pickup_type.add(newStoptimes__pickup_type);
	       						newStoptimes__pickup_type.addValue(key_stop_times__pickup_type[2]);
	       						newStoptimes__drop_off_type = new ValueList(key_stop_times__drop_off_type[0]);
	       						listStoptimes__drop_off_type.add(newStoptimes__drop_off_type);
	       						newStoptimes__drop_off_type.addValue(key_stop_times__drop_off_type[2]);
	   			
	       						lastStopOnPattern = j;   			
	       						notPassed = hot;
	       					}
	    			
	       					// Find out if setdown has been reached
	       					if (setDownTimingLink.equals((String)((ValueList)_listTimingLinksJourneyPatternTimingLink.get(j)).getValue(0)))
	       						setDownReached = true;
	       				} 
	       				j++;
	       			}
	       		}
	       	}
	   		// Add last stop in vehicle journey
	   		if (_listTimingLinksJourneyPatternSection.size() > 0) { // && jp == _listJourneyPatternSectionRefs.size()) { 
	   			newStoptimes__trip_id = new ValueList(iterator.getKeyName());
	   			listStoptimes__trip_id.add(newStoptimes__trip_id);
	   			newStoptimes__trip_id.addValue(journeyPatternRef);			
	   			newStoptimes__arrival_time = new ValueList(iterator.getKeyName());
	   			listStoptimes__arrival_time.add(newStoptimes__arrival_time);
	   			if (notPassed)
	   				newStoptimes__arrival_time.addValue(TransxchangeDataAspect.formatTime(stopTimehhmmss[0], stopTimehhmmss[1]));
	   			else
	   				newStoptimes__arrival_time.addValue("");
	   			newStoptimes__departure_time = new ValueList(iterator.getKeyName()); // departure time
	   			listStoptimes__departure_time.add(newStoptimes__departure_time);

	   			// Conformance with GTFS revision 20-Nov-2007: Departure time at last stop
	   			newStoptimes__departure_time.addValue(TransxchangeDataAspect.formatTime(stopTimehhmmss[0], stopTimehhmmss[1]));   	    	
	   			newStoptimes__stop_id = new ValueList(journeyPatternSectionRef); 
	   			listStoptimes__stop_id.add(newStoptimes__stop_id);
	   			newStoptimes__stop_id.addValue((String)((ValueList)_listTimingLinksToStop.get(lastStopOnPattern)).getValue(0));
	   			handler.getStops().addStop((String)((ValueList)_listTimingLinksToStop.get(lastStopOnPattern)).getValue(0));
	   			newStoptimes__stop_sequence = new ValueList(journeyPatternSectionRef); 
	   			listStoptimes__stop_sequence.add(newStoptimes__stop_sequence);
				sn = new Integer(sequenceNumber);
				newStoptimes__stop_sequence.addValue(sn.toString());
				sn = null;
	   			newStoptimes__pickup_type = new ValueList(key_stop_times__pickup_type[0]);
	   			listStoptimes__pickup_type.add(newStoptimes__pickup_type);
	   			newStoptimes__pickup_type.addValue(key_stop_times__pickup_type[2]);
	   			newStoptimes__drop_off_type = new ValueList(key_stop_times__drop_off_type[0]);
	   			listStoptimes__drop_off_type.add(newStoptimes__drop_off_type);
	   			newStoptimes__drop_off_type.addValue(key_stop_times__drop_off_type[2]);
	   		}
	   		
	        for (int ii = 0; ii < this.getListStoptimes__trip_id().size(); ii++) {
	        	stop_timesOut.print(((ValueList)this.getListStoptimes__trip_id().get(ii)).getKeyName());
	        	stop_timesOut.print(",");
	        	stop_timesOut.print(((ValueList)this.getListStoptimes__arrival_time().get(ii)).getValue(0));
	        	stop_timesOut.print(",");
	        	stop_timesOut.print(((ValueList)this.getListStoptimes__departure_time().get(ii)).getValue(0));
	        	stop_timesOut.print(",");
	        	stop_timesOut.print(((ValueList)this.getListStoptimes__stop_id().get(ii)).getValue(0));
	        	stop_timesOut.print(",");
	        	stop_timesOut.print(((ValueList)this.getListStoptimes__stop_sequence().get(ii)).getValue(0));
	        	stop_timesOut.print(",");
	        	stop_timesOut.print(",");
	        	stop_timesOut.print(((ValueList)this.getListStoptimes__pickup_type().get(ii)).getValue(0));
	        	stop_timesOut.print(",");
	        	stop_timesOut.print(((ValueList)this.getListStoptimes__drop_off_type().get(ii)).getValue(0));
	        	stop_timesOut.println(",");
	        }       
	        listStoptimes__trip_id.clear();
	    	listStoptimes__arrival_time.clear();
	    	listStoptimes__departure_time.clear();
	    	listStoptimes__stop_id.clear();
	    	listStoptimes__stop_sequence.clear();
	    	listStoptimes__pickup_type.clear();
	    	listStoptimes__drop_off_type.clear();
	    }
	}
	
   	@Override
	public void completeData() {
  	    // Add quotes if needed
  	    csvProofList(listStoptimes__trip_id);
  	    csvProofList(listStoptimes__arrival_time);
  	    csvProofList(listStoptimes__departure_time);
  	    csvProofList(listStoptimes__stop_id);
  	    csvProofList(listStoptimes__stop_sequence);
  	    csvProofList(listStoptimes__pickup_type);
  	    csvProofList(listStoptimes__drop_off_type);
	}

   	@Override
	public void dumpValues() {
		int i;
		ValueList iterator;

		System.out.println("*** Timing Links Pass");
	    for (i = 0; i < _listTripsJourneyPatternTimingLinkRefPass.size(); i++) {
		    iterator = (ValueList)_listTripsJourneyPatternTimingLinkRefPass.get(i);
		    iterator.dumpValues();
		}
		System.out.println("*** Timing Links Pickup");  
	    for (i = 0; i < _listTripsJourneyPatternTimingLinkRefPickup.size(); i++) {
		    iterator = (ValueList)_listTripsJourneyPatternTimingLinkRefPickup.get(i);
		    iterator.dumpValues();
		}
		System.out.println("*** Timing Links Setdown");  
	    for (i = 0; i < _listTripsJourneyPatternTimingLinkRefSetdown.size(); i++) {
		    iterator = (ValueList)_listTripsJourneyPatternTimingLinkRefSetdown.get(i);
		    iterator.dumpValues();
		}
		System.out.println("*** Timing Links Runtimes");  
	    for (i = 0; i < _listTripsTimingLinkRunTime.size(); i++) {
		    iterator = (ValueList)_listTripsTimingLinkRunTime.get(i);
		    iterator.dumpValues();
		}
//		for (int i = 0; i < listTrips__block_id.size(); i++) {
//		    iterator = (ValueList)listTrips__block_id.get(i);
//		    iterator.dumpValues();
//		}
		System.out.println("*** Timing Links");
		for (i = 0; i < _listTimingLinksFromStop.size(); i++) {
		    iterator = (ValueList)_listTimingLinksFromStop.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < _listTimingLinksToStop.size(); i++) {
		    iterator = (ValueList)_listTimingLinksToStop.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < _listTimingLinksRunTime.size(); i++) {
		    iterator = (ValueList)_listTimingLinksRunTime.get(i);
		    iterator.dumpValues();
		} 
		for (i = 0; i < _listTimingLinksJourneyPatternSection.size(); i++) {
		    iterator = (ValueList)_listTimingLinksJourneyPatternSection.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < _listTimingLinksJourneyPatternTimingLink.size(); i++) {
		    iterator = (ValueList)_listTimingLinksJourneyPatternTimingLink.get(i);
		    iterator.dumpValues();
		}

		System.out.println("*** Stop Times");
		for (i = 0; i < listStoptimes__trip_id.size(); i++) {
		    iterator = (ValueList)listStoptimes__trip_id.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listStoptimes__stop_id.size(); i++) {
		    iterator = (ValueList)listStoptimes__stop_id.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listStoptimes__stop_sequence.size(); i++) {
		    iterator = (ValueList)listStoptimes__stop_sequence.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listStoptimes__arrival_time.size(); i++) {
		    iterator = (ValueList)listStoptimes__arrival_time.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listStoptimes__departure_time.size(); i++) {
		    iterator = (ValueList)listStoptimes__departure_time.get(i);
		    iterator.dumpValues();
		}
//		for (i = 0; i < listStoptimes__pickup_type.size(); i++) {
//		    iterator = (ValueList)listStoptimes__pickup_type.get(i);
//		    iterator.dumpValues();
//		}
//		for (i = 0; i < listStoptimes__drop_off_type.size(); i++) {
//		    iterator = (ValueList)listStoptimes__drop_off_type.get(i);
//		    iterator.dumpValues();
//		}		
	}
	
	
	public TransxchangeStopTimes(TransxchangeHandlerEngine owner) {
		super(owner);
		listStoptimes__trip_id = new ArrayList();
		listStoptimes__arrival_time = new ArrayList();
		listStoptimes__departure_time = new ArrayList();
		listStoptimes__stop_id = new ArrayList();
		listStoptimes__stop_sequence = new ArrayList();
		listStoptimes__pickup_type = new ArrayList();
		listStoptimes__drop_off_type = new ArrayList();
		
		_listTripsJourneyPatternTimingLinkRefPass = new ArrayList();
		_listTripsJourneyPatternTimingLinkRefPickup = new ArrayList();
		_listTripsJourneyPatternTimingLinkRefSetdown = new ArrayList();
		_listTripsTimingLinkRunTime = new ArrayList();
		_listTimingLinksFromStop = new ArrayList();
		_listTimingLinksToStop = new ArrayList();
		_listTimingLinksRunTime = new ArrayList();
		_listTimingLinksJourneyPatternSection = new ArrayList();
		_listTimingLinksJourneyPatternTimingLink = new ArrayList();

		handler = owner;
	}	
}
