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

import java.util.ArrayList;
import java.util.List;

import org.xml.sax.Attributes;
import org.xml.sax.SAXParseException;

import transxchange2GoogleTransit.Util;

/*
 * This class handles the TransXChange xml input file under the aspect of
 * 	trips
 */
public class TransxchangeTrips extends TransxchangeDataAspect {

	// xml keys and output field fillers
	static final String[] key_trips__route_id = new String[] {"VehicleJourney", "LineRef", "OpenRequired"}; // GTFS required
	static final String[] key_trips__service_id = new String[] {"VehicleJourney", "ServiceRef", "OpenRequired"}; // GTFS required
	static final String[] key_trips__trip_id = new String[] {"VehicleJourney", "VehicleJourneyCode", "OpenRequired"}; // GTFS required
	static final String[] key_trips__trip_headsign = new String [] {"JourneyPattern", "DestinationDisplay", "OpenRequired"};
	static final String[] key_trips__trip_direction = new String [] {"JourneyPattern", "Direction", ""}; // v1.7.3
	static final String[] key_trips__trip_routeref = new String [] {"JourneyPattern", "RouteRef", ""}; // v1.7.3
	static final String[] key_trips__block_id = new String[] {"__transxchange2GTFS_drawDefault", "", ""};

	// Parsed data
	List<ValueList> listTrips__route_id;
	List<ValueList> listTrips__service_id;
	List<ValueList> listTrips__trip_id;
	List<ValueList> listTrips__trip_headsign;
	List<ValueList> listTrips__block_id;
	List<ValueList> listTrips__direction_id; // v1.7.3
	List<ValueList> listTrips__routeref; // v1.7.3

	static final String[] _key_trips__trip_journeypatternsection = new String [] {"JourneyPattern", "JourneyPatternSectionRefs"};
	List<ValueList> _listJourneyPatternDestinationDisplays;
	ValueList newJourneyPatternDestinationDisplay;
	List<ValueList> _listJourneyPatternRef;
	List<ValueList> _listJourneyPatternSectionRefs;
	List<ValueList> _listJourneyPatternDirections; // v1.7.3
	List<ValueList> _listJourneyPatternRouteRef; // v1.7.3

	String _journeyPattern = "";

	static final String[] _key_trips_departure_time = new String [] {"VehicleJourney", "DepartureTime"};
	static final String[] _key_trips_endtime = new String [] {"VehicleJourney", "EndTime"};
	static final String[] _key_trips_frequency = new String [] {"VehicleJourney", "ScheduledFrequency"};
	static final String[] _key_trips_journeypatternref = new String [] {"VehicleJourney", "JourneyPatternRef"};
	static final String[] _key_trips_journeypatternref2 = new String [] {"VehicleJourney", "VehicleJourneyRef"};
	String _vehicleJourneyCode = "";
	String _departureTime = "";
	String _endTime  ="";
	String _scheduledFrequency = "";
	String _serviceCode = "";
	String _lineName = "";
	String _journeyPatternRef = "";
	String _vehicleJourneyRef = "";

	public List<ValueList> getListTrips__route_id() {
		return listTrips__route_id;
	}
	public List<ValueList> getListTrips__service_id() {
		return listTrips__service_id;
	}
	public List<ValueList> getListTrips__trip_id() {
		return listTrips__trip_id;
	}
	public List<ValueList> getListTrips__trip_headsign() {
		return listTrips__trip_headsign;
	}
	// v1.7.3
	public List<ValueList> getListTrips__direction_id() {
		return listTrips__direction_id;
	}
	public List<ValueList> getListTrips__block_id() {
		return listTrips__block_id;
	}
	public List<ValueList> getListTrips__routeref() {
		return listTrips__routeref;
	}
	public List<ValueList> getListJourneyPatternRef() {
		return _listJourneyPatternRef;
	}
	public List<ValueList> getListJourneyPatternSectionRefs() {
		return _listJourneyPatternSectionRefs;
	}
	String getVehicleJourneyCode() {
		return _vehicleJourneyCode;
	}
	String getDepartureTime() {
		return _departureTime;
	}
	String getJourneyPattern() {
		return _journeyPattern;
	}

