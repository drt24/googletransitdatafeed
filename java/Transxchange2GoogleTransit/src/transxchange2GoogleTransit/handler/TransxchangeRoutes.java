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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.xml.sax.Attributes;
import org.xml.sax.SAXParseException;

import transxchange2GoogleTransit.Route;

/*
 * This class handles the TransXChange xml input file under the aspect of
 * 	routes
 */
public class TransxchangeRoutes extends TransxchangeDataAspect {

	// xml keys and output field fillers
	static final String[] key_route__description = new String[] {"Route", "Description"}; // v1.7.3: Read id of <Route> and <Route> <Description>
	static final String[] key_routes__route_id = new String[] {"Service", "Line", "OpenRequired"}; // GTFS required
	static final String[] key_routes__agency_id = new String[] {"Service", "RegisteredOperatorRef", ""};
	static final String[] key_routes__route_short_name = new String[] {"Service", "LineName", "OpenRequired"}; // GTFS required
	static final String[] key_routes__route_long_name = new String[] {"__transxchange2GTFS_drawDefault", "", "OpenRequired"}; // GTFS required
	static final String[] key_routes__route_desc = new String[] {"Service", "Description", ""};
	static final String[] key_routes__route_origin = new String[] {"Service", "Origin", ""};
	static final String[] key_routes__route_destination = new String[] {"Service", "Destination", ""};
	static final String[] key_routes__route_type = new String[] {"__transxchange2GTFS_drawDefault", "", "3"}; // GTFS required
	static final String[] key_routes__route_mode = new String[] {"Service", "Mode"};

	// Parsed data
	Map<String, String> listRoutes; // v1.7.3
	List<ValueList> listRoutes__route_id;
	List<ValueList> listRoutes__agency_id;
	List<ValueList> listRoutes__route_short_name;
	List<ValueList> listRoutes__route_long_name;
	List<ValueList> listRoutes__route_desc;
	Map<String, String> listRoutes__route_dest;
	Map<String, String> listRoutes__route_origin;
	List<ValueList> listRoutes__route_type;
	List<ValueList> listRoutes__service_id;
	ValueList newRoutes__route_type;

	String _origin = "";
	String _agencyId = "";
	List<ValueList> _listRouteDesc;

	String routeId = ""; // v1.7.3
	String currentRouteId;

	public String getHeadsign(String routeId, boolean inbound) { // v1.7.3: Added inbound flag
		if (inbound) { // v1.7.3: Reverse Origin/Destination inbound
			if (routeId == null || listRoutes__route_origin == null || !listRoutes__route_origin.containsKey(routeId))
				return "";
			return listRoutes__route_origin.get(routeId);
		} else {
			if (routeId == null || listRoutes__route_dest == null || !listRoutes__route_dest.containsKey(routeId))
				return "";
			return listRoutes__route_dest.get(routeId);
		}
	}

	public List<ValueList> getListRoutes__route_type() {
		return listRoutes__route_type;
	}

	// v1.7.3
	String getRouteDescription(String routeId) {
		if (routeId == null || !listRoutes.containsKey(routeId))
			return "";
		return listRoutes.get(routeId).trim();
	}

   	@Override
	public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException {

	    int qualifierIx;
	    String qualifierString;

	    super.startElement(uri, name, qName, atts);

	    // v1.7.3
		if (qName.equals(key_route__description[0])) {
			routeId = atts.getValue("id");
			key = key_route__description[0];
		}
		if (key.equals(key_route__description[0]) && qName.equals(key_route__description[1]))
			keyNested = key_route__description[1];

	    if (key.equals(key_routes__route_id[0]) && qName.equals(key_routes__route_id[1])) {
	        qualifierIx = atts.getIndex("id");
	        qualifierString = atts.getValue(qualifierIx);
	        ValueList newRoutes__route_id = new ValueList(qualifierString);
	        listRoutes__route_id.add(newRoutes__route_id);
	    	newRoutes__route_id.addValue(qualifierString);
			currentRouteId = qualifierString;
	    }
		if (qName.equals(key_routes__agency_id[0]))
			key = key_routes__agency_id[0];
		if (key.equals(key_routes__agency_id[0]) && qName.equals(key_routes__agency_id[1]))
			keyNested = key_routes__agency_id[1];
		if (qName.equals(key_routes__route_short_name[0]))
			key = key_routes__route_short_name[0];
		if (key.equals(key_routes__route_short_name[0]) && qName.equals(key_routes__route_short_name[1]))
			keyNested = key_routes__route_short_name[1];
		if (qName.equals(key_routes__route_desc[0]))
			key = key_routes__route_desc[0];
		if (key.equals(key_routes__route_desc[0]) && qName.equals(key_routes__route_desc[1]))
			keyNested = key_routes__route_desc[1];
		if (qName.equals(key_routes__route_origin[0]))
			key = key_routes__route_origin[0];
		if (key.equals(key_routes__route_origin[0]) && qName.equals(key_routes__route_origin[1]))
			keyNested = key_routes__route_origin[1];
		if (qName.equals(key_routes__route_destination[0]))
			key = key_routes__route_destination[0];
		if (key.equals(key_routes__route_destination[0]) && qName.equals(key_routes__route_destination[1]))
			keyNested = key_routes__route_destination[1];
		if (key.equals(key_routes__route_mode[0]) && qName.equals(key_routes__route_mode[1]))
			keyNested = key_routes__route_mode[1];
	}

