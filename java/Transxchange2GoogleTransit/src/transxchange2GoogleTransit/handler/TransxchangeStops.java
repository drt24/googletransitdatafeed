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
import java.io.FileReader;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.StringTokenizer;

import org.xml.sax.Attributes;
import org.xml.sax.SAXParseException;

import transxchange2GoogleTransit.LatLong;
import transxchange2GoogleTransit.Stop;

/*
 * This class handles the TransXChange xml input file under the aspect of
 * 	stops
 */
public class TransxchangeStops extends TransxchangeDataAspect{

	// xml keys and output field fillers
	static final String[] key_stops__stop_id = new String[] {"StopPoints", "AtcoCode", ""}; // GTFS required
	static final String[] key_stops__stop_id2 = new String[] {"StopPoints", "StopPointRef", ""}; // GTFS required
	static final String[] key_stops__stop_name = new String[] {"StopPoints", "CommonName", ""}; // GTFS required
	static final String[] key_stops__stop_desc = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	static final String[] key_stops__stop_east = new String[] {"StopPoints", "Easting", ""};
	static final String[] key_stops__stop_north = new String[] {"StopPoints", "Northing", ""};
	static final String[] key_stops__stop_lat = new String[] {"StopPoints", "Latitude", ""}; // GTFS required
	static final String[] key_stops__stop_lon = new String[] {"StopPoints", "Longitude", ""}; // GTFS required
	static final String[] key_stops__stop_street = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	static final String[] key_stops__stop_city = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	static final String[] key_stops__stop_region = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	static final String[] key_stops__stop_postcode = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	static final String[] key_stops__stop_country = new String[] {"__transxchange2GTFS_drawDefault", "", ""};

	static final String [] _key_stops__stop_locality = new String[] {"StopPoints", "LocalityName"};
	List<ValueList> _listStops__stop_locality;
	ValueList _newStops__stop_locality;
	static final String [] _key_stops__stop_indicator = new String[] {"StopPoints", "Indicator"};
	List<ValueList> _listStops__stop_indicator;
	ValueList _newStops__stop_indicator;

	static final String[] _key_route_section = {"RouteSection"};
	static final String[] _key_route_link_from = new String [] {"RouteLink", "From", "StopPointRef"};
	static final String[] _key_route_link_to = new String [] {"RouteLink", "To", "StopPointRef"};
	//static final String[] _key_route_link_location_x = new String [] {"RouteLink", "Easting-removed!"}; // v1.7.5. Do not pick up Easting/Northing from route links any longer
	//static final String[] _key_route_link_location_y = new String [] {"RouteLink", "Northing-removed!"}; // v1.7.5
	boolean inRouteSection = false;
	String keyNestedLocation = "";
	String stopPointFrom = "";
	String stopPointTo = "";
	//String stopPointToLat = ""; // Store current lat of stop-to to maintain lat of last stop in route link
	//String stopPointToLon = ""; // same for lon

	static Map<String, String> lat = null;
	static Map<String, String> lon = null;
	static Map<String, Integer> stopIx = null;

	static Map<String, String> stops = null;

	static Map<String, Integer> stopColumnIxs = null;
	static List[] columnValues = {null, null, null, null, null, null, null, null, null, null,
		null, null, null, null, null, null, null, null, null, null,
		null, null, null, null, null, null, null, null, null, null,
		null, null, null, null, null, null, null, null, null, null,
		null, null, null, null, null, null, null, null, null, null};

	static final String[] _key_stops_alternative_descriptor = new String[] {"StopPoints", "AlternativeDescriptors", "CommonName"};

	String keyRef = null;

	// Parsed data
	private Set<String> stopIds;
	private Map<String,String> stopIdName;
	private Map<String,LatLong> stopIdToLatLong;

  public static LatLong getStopPosition(String stopId) {
    String latitude;
    if (lat != null) {
      latitude = lat.get(stopId);
    } else {
      latitude = null;
    }
    String longitude;
    if (lon != null) {
      longitude = lon.get(stopId);
    } else {
      longitude = null;
    }
    return new LatLong(latitude, longitude);
  }

