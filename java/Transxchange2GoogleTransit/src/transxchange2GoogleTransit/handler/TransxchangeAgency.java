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

import java.util.HashMap;
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
	static final String key_agency__agency_id = "Operator"; // GTFS required
	static final String key_agency__agency_lid = "LicensedOperator"; // GTFS required
	static String key_agency__agency_name = "OperatorNameOnLicence"; // GTFS required
	//static final String[] key_agency__agency_url = new String[] {"EmailAddress", "", "OpenRequired"}; // GTFS required
	//static final String[] key_agency__agency_timezone = new String[] {"__transxchange2GTFS_drawDefault", "", ""}; // GTFS required
	//static final String[] key_agency__agency_lang = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	//static final String[] key_agency__agency_phone = new String[] {"__transxchange2GTFS_drawDefault", "", ""};
	//TODO(drt24) It is actually possible to extract a phone number

	// Parsed data
	Map<String,String> agencyIdName;

  String agencyId;

  @Override
  public void startElement(String uri, String name, String qName, Attributes atts)
      throws SAXParseException {

    super.startElement(uri, name, qName, atts);

    // v1.6.4: Switched to use short name in place of name on license
    if (handler.isAgencyShortName()) {
      key_agency__agency_name = "OperatorShortName";
    }

    if (qName.equals(key_agency__agency_id) || qName.equals(key_agency__agency_lid)) {
      int qualifierIx = atts.getIndex("id");
      agencyId = atts.getValue(qualifierIx);
      if (!agencyIdName.containsKey(agencyId)) {
        agencyIdName.put(agencyId, null);
      }
    }
    if (qName.equals(key_agency__agency_name))
      key = key_agency__agency_name;
  }

  @Override
  public void endElement(String uri, String name, String qName) {
    if (niceString == null || niceString.length() == 0) {
      return;
    }
    if (key.equals(key_agency__agency_name)) {

      String agencyOverride = handler.getAgencyOverride();
      if (agencyOverride != null && agencyOverride.length() > 0) {
        agencyIdName.put(agencyId, agencyOverride);
      } else {
        Map<String, String> agencyMap = handler.getAgencyMap();
        if (agencyMap == null || !agencyMap.containsKey(agencyId))
          agencyIdName.put(agencyId, niceString);
        else
          agencyIdName.put(agencyId, agencyMap.get(agencyId));
      }
    }
    // TODO(drt24): actually look for the URL
  }

   	@Override
	public void clearKeys (String qName) {
		if (qName.equals(key_agency__agency_id))
			key = "";
		if (qName.equals(key_agency__agency_name))
			key = "";
	}

  @Override
  public void completeData() {
    // Add quotes if needed
    // TODO(drt24) need to cvsproof #agencyIdName
  }

  @Override
  public void dumpValues() {
    System.out.println("*** Agency");
    for (Map.Entry<String, String> agencyEntry : agencyIdName.entrySet()) {
      System.out.println(agencyEntry.getKey() + ": " + agencyEntry.getValue());
    }
  }

  public TransxchangeAgency(TransxchangeHandlerEngine owner) {
    super(owner);
    agencyIdName = new HashMap<String, String>();
  }

  public void export(Map<String, Agency> agencyMap) {
    for (Map.Entry<String, String> agencyEntry : agencyIdName.entrySet()) {
      if (agencyId != null && agencyId.length() > 0) {
        Agency agency =
            new Agency(agencyEntry.getKey(), agencyEntry.getValue(), handler.getUrl(),
                handler.getTimezone(), handler.getLang(), handler.getPhone());
        agencyMap.put(agencyId, agency);
      }
    }
    // Now clear out all these lists so that we can't use them again and so that garbage collection
    // can happen
    agencyIdName.clear();
  }
}