   	@Override
	public void endElement (String uri, String name, String qName) {
		if (niceString == null || niceString.length() == 0){
			return;
		}

		// v1.7.3
		if (key.equals(key_route__description[0]) && keyNested.equals(key_route__description[1])) {
			listRoutes.put(routeId, niceString);
        	key = "";
        	keyNested = "";
		}

		if (key.equals(key_routes__route_short_name[0]) && keyNested.equals(key_routes__route_short_name[1])) {
		  String routeName = niceString;
		  boolean isShortName = routeName.length() <= 6;
		  // We only get one length of name, if it is short we use it as a short name otherwise as a long name
		  ValueList newRoutes__route_short_name = new ValueList(key_routes__route_short_name[1]);
		  listRoutes__route_short_name.add(newRoutes__route_short_name);
		  newRoutes__route_short_name.addValue((isShortName) ? routeName :"");
		  ValueList newRoutes__route_long_name = new ValueList(key_routes__route_long_name[1]);
		  listRoutes__route_long_name.add(newRoutes__route_long_name);
		  newRoutes__route_long_name.addValue((!isShortName) ? routeName :"");
		  keyNested = "";
			newRoutes__route_type = new ValueList(key_routes__route_type[0]); // Default for _type
			listRoutes__route_type.add(newRoutes__route_type);
			newRoutes__route_type.addValue(handler.getDefaultRouteType());
			ValueList newRoutes__service_id = new ValueList(niceString);
			listRoutes__service_id.add(newRoutes__service_id);
        	newRoutes__service_id.addValue(((TransxchangeCalendar)handler.getCalendar()).getService());
		}
		if (key.equals(key_routes__agency_id[0]) && keyNested.equals(key_routes__agency_id[1])) {
			_agencyId = niceString;
		}
		if (key.equals(key_routes__route_origin[0]) && keyNested.equals(key_routes__route_origin[1])) {
			_origin = niceString;
		}
		if (key.equals(key_routes__route_destination[0]) && keyNested.equals(key_routes__route_destination[1])) {
			listRoutes__route_dest.put(currentRouteId, niceString);
			keyNested = "";
		}
		if (key.equals(key_routes__route_origin[0]) && keyNested.equals(key_routes__route_origin[1])) {
			listRoutes__route_origin.put(currentRouteId, niceString);
			keyNested = "";
		}
		if (key.equals(key_routes__route_desc[0]) && keyNested.equals(key_routes__route_desc[1])) {
			ValueList _newRouteDesc = new ValueList(currentRouteId);
			_listRouteDesc.add(_newRouteDesc);
			_newRouteDesc.addValue(niceString);
        	keyNested = "";
		}

		Map<String,String> modeList = handler.getModeList();
		if (key.equals(key_routes__route_mode[0]) && keyNested.equals(key_routes__route_mode[1])) {
			if (modeList != null) {
				if (!(newRoutes__route_type != null && newRoutes__route_type.size() > 0)) {
					newRoutes__route_type = new ValueList(key_routes__route_type[0]); // Default for _type
					listRoutes__route_type.add(newRoutes__route_type);
					newRoutes__route_type.addValue(handler.getDefaultRouteType());
				}
				newRoutes__route_type.setValue(0, modeList.get(niceString));
				newRoutes__route_type = null;
			}
		}
	}

   	@Override
	public void clearKeys (String qName) {
		if (key.equals(key_routes__agency_id[0]) && keyNested.equals(key_routes__agency_id[1])) {
			ValueList iterator;

			// Backfill agency id to route short names
			for (int i = 0; i < listRoutes__service_id.size(); i++) {
			    iterator = listRoutes__service_id.get(i);
			    if (iterator.getValue(0).equals(((TransxchangeCalendar)handler.getCalendar()).getService())) {
			    	ValueList newRoutes__agency_id = new ValueList(key_routes__agency_id[1]);
			    	listRoutes__agency_id.add(newRoutes__agency_id);
			    	newRoutes__agency_id.addValue(_agencyId);
			    }
			}
			keyNested = "";
		}
		if (key.equals(key_routes__route_short_name[0]))
			keyNested = "";
		if (qName.equals(key_routes__route_short_name[0]))
			key = "";
		if (key.equals(key_routes__route_desc[0]))
			keyNested = "";
		if (qName.equals(key_routes__route_desc[0]))
			key = "";
		if (key.equals(key_routes__route_origin[1]))
			keyNested = "";
		if (qName.equals(key_routes__route_origin[0]))
			key = "";
		if (key.equals(key_routes__route_destination[1])) {
			keyNested = "";
			_origin = "";
		}
		if (qName.equals(key_routes__route_destination[0]))
			key = "";
	}