	void setJourneyPattern(String jp) {
		_journeyPattern = jp;
	}

/*	String getService(String trip) {
		if (trip == null || trip.length() == 0)
			return "";
		boolean found = false;
		int i = 0;
		String result = "";
		while (!found && i < listTrips__service_id.size()) {
			if ((listTrips__service_id.get(i)).getKeyName().equals(trip))
				found = true;
			else
				i++;
		}
		if (found)
			result = (listTrips__service_id.get(i)).getValue(0);
		return result;
	}
*/
   	@Override
	public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException {

	    super.startElement(uri, name, qName, atts);

		if (qName.equals(key_trips__route_id[0]))
			key = key_trips__route_id[0]; // this also covers trip_service_id, _trip_id, _departure_time, _endtime, _scheduled_frequency, _journeypatternref, _journetpatternref2
		if (key.equals(key_trips__route_id[0]) && qName.equals(key_trips__route_id[1]))
			keyNested = key_trips__route_id[1];
		if (key.equals(key_trips__service_id[0]) && qName.equals(key_trips__service_id[1]))
			keyNested = key_trips__service_id[1];
		if (key.equals(key_trips__trip_id[0]) && qName.equals(key_trips__trip_id[1]))
			keyNested = key_trips__trip_id[1];
		if (key.equals(key_trips__service_id[0]) && qName.equals(key_trips__service_id[1]))
			keyNested = key_trips__service_id[1];
		if (key.equals(_key_trips_departure_time[0]) && qName.equals(_key_trips_departure_time[1]))
			keyNested = _key_trips_departure_time[1];
		if (key.equals(_key_trips_endtime[0]) && qName.equals(_key_trips_endtime[1]))
			keyNested = _key_trips_endtime[1];
		if (key.equals(_key_trips_frequency[0]) && qName.equals(_key_trips_frequency[1]))
			keyNested = _key_trips_frequency[1];
		if (key.equals(_key_trips_journeypatternref[0]) && qName.equals(_key_trips_journeypatternref[1]))
			keyNested = _key_trips_journeypatternref[1];
		if (key.equals(_key_trips_journeypatternref2[0]) && qName.equals(_key_trips_journeypatternref2[1]))
			keyNested = _key_trips_journeypatternref2[1];
		if (qName.equals(key_trips__trip_headsign[0])) {
	        int qualifierIx = atts.getIndex("id");
	        _journeyPattern = atts.getValue(qualifierIx);
			key = key_trips__trip_headsign[0];
		}
		if (key.equals(key_trips__trip_headsign[0]) && qName.equals(key_trips__trip_headsign[1]))
			keyNested = key_trips__trip_headsign[1];
		if (key.equals(_key_trips__trip_journeypatternsection[0]) && qName.equals(_key_trips__trip_journeypatternsection[1]))
			keyNested = _key_trips__trip_journeypatternsection[1];
		// v1.7.3
		if (key.equals(key_trips__trip_direction[0]) && qName.equals(key_trips__trip_direction[1]))
			keyNested = key_trips__trip_direction[1];
		if (key.equals(key_trips__trip_routeref[0]) && qName.equals(key_trips__trip_routeref[1]))
			keyNested = key_trips__trip_routeref[1];
	}