	public static void addStop(String stopId) {
		if (stopId == null || stopId.length() == 0)
			return;
		if (stops == null)
			stops = new HashMap<String, String>();
		stops.put(stopId, "0");
	}
	public static boolean hasStop(String testId) {
		if (stops == null || testId == null || testId.length() == 0)
			return false;
		if (!stops.containsKey(testId))
			return false;
		if (!(stops.get(testId)).equals("1"))
			return false;
		return true;
	}
	public static void flagStop(String stopId) {
		if (stops == null || stopId == null || stopId.length() == 0)
			return;
		stops.put(stopId, "1");
	}
	public static void flagAllStops(String flag) {
		if (stops == null || flag == null)
			return;
		for (String key : stops.keySet()) {
			stops.put(key, flag);
		}
	}
	public static void clearStops() {
	  stops.clear();
	}

   	@Override
	public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException {

		super.startElement(uri, name, qName, atts);
		if (key.equals(key_stops__stop_id[0]))
			if (qName.equals(key_stops__stop_id[1])) {
				keyNested = key_stops__stop_id[1];
			}
		if (key.equals(key_stops__stop_id2[0]))
			if (qName.equals(key_stops__stop_id2[1])) {
				keyNested = key_stops__stop_id2[1];
			}
		if (key.equals(key_stops__stop_name[0]) && keyNested.length() == 0)
			if (qName.equals(key_stops__stop_name[1])) {
				keyNested = key_stops__stop_name[1];
			}
		if (key.equals(key_stops__stop_east[0]))
			if (qName.equals(key_stops__stop_east[1])) {
				keyNested = key_stops__stop_east[1];
			}
		if (key.equals(key_stops__stop_north[0]))
			if (qName.equals(key_stops__stop_north[1])) {
				keyNested = key_stops__stop_north[1];
			}

	    // Embedded coordinates
		if (key.equals(key_stops__stop_lat[0]))
			if (qName.equals(key_stops__stop_lat[1])) {
				keyNested = key_stops__stop_lat[1];
			}
		if (key.equals(key_stops__stop_lon[0]))
			if (qName.equals(key_stops__stop_lon[1])) {
				keyNested = key_stops__stop_lon[1];
			}

		if (qName.equals(key_stops__stop_id[0]))
			key = key_stops__stop_id[0];
		if (key.equals(_key_stops__stop_locality[0]) && qName.equals(_key_stops__stop_locality[1])) {
			keyNested = _key_stops__stop_locality[1];
		}
		if (key.equals(_key_stops__stop_indicator[0]) && qName.equals(_key_stops__stop_indicator[1])) {
			keyNested = _key_stops__stop_indicator[1];
		}

		// Route sections (to helper structures)
		// From and to stop points
		if (qName.equals(_key_route_section[0]))
			inRouteSection = !inRouteSection;
		if (key.equals(_key_route_link_from[0]) && (keyNested.equals(_key_route_link_from[1]) || keyNested.equals(_key_route_link_to[1])) && qName.equals(_key_route_link_from[2])) {
			keyNestedLocation = _key_route_link_from[2];
		}
		if (key.equals(_key_route_link_to[0]) && qName.equals(_key_route_link_to[1])) {
			keyNested = _key_route_link_to[1];
		}
		if (key.equals(_key_route_link_from[0]) && qName.equals(_key_route_link_from[1])) {
			keyNested = _key_route_link_from[1];
		}
//		if (key.equals(_key_route_link_location_x[0]) && qName.equals(_key_route_link_location_x[1])) {
//			keyNested = _key_route_link_location_x[1];
//		}
//		if (key.equals(_key_route_link_location_y[0]) && qName.equals(_key_route_link_location_y[1])) {
//			keyNested = _key_route_link_location_y[1];
//		}
		if (qName.equals(_key_route_link_from[0])) 	// this also covers route_link_location_x and _y
			key = _key_route_link_from[0];

		//  Alternative description
		if (key.equals(_key_stops_alternative_descriptor[0]) && qName.equals(_key_stops_alternative_descriptor[1]))
			keyNested = _key_stops_alternative_descriptor[1];
	}

