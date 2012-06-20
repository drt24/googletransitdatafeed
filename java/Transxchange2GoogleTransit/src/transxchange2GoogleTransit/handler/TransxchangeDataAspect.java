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
import java.io.IOException;

import org.xml.sax.Attributes;
import org.xml.sax.SAXParseException;

/*
 * Abstract superclass to cover transxchange data aspects (subclasses: TransxchangeAgency, TransxchangeStops etc.
 */
public abstract class TransxchangeDataAspect {

	String key = ""; // general key
	String keyNested = ""; // nested key
	String niceString = ""; // parsed string
	boolean activeStartElement = false; // control flag to skip characters outside start/endElement()

	TransxchangeHandlerEngine handler;

	public void startElement(String uri, String name, String qName, Attributes atts)
		throws SAXParseException
	{
		if (handler.getParseError() != null){
		  Exception e = handler.getParseError();
			throw new SAXParseException(e.getMessage(), null, e);
		}
		niceString = "";
	}

	public void endElement (String uri, String name, String qName) {
	}

	public void clearKeys (String qName) {
	}

	public void characters (char ch[], int start, int length) {
		if (key.length() > 0) {
		  StringBuffer buffer = new StringBuffer(niceString);
			for (int i = start; i < start + length; i++) {
				buffer.append(ch[i]);
			}
			niceString = buffer.toString();
		}
	}

	public void endDocument()
		throws IOException {
	}

	public void completeData() {
	}

	public void dumpValues() {
	}

	TransxchangeDataAspect(TransxchangeHandlerEngine owner) {
		handler = owner;
	}
}