   	@Override
	public void endElement(String uri, String name, String qName) {
	    boolean hot;

	    /*
	     * Local class to create trip structure either for single trip, or unrolled based on frequency (called further below)
	     */
	    class TripStructure {
	    	 void createTripStructure() {
	    		 /*
	    		  * Find out if out-of-line calendar dates where picked up earlier and assign to current VehicleJourney
	    		  */
	    		 String tripId;
	    		 List<ValueList> oolStart = handler.getCalendarDates().getListOOLDates_start();
//	    		 List oolEnd = handler.getCalendarDates().getListOOLDates_end();

	    		 if (oolStart != null) {
	    			 // found out-of-line dates
	    			 List<ValueList> calendarServices = handler.getCalendar().getListCalendar__service_id();
	    			 int i = 0;
	    			 boolean found = false;

	    			 // find matching service in calendar data structure. This assumes the service has already been defined in XML file. This is normally the case
	    			 while (i < calendarServices.size() && !found) {
	    				 if ((calendarServices.get(i)).getValue(0).equals(_serviceCode))
	    					 found = true;
	    				 else
	    					 i++;
	    			 }
	    			 if (found) {
	    				 // matching service found
	    				 // generate service key specifically for current VehicleJourney
		    			 handler.getCalendar().calendarDuplicateService(_serviceCode, _serviceCode + "_" + _vehicleJourneyCode + "@" + _departureTime);
		    			 _serviceCode = _serviceCode + "_" + _vehicleJourneyCode + "@" + _departureTime;
		    			 handler.getCalendarDates().calendarDatesRolloutOOLDates(_serviceCode);
	    			 }
	    			 handler.getCalendarDates().resetOOLDates_start();
	    			 handler.getCalendarDates().resetOOLDates_end();
	    		 }
	    		 ValueList newTrips__trip_id = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    		 listTrips__trip_id.add(newTrips__trip_id);
	    		 newTrips__trip_id.addValue(_departureTime);
	    		 ValueList newTrips__route_id = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    		 listTrips__route_id.add(newTrips__route_id);
	    		 newTrips__route_id.addValue(_lineName);
	    		 tripId = _vehicleJourneyCode + "@" + _departureTime;
	    		 ValueList newTrips__service_id = new ValueList(tripId);
	    		 handler.addTripServiceId(tripId, _serviceCode);
	    		 listTrips__service_id.add(newTrips__service_id);
	    		 newTrips__service_id.addValue(_serviceCode);
	    		 ValueList newJourneyPatternRef = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    		 _listJourneyPatternRef.add(newJourneyPatternRef);
	    		 newJourneyPatternRef.addValue(_journeyPatternRef);
	    		 ValueList newTrips__block_id = new ValueList(_vehicleJourneyCode + "@" + _departureTime);
	    		 listTrips__block_id.add(newTrips__block_id);
	    		 newTrips__block_id.addValue(key_trips__block_id[2]);
	    	 }
	    }

		if (niceString == null || niceString.length() == 0)
	    	return;

        if (key.equals(key_trips__trip_id[0]) && keyNested.equals(key_trips__trip_id[1])) {
        	_vehicleJourneyCode = niceString;
        	keyNested = "";
        }
        if (key.equals(key_trips__route_id[0]) && keyNested.equals(key_trips__route_id[1])) {
        	_lineName = niceString;
        	keyNested = "";
        }
        if (key.equals(key_trips__service_id[0]) && keyNested.equals(key_trips__service_id[1])) {
        	_serviceCode = niceString;
        	keyNested = "";
        }
        if (key.equals(_key_trips_journeypatternref[0]) && keyNested.equals(_key_trips_journeypatternref[1])) {
        	_journeyPatternRef = niceString;
        	keyNested = "";
        }
        if (key.equals(_key_trips_journeypatternref2[0]) && keyNested.equals(_key_trips_journeypatternref2[1])) {
        	_vehicleJourneyRef = niceString;
        	keyNested = "";
        }
        if (key.equals(_key_trips_departure_time[0]) && keyNested.equals(_key_trips_departure_time[1])) {
			_departureTime = niceString;
			new TripStructure().createTripStructure();
			keyNested = "";
        }
        if (key.equals(_key_trips_endtime[0]) && keyNested.equals(_key_trips_endtime[1])) {
        	_endTime = niceString;
        	keyNested = "";
        }
        if (key.equals(_key_trips_frequency[0]) && keyNested.equals(_key_trips_frequency[1])) {
        	_scheduledFrequency = niceString;
        	// Unroll transxchange:vehicle journeys with frequency to GTFS: descrete trips. In the first few versions of GTFS, there did not exist frequency.txt
        	int frequency = 0;
        	int[] departureTimehhmmss = {-1, -1, -1};
        	int[] endTimehhmmss = {-1, -1, -1};

        	Util.readTransxchangeTime(departureTimehhmmss, _departureTime);
        	Util.readTransxchangeTime(endTimehhmmss, _endTime);
        	frequency = Util.readTransxchangeFrequency(_scheduledFrequency);
        	hot = (frequency > 0);
        	while (hot) {
        		int departureTimeInSeconds = departureTimehhmmss[2] + departureTimehhmmss[1] * 60 + departureTimehhmmss[0] * 3600;
        		departureTimeInSeconds += frequency;
        		departureTimehhmmss[0] = departureTimeInSeconds / 3600;
        		departureTimehhmmss[1] = (departureTimeInSeconds / 60) % 60;
        		departureTimehhmmss[2] = departureTimeInSeconds % 60;
        		if (departureTimehhmmss[0] > endTimehhmmss[0])
        			hot = false;
        		else
        			if (departureTimehhmmss[0] >= endTimehhmmss[0])
        				if (departureTimehhmmss[1] > endTimehhmmss[1])
        					hot = false;
        		if (hot) {
        			_departureTime = Util.formatTime(departureTimehhmmss[0], departureTimehhmmss[1]);
        			new TripStructure().createTripStructure();
        		}
        	}
        	keyNested = "";
        }
        if (key.equals(key_trips__trip_headsign[0]) && keyNested.equals(key_trips__trip_headsign[1])) {
        	newJourneyPatternDestinationDisplay = new ValueList(_journeyPattern);
        	_listJourneyPatternDestinationDisplays.add(newJourneyPatternDestinationDisplay);
        	newJourneyPatternDestinationDisplay.addValue(niceString);
		}
        // v1.7.3
        if (key.equals(key_trips__trip_direction[0]) && keyNested.equals(key_trips__trip_direction[1])) {
          ValueList newJourneyPatternDirection = new ValueList(_journeyPattern);
        	_listJourneyPatternDirections.add(newJourneyPatternDirection);
        	boolean directionDetermined = false;
        	if (niceString.equals("outbound")) {
        		newJourneyPatternDirection.addValue("0");
        		directionDetermined = true;
        	}
        	if (niceString.equals("inbound")) {
        		newJourneyPatternDirection.addValue("1");
        		directionDetermined = true;
        	}
        	if (!directionDetermined)
        		newJourneyPatternDirection.addValue("");
		}
        if (key.equals(key_trips__trip_routeref[0]) && keyNested.equals(key_trips__trip_routeref[1])) {
          ValueList newJourneyPatternRouteRef = new ValueList(_journeyPattern);
        	_listJourneyPatternRouteRef.add(newJourneyPatternRouteRef);
    		newJourneyPatternRouteRef.addValue(niceString);
		}
        if (key.equals(_key_trips__trip_journeypatternsection[0]) && keyNested.equals(_key_trips__trip_journeypatternsection[1])) {
          ValueList newJourneyPatternSectionRefs = new ValueList(_journeyPattern);
        	_listJourneyPatternSectionRefs.add(newJourneyPatternSectionRefs);
        	newJourneyPatternSectionRefs.addValue(niceString);
		}
	}

