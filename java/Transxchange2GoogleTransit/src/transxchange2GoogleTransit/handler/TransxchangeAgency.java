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
import java.util.Map;

import org.xml.sax.Attributes;
import org.xml.sax.SAXParseException;

import transxchange2GoogleTransit.Agency;

/*
 * This class handles the TransXChange xml input file under the aspect of
 * 	agencies
 */
public class TransxchangeAgency extends TransxchangeDataAspect {

	// xml keys and output field fillers
	static final String[] key_agency__agency_id = new String[] {"Operator", "", "OpenRequired"}; // GTFS required
	static final String[] key_agency__agency_lid = new String[] {"LicensedOperator", "", "OpenRequired"}; // GTFS required
	static String[] key_agency__agency_name = new String[] {"OperatorNameOnLicence", "", "OpenRequired"}; // GTFS required
	//static final String[] key_agency__agency_url = new String[] {"EmailAddress", "", "OpenRequired"}; // GTFS required
	//static final String[] key_agency__agency_timezone = new String[] {"__transxchange2GTFS_drawDefault", "", ""}; // GTFS required
	//static final String[] key_agency__agency_lang = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	//static final String[] key_agency__agency_phone = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	//TODO(drt24) It is actually possible to extract a phone number

	// Parsed data
	List<ValueList> listAgency__agency_id;
	List<ValueList> listAgency__agency_name;
	//List<ValueList> listAgency__agency_url;

  String agencyId;

   	@Override
	public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException {

		int qualifierIx;

		super.startElement(uri, name, qName, atts);

		// v1.6.4: Switched to use short name in place of name on license
		if (handler.isAgencyShortName()) {
			key_agency__agency_name = new String[] {"OperatorShortName", "", "OpenRequired"};
		}

		if (qName.equals(key_agency__agency_id[0]) || qName.equals(key_agency__agency_lid[0])) {
        	qualifierIx = atts.getIndex("id");
        	agencyId = atts.getValue(qualifierIx);
        	ValueList newAgency__agency_id = new ValueList(key_agency__agency_id[0]);
        	listAgency__agency_id.add(newAgency__agency_id);
        	newAgency__agency_id.addValue(agencyId);
		}
		if (qName.equals(key_agency__agency_name[0]))
			key = key_agency__agency_name[0];
		//if (qName.equals(key_agency__agency_url[0]))
		//	key = key_agency__agency_url[0];
	}

   	@Override
	public void endElement (String uri, String name, String qName) {
   	  if (niceString == null || niceString.length() == 0){
   	    return;
   	  }
   	  if (key.equals(key_agency__agency_name[0])) {
   	    ValueList newAgency__agency_name = new ValueList(key_agency__agency_name[0]);
   	    listAgency__agency_name.add(newAgency__agency_name);
   	    String agencyOverride = handler.getAgencyOverride();
   	    if (agencyOverride != null && agencyOverride.length() > 0)
   	      newAgency__agency_name.addValue(agencyOverride);
   	    else {
   	      Map<String, String> agencyMap = handler.getAgencyMap();
   	      if (agencyMap == null || !agencyMap.containsKey(agencyId))
   	        newAgency__agency_name.addValue(niceString);
   	      else
   	        newAgency__agency_name.addValue(agencyMap.get(agencyId));
   	    }
   	  }
   	  //TODO(drt24): actually look for the URL
	}

   	@Override
	public void clearKeys (String qName) {
		if (qName.equals(key_agency__agency_id[0]))
			key = "";
		if (qName.equals(key_agency__agency_name[0]))
			key = "";
		//if (qName.equals(key_agency__agency_url[0]))
		//	key = "";
	}

  @Override
  public void completeData() {
    // Add quotes if needed
    csvProofList(listAgency__agency_id);
    csvProofList(listAgency__agency_name);
    //csvProofList(listAgency__agency_url);
  }

   	@Override
	public void dumpValues() {
		int i;
		ValueList iterator = null;

		System.out.println("*** Agency");
		for (i = 0; i < listAgency__agency_id.size(); i++) {
		    iterator = listAgency__agency_id.get(i);
		    iterator.dumpValues();
		}
		for (i = 0; i < listAgency__agency_name.size(); i++) {
		    iterator = listAgency__agency_name.get(i);
		    iterator.dumpValues();
		}
//		for (i = 0; i < listAgency__agency_url.size(); i++) {
//		    iterator = listAgency__agency_url.get(i);
//		    iterator.dumpValues();
//		}
	}

	public TransxchangeAgency(TransxchangeHandlerEngine owner) {
		super(owner);
		listAgency__agency_id = new ArrayList<ValueList>();
		listAgency__agency_name = new ArrayList<ValueList>();
//		listAgency__agency_url = new ArrayList<ValueList>();
  }

  public void export(Map<String, Agency> agencyMap) {
    int size = listAgency__agency_id.size();
    assert listAgency__agency_name.size() == size;
//    assert listAgency__agency_url.size() == size;
    for (int i = 0; i < size; ++i) {
      String agencyId = listAgency__agency_id.get(i).getValue(0);
      // TODO(drt24) verify getKeyName matches agencyId
      if (agencyId != null && agencyId.length() > 0) {
//        String url = listAgency__agency_url.get(i).getValue(0);
        Agency agency =
            new Agency(agencyId, listAgency__agency_name.get(i).getValue(0),
                handler.getUrl(), handler.getTimezone(),
                handler.getLang(), handler.getPhone());
        agencyMap.put(agencyId, agency);
      }
    }
    // Now clear out all these lists so that we can't use them again and so that garbage collection
    // can happen
    listAgency__agency_id.clear();
    listAgency__agency_name.clear();
//    listAgency__agency_url.clear();
  }
}