   	@Override
	public void endDocument() {
		int i, j;
		boolean hot;

		// Route descriptions
		for (i = 0; i < listRoutes__route_id.size(); i++) {
			j = 0;
			hot = true;
			while (hot && j < _listRouteDesc.size()) {
				if (((listRoutes__route_id.get(i)).getKeyName()).equals(((_listRouteDesc.get(j)).getKeyName())))
					hot = false;
				else
					j++;
			}
			if (!hot) {
				ValueList newRoutes__route_desc = new ValueList((_listRouteDesc.get(j)).getKeyName());
				listRoutes__route_desc.add(newRoutes__route_desc);
				newRoutes__route_desc.addValue(((_listRouteDesc.get(j)).getValue(0)));
			} else {
				ValueList newRoutes__route_desc = new ValueList(key_routes__route_desc[2]);
				listRoutes__route_desc.add(newRoutes__route_desc);
				newRoutes__route_desc.addValue(key_routes__route_desc[2]);
	    	}
    	}
    }

   	@Override
	public void completeData() {
  	    // Add quotes if needed
  	    csvProofList(listRoutes__route_id);
  	    csvProofList(listRoutes__route_short_name);
  	    csvProofList(listRoutes__route_long_name);
  	    csvProofList(listRoutes__route_desc);
//  	    csvProofList(listRoutes__route_dest);
//	    	csvProofList(listRoutes__route_origin);
  	    csvProofList(listRoutes__route_type);
	}

   	@Override
	public void dumpValues() {
		int i;
		ValueList iterator;

		System.out.println("*** Routes");
		for (i = 0; i < listRoutes__route_id.size(); i++) {
		    iterator = listRoutes__route_id.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listRoutes__agency_id.size(); i++) {
		    iterator = listRoutes__agency_id.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listRoutes__route_short_name.size(); i++) {
		    iterator = listRoutes__route_short_name.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listRoutes__route_long_name.size(); i++) {
		    iterator = listRoutes__route_long_name.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listRoutes__route_desc.size(); i++) {
		    iterator = listRoutes__route_desc.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listRoutes__route_dest.size(); i++) {
		    System.out.println(listRoutes__route_dest.get(i));
		}
		for (i = 0; i < listRoutes__route_origin.size(); i++) {
		    System.out.println(listRoutes__route_origin.get(i));
		}
	}

	public TransxchangeRoutes(TransxchangeHandlerEngine owner) {
		super(owner);
		listRoutes = new HashMap<String, String>();
		listRoutes__route_id = new ArrayList<ValueList>();
		listRoutes__agency_id = new ArrayList<ValueList>();
		listRoutes__route_short_name = new ArrayList<ValueList>();
		listRoutes__route_long_name = new ArrayList<ValueList>();
		listRoutes__route_desc = new ArrayList<ValueList>();
		listRoutes__route_dest = new HashMap<String, String>();
		listRoutes__route_origin = new HashMap<String, String>();
		listRoutes__route_type = new ArrayList<ValueList>();
		listRoutes__service_id = new ArrayList<ValueList>();

		_listRouteDesc = new ArrayList<ValueList>();
  }

  public void export(Map<String, Route> routeMap) {
    int size = listRoutes__route_id.size();
    assert listRoutes__agency_id.size() == size;
    assert listRoutes__route_short_name.size() == size;
    assert listRoutes__route_long_name.size() == size;
    assert listRoutes__route_desc.size() == size;
    assert listRoutes__route_type.size() == size;
    assert listRoutes__service_id.size() == size;
    for (int i = 0; i < size; ++i) {
      String routeId = listRoutes__route_id.get(i).getValue(0);
      if (routeId != null && routeId.length() > 0) {
        // TODO(drt24) verify getKeyName matches stopId
        Route route =
            new Route(routeId, listRoutes__agency_id.get(i).getValue(0),
                listRoutes__route_short_name.get(i).getValue(0), listRoutes__route_long_name.get(i)
                    .getValue(0), listRoutes__route_desc.get(i).getValue(0), listRoutes__route_dest
                    .get(routeId), listRoutes__route_origin.get(routeId), listRoutes__route_type
                    .get(i).getValue(0), listRoutes__service_id.get(i).getValue(0));
        routeMap.put(routeId, route);
      }
    }
    // Now clear out all these lists so that we can't use them again and so that garbage collection
    // can happen
    listRoutes.clear();
    listRoutes__route_id.clear();
    listRoutes__agency_id.clear();
    listRoutes__route_short_name.clear();
    listRoutes__route_long_name.clear();
    listRoutes__route_desc.clear();
    listRoutes__route_dest.clear();
    listRoutes__route_origin.clear();
    listRoutes__route_type.clear();
    listRoutes__service_id.clear();
    // TODO Auto-generated method stub

  }
}