  @Override
  public void endElement(String uri, String name, String qName) {

    if (niceString == null || niceString.length() == 0)
      return;

    if (key.equals(key_stops__stop_id[0]) && keyNested.equals(key_stops__stop_id[1])) {
      stopIds.add(niceString);
      keyRef = niceString;
      return;
    }
    if (key.equals(key_stops__stop_id2[0]) && keyNested.equals(key_stops__stop_id2[1])) {
      stopIds.add(niceString);
      keyRef = niceString;
      return;
    }
    if (key.equals(key_stops__stop_name[0]) && keyNested.equals(key_stops__stop_name[1])) {
      assert keyRef != null;
      stopIdName.put(keyRef, niceString);
      return;
    }
    if (key.equals(_key_stops__stop_locality[0]) && keyNested.equals(_key_stops__stop_locality[1])) {
      assert keyRef != null;
      _newStops__stop_locality = new ValueList(keyRef);
      _listStops__stop_locality.add(_newStops__stop_locality);
      _newStops__stop_locality.addValue(niceString);
      return;
    }
    if (key.equals(_key_stops__stop_indicator[0])
        && keyNested.equals(_key_stops__stop_indicator[1])) {
      assert keyRef != null;
      _newStops__stop_indicator = new ValueList(keyRef);
      _listStops__stop_indicator.add(_newStops__stop_indicator);
      _newStops__stop_indicator.addValue(niceString);
      return;
    }
    // TODO(drt24) We could try extracting latitude and longitude by conversion of easting and
    // northing

    // Embedded coordinates
    if (key.equals(key_stops__stop_lat[0]) && keyNested.equals(key_stops__stop_lat[1])) {
      assert keyRef != null;
      LatLong ll = stopIdToLatLong.get(keyRef);
      if (ll != null) {
        ll = new LatLong(niceString, ll.longitude);
      } else {
        ll = new LatLong(niceString, null);
      }
      stopIdToLatLong.put(keyRef, ll);
      return;
    }
    if (key.equals(key_stops__stop_lon[0]) && keyNested.equals(key_stops__stop_lon[1])) {
      assert keyRef != null;
      LatLong ll = stopIdToLatLong.get(keyRef);
      if (ll != null) {
        ll = new LatLong(ll.latitude, niceString);
      } else {
        ll = new LatLong(null, niceString);
      }
      stopIdToLatLong.put(keyRef, ll);
      return;
    }

    // Route sections (to stop point lat and lon), based on from- and to-stop points
    if (key.equals(_key_route_link_from[0]) && keyNested.equals(_key_route_link_from[1])
        && keyNestedLocation.equals(_key_route_link_from[2])) {
      stopPointFrom = niceString;
      keyNestedLocation = "";
      return;
    }
    if (key.equals(_key_route_link_to[0]) && keyNested.equals(_key_route_link_to[1])
        && keyNestedLocation.equals(_key_route_link_to[2])) {
      stopPointTo = niceString;
      keyNestedLocation = "";
      keyNested = "";
      return;
    }
    if (key_stops__stop_id[0].equals(qName)) {
      keyRef = null;
    }
  }

   	@Override
   	public void clearKeys (String qName) {
    	if (inRouteSection) {
//    		if (keyNested.equals(_key_route_link_location_x[1]))
//    			keyNestedLocation = "";
    		if (keyNestedLocation.equals(_key_route_link_from[2]))
    			keyNestedLocation = "";
    		if (keyNested.equals(_key_route_link_from[1]))
    			keyNested = "";
//    		if (qName.equals(_key_route_link_location_y[1]))
//    			keyNested = "";
    	}
    	if (qName.equals(_key_route_section[0])) {
//    		if (inRouteSection) {
//    			if (stopPointToLat.length() > 0) {
//    			  ValueList newStops__stop_lat = new ValueList(stopPointTo); // last stop in route section
//    				listStops__stop_lat.add(newStops__stop_lat);
//    				newStops__stop_lat.addValue(stopPointToLat);
//    			}
//    			if (stopPointToLon.length() > 0) {
//    			  ValueList newStops__stop_lon = new ValueList(stopPointTo); // last stop in route section
//    				listStops__stop_lon.add(newStops__stop_lon);
//    				newStops__stop_lon.addValue(stopPointToLon);
//    			}
//    		}
    		inRouteSection = !inRouteSection;
    		key = "";
    	}
    	if (key.equals(key_stops__stop_id[0]))
    		keyNested = "";
    	if (qName.equals(key_stops__stop_id[0]))
    		key = "";
    	if (key.equals(key_stops__stop_id[0]))
    		keyNested = "";
    	if (key.equals(key_stops__stop_east[0]))
    		keyNested = "";
    	if (key.equals(key_stops__stop_north[0]))
    		keyNested = "";

	    // Embedded coordinates
    	if (key.equals(key_stops__stop_lat[0]))
    		keyNested = "";
    	if (key.equals(key_stops__stop_lon[0]))
    		keyNested = "";
   	}