   	@Override
	public void clearKeys(String qName) {
		if (qName.equals(key_trips__trip_headsign[1]))
			keyNested = "";
		// v1.7.3
		if (qName.equals(key_trips__trip_direction[1]))
			keyNested = "";
		if (qName.equals(key_trips__trip_routeref[1]))
			keyNested = "";
		if (qName.equals(_key_trips__trip_journeypatternsection[0]))
			key = "";
        if (key.equals(_key_trips__trip_journeypatternsection[0]) && keyNested.equals(_key_trips__trip_journeypatternsection[1])) {
        	keyNested = "";
        }
		if (qName.equals(key_trips__route_id[0])) { // covers all _trip nested keys
			key = "";
			_journeyPattern = "";
			_vehicleJourneyCode = "";
			_departureTime = "";
			_endTime = "";
			_scheduledFrequency = "";
			_serviceCode = "";
			_lineName = "";
	    	_vehicleJourneyCode = "";
	    	_vehicleJourneyRef = "";
		}
	}

   	@Override
	public void endDocument() {
		int i, j;
		boolean hot;
		ValueList iterator, jterator;
	    String tripHeadsign, tripDirection, tripRouteRef;
		String journeyPatternRef = "";

	    // Roll out trip headsigns
	    for (i = 0; i < _listJourneyPatternRef.size(); i++) {
	    	iterator = _listJourneyPatternRef.get(i);
	    	journeyPatternRef = iterator.getValue(0);
	    	j = 0;
	    	hot = true;
	    	tripHeadsign = "";
	       	while (hot && j < _listJourneyPatternDestinationDisplays.size()) { // find associated destination
	        	jterator = _listJourneyPatternDestinationDisplays.get(j);
	       		if (jterator.getKeyName().equals(journeyPatternRef)) {
	       			tripHeadsign = jterator.getValue(0);
	       			hot = false;
	       		} else
	       			j++;
	       	}
	       	ValueList newTrips__trip_headsign = new ValueList(iterator.getKeyName());
	    	listTrips__trip_headsign.add(newTrips__trip_headsign);
	    	newTrips__trip_headsign.addValue(tripHeadsign);
	    }

	    // v1.7.3: Roll out trip directions
	    for (i = 0; i < _listJourneyPatternRef.size(); i++) {
	    	iterator = _listJourneyPatternRef.get(i);
	    	journeyPatternRef = iterator.getValue(0);
	    	j = 0;
	    	hot = true;
	    	tripDirection = "";
	       	while (hot && j < _listJourneyPatternDirections.size()) { // find associated destination
	        	jterator = _listJourneyPatternDirections.get(j);
	       		if (jterator.getKeyName().equals(journeyPatternRef)) {
	       			tripDirection = jterator.getValue(0);
	       			hot = false;
	       		} else
	       			j++;
	       	}
	       	ValueList newTrips__direction_id = new ValueList(iterator.getKeyName());
	    	listTrips__direction_id.add(newTrips__direction_id);
	    	newTrips__direction_id.addValue(tripDirection);
	    }

	    // v1.7.3: Roll out trip route references
	    for (i = 0; i < _listJourneyPatternRef.size(); i++) {
	    	iterator = _listJourneyPatternRef.get(i);
	    	journeyPatternRef = iterator.getValue(0);
	    	j = 0;
	    	hot = true;
	    	tripRouteRef = "";
	       	while (hot && j < _listJourneyPatternRouteRef.size()) { // find associated destination
	        	jterator = _listJourneyPatternRouteRef.get(j);
	       		if (jterator.getKeyName().equals(journeyPatternRef)) {
	       			tripRouteRef = jterator.getValue(0);
	       			hot = false;
	       		} else
	       			j++;
	       	}
	       	ValueList newTrips__routeref = new ValueList(iterator.getKeyName());
	    	listTrips__routeref.add(newTrips__routeref);
	    	newTrips__routeref.addValue(tripRouteRef);
	    }
   	}

   	@Override
	public void completeData() {
  	    // Add quotes if needed
  	    Util.csvProofList(listTrips__route_id);
  	    Util.csvProofList(listTrips__service_id);
  	    Util.csvProofList(listTrips__trip_id);
  	    Util.csvProofList(listTrips__trip_headsign);
 	    Util.csvProofList(listTrips__direction_id); // v1.7.3
 	    Util.csvProofList(listTrips__routeref); // v1.7.3
  	    Util.csvProofList(listTrips__block_id);
	}

   	@Override
	public void dumpValues() {
		ValueList iterator;

		System.out.println("*** Trips");
		for (int i = 0; i < listTrips__trip_id.size(); i++) {
		    iterator = listTrips__trip_id.get(i);
		    iterator.dumpValues();
		}
		for (int i = 0; i < _listJourneyPatternDestinationDisplays.size(); i++) {
		    iterator = _listJourneyPatternDestinationDisplays.get(i);
		    iterator.dumpValues();
		}
		// v1.7.3
		for (int i = 0; i < _listJourneyPatternDirections.size(); i++) {
		    iterator = _listJourneyPatternDirections.get(i);
		    iterator.dumpValues();
		}
		for (int i = 0; i < _listJourneyPatternRouteRef.size(); i++) {
		    iterator = _listJourneyPatternRouteRef.get(i);
		    iterator.dumpValues();
		}
    for (int i = 0; i < _listJourneyPatternSectionRefs.size(); i++) {
		    iterator = _listJourneyPatternSectionRefs.get(i);
		    iterator.dumpValues();
		}
		for (int i = 0; i < listTrips__route_id.size(); i++) {
		    iterator = listTrips__route_id.get(i);
		    iterator.dumpValues();
		}
		for (int i = 0; i < listTrips__service_id.size(); i++) {
		    iterator = listTrips__service_id.get(i);
		    iterator.dumpValues();
		}
		for (int i = 0; i < _listJourneyPatternRef.size(); i++) {
		    iterator = _listJourneyPatternRef.get(i);
		    iterator.dumpValues();
		}
	}

	public TransxchangeTrips(TransxchangeHandlerEngine owner) {
		super(owner);
		listTrips__route_id = new ArrayList<ValueList>();
		listTrips__service_id = new ArrayList<ValueList>();
		listTrips__trip_id = new ArrayList<ValueList>();
		listTrips__trip_headsign = new ArrayList<ValueList>();
		listTrips__direction_id = new ArrayList<ValueList>(); // v1.7.3
		listTrips__routeref = new ArrayList<ValueList>(); // v1.7.3
		listTrips__block_id = new ArrayList<ValueList>();

		_listJourneyPatternRef = new ArrayList<ValueList>();
		_listJourneyPatternDestinationDisplays = new ArrayList<ValueList>();
		_listJourneyPatternDirections = new ArrayList<ValueList>(); // v1.7.3
		_listJourneyPatternRouteRef = new ArrayList<ValueList>(); // v1.7.3
		_listJourneyPatternSectionRefs = new ArrayList<ValueList>();
	}
}