   	@Override
	public void endDocument() {
	    ValueList jterator;
	    String indicator, locality, naptanPick;

	    // Roll stop locality and indicator into stopname
    	List<String> stopColumns = handler.getStopColumns();
    	if (stopColumns == null)
    		if (handler.getNaptanHelperStopColumn() == -1)
			    for (Map.Entry<String, String> idName : stopIdName.entrySet()) {
			    	indicator = "";
			    	locality = "";
			    	String stopName = idName.getValue();
			    	String stopId = idName.getKey();
			    	int j = 0; // Find locality
			    	jterator = null;
			    	while (j < _listStops__stop_locality.size()) {
			    		jterator = _listStops__stop_locality.get(j);
			    		if (jterator.getKeyName().equals(stopId)){
			    		  locality = jterator.getValue(0);
			    			break;
			    		} else
			    			j++;
			    	}
			    		
			    	j = 0; // Find indicator
			    	jterator = null;
			    	while (j < _listStops__stop_indicator.size()) {
			    		jterator = _listStops__stop_indicator.get(j);
			    		if (jterator.getKeyName().equals(stopId)){
			    		  indicator = jterator.getValue(0);
			    			break;
			    		} else
			    			j++;
			    	}			    		

			    	if (locality.length() > 0 && stopName != null) // Prefix locality
			    		stopName = locality + ", " + stopName;
			    	if (indicator.length() > 0 && stopName != null) // Postfix indicator
			        	stopName = stopName + ", "+ indicator;
			    	stopIdName.put(stopId,stopName);
			    }
    		else
			    for (String stopId : stopIdName.keySet()) {
			    	stopIdName.put(stopId, handler.getNaPTANStopName(stopId));
			    }
    	else
		    for (Map.Entry<String, String> idName : stopIdName.entrySet()) {
//		    	iterator = listStops__stop_id.get(i);
//		    	stopId = iterator.getValue(0);
		      String stopId = idName.getKey();
		    	String stopName = "";
		    	for (int j = 0; j < 30; j++) {
		    		if (columnValues[j] != null) {
		    			if (stopName.length() > 0)
		    				stopName += handler.getStopfilecolumnseparator(); // ",";
		    			Integer index = (Integer)stopIx.get(stopId);
		    			if (index != null) {
		    				naptanPick = (String) columnValues[j].get((Integer)stopIx.get(stopId));
		    				naptanPick = naptanPick.replaceAll("\"", "");
		    				stopName += naptanPick;
			    		}
		    		}
		    	}
		    	stopIdName.put(stopId, stopName);
		    }
	}

   	@Override
	public void dumpValues() {
	    System.out.println("*** Stops");
	    for (Map.Entry<String, String> idName : stopIdName.entrySet()){
	      System.out.println(idName.getKey() + ": " + idName.getValue());
	    }
	    for (Map.Entry<String, LatLong> entry : stopIdToLatLong.entrySet()){
	      System.out.println(entry.getKey() + ": " + entry.getValue());
	    }
	}

	public TransxchangeStops(TransxchangeHandlerEngine owner) {
		super(owner);
		stopIds = new HashSet<String>();
		stopIdName = new HashMap<String,String>();
		stopIdToLatLong = new HashMap<String,LatLong>();

		_listStops__stop_locality = new ArrayList<ValueList>();
		_listStops__stop_indicator = new ArrayList<ValueList>();
	}


	public static void readStopfile(String stopsFileName, List<String> stopColumns)
		throws UnsupportedEncodingException, IOException {

		// Read Naptan format stop file
		if (!(stopsFileName != null && stopsFileName.length() > 0))
			return;

		BufferedReader bufFileIn = new BufferedReader(new FileReader(stopsFileName));

		// Read first line to find column positions of stopcode, lat and lon
		String line;
		int stopcodeIx;
		int latIx;
		int lonIx;
		if ((line = bufFileIn.readLine()) != null) {
			if ((stopcodeIx = NaPTANHelper.findColumn(line, "\"AtcoCode\"")) == -1)
				throw new IOException("stopfile column AtcoCode not found");
			if ((latIx = NaPTANHelper.findColumn(line, "\"Latitude\"")) == -1)
				throw new IOException("stopfile column Latitude not found");
			if ((lonIx = NaPTANHelper.findColumn(line, "\"Longitude\"")) == -1)
				throw new IOException("stopfile column Longitude not found");
		} else
			throw new IOException("stopfile is empty");

		if (lat != null)
			lat.clear();
		if (lon != null)
			lon.clear();
		lat = new HashMap<String, String>();
		lon = new HashMap<String, String>();
		stopIx = new HashMap<String, Integer>();
		String stopcode;
		String tokens[] = {"", "", "", "", "", "", "", "", "", "",
				"", "", "", "", "", "", "", "", "", "",
				"", "", "", "", "", "", "", "", "", "",
				"", "", "", "", "", "", "", "", "", "",
				"", "", "", "", "", "", "", "", "", ""};
		int i, j;
		int lineCounter = 0;
		while((line = bufFileIn.readLine()) != null) {
			StringTokenizer st = new StringTokenizer(line, ",");
			i = 0;
			while (st.hasMoreTokens() && i < 30) {
				tokens[i] = st.nextToken();
				i++;
			}
			stopcode = tokens[stopcodeIx].substring(1, tokens[stopcodeIx].length() - 1); // Remove quotation marks
			lat.put(stopcode, tokens[latIx]);
			lon.put(stopcode, tokens[lonIx]);
			stopIx.put(stopcode, (Integer)lineCounter);
			lineCounter++;
		}
		bufFileIn.close();

		// Read columns
		if (stopColumns != null && stopColumns.size() > 0) {
			bufFileIn = new BufferedReader(new FileReader(stopsFileName));
			if ((line = bufFileIn.readLine()) != null) {
				Iterator<String> iterator = stopColumns.iterator();
				String column;
				stopColumnIxs = new HashMap<String, Integer>();
				while (iterator.hasNext()) {
					column = iterator.next();
					stopColumnIxs.put(column, (Integer)NaPTANHelper.findColumn(line, column));
				}
			} else
				throw new IOException("stopfile is empty");
			while((line = bufFileIn.readLine()) != null) {
				Iterator<String> iterator = stopColumns.iterator();
				i = 0;
				String column;
				while(iterator.hasNext() && i < 30) {
					column = iterator.next();
					StringTokenizer st = new StringTokenizer(line, ",");
					String token;
					j = 0;
					while (st.hasMoreTokens()) {
						token = st.nextToken();
						if ((Integer)stopColumnIxs.get(column) == j) {
							if (columnValues[i] == null)
								columnValues[i] = new ArrayList<String>();
							columnValues[i].add(token);
						}
						j++;
					}
					i++;
				}
			}
			bufFileIn.close();
		}
  }

  public void export(Map<String, Stop> stopsMap) {

    for (String stopId : stopIds) {
      if (stopId != null && stopId.length() > 0) {
        LatLong ll = stopIdToLatLong.get(stopId);
        if (ll == null) {
          ll = new LatLong(null, null);// the not set location
        }
        Stop stop = new Stop(stopId, stopIdName.get(stopId), ll);
        stopsMap.put(stopId, stop);
      }
    }
    // Now clear out all these lists so that we can't use them again and so that garbage collection
    // can happen
    stopIds.clear();
    stopIdName.clear();
    stopIdToLatLong.clear();
  }
}
