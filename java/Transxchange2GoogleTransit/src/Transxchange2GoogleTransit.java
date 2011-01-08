/*
 * Copyright 2007, 2008, 2009, 2010, 2011 GoogleTransitDataFeed
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

import java.io.IOException;
import java.io.UnsupportedEncodingException;

import java.io.BufferedReader;
import java.io.FileReader;

import javax.xml.parsers.ParserConfigurationException;

import org.xml.sax.SAXException;
import org.xml.sax.SAXParseException;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.StringTokenizer;

import transxchange2GoogleTransitHandler.*;

/*
 * Transxchange2GoogleTransit 
 * 	$ transxchange2GoogleTransit <transxchange input filename> <url> <timezone> <default route type> <output-directory> <stopfile>
 * 
 * <default route type>: 0 - Tram, 1 - Subway, 2 - Rail, 3 - Bus, 4 - Ferry, 5 - Cable car, 6 - Gondola, 7 - Funicular
 */
public class Transxchange2GoogleTransit {
	
	static boolean 										useAgencyShortname = false;
	static boolean 										skipEmptyService = false;
	static boolean 										skipOrphanStops = false;
	static HashMap										modeList = null;
	static ArrayList									stopColumns = null;
	static String										stopfilecolumnseparator;
	static int											naptanHelperStopColumn = -1;
	static HashMap										naptanStopnames = null;

	public static void main(String[] args) {

		TransxchangeHandler handler = null;

		System.out.println();
        System.out.println("transxchange2GTFS 1.7.0");
        System.out.println("Please refer to LICENSE file for licensing information");
        if ((args.length != 3 || args.length == 3 && !args[1].toLowerCase().equals("-c")))
        	if (args.length < 5 || args.length > 6) {
	        	System.out.println();
	        	System.out.println("Usage: $ transxchange2GoogleTransit <transxchange input filename> -c <configuration file name>");
	        	System.out.println();
	        	System.out.println("             -- OR --");
	        	System.out.println();
	        	System.out.println("Usage: $ transxchange2GoogleTransit <transxchange input filename> -");
	        	System.out.println("         <url> <timezone> <default route type> <output-directory> [<stopfile>]");
	        	System.out.println();
	        	System.out.println("         <timezone>: Please refer to ");
	        	System.out.println("             http://en.wikipedia.org/wiki/List_of_tz_zones");
	        	System.out.println("         <default route type>:");
	        	System.out.println("             0 - Tram, 1 - Subway, 2 - Rail, 3 - Bus, 4 - Ferry, 5 - Cable car, 6 - Gondola, 7 - Funicular");
	        	System.exit(1);
	        }
    
        // Parse transxchange input file and create initial Google Transit output files
        try {
        	
        	handler = new TransxchangeHandler();

        	// v1.6.4: Read configuration file
        	if (args.length == 3)
        		args = readConfigFile(args[0], args[2]);
        	if (args.length == 6)
        		handler.parse(args[0], args[1], args[2], args[3], "", args[4], args[5], useAgencyShortname, skipEmptyService, skipOrphanStops, modeList, stopColumns, stopfilecolumnseparator, naptanHelperStopColumn, naptanStopnames);
        	else
        		handler.parse(args[0], args[1], args[2], args[3], "", args[4], "", useAgencyShortname, skipEmptyService, skipOrphanStops, modeList, stopColumns, stopfilecolumnseparator, naptanHelperStopColumn, naptanStopnames);
		} catch (ParserConfigurationException e) {
        	System.out.println("transxchange2GTFS ParserConfiguration parse error:");
        	System.out.println(e.getMessage());
        	System.exit(1);			
		}
		catch (SAXException e) {
			System.out.println("transxchange2GTFS SAX parse error:");
			System.out.println(e.getMessage());
			System.out.println(e.getException());
			System.exit(1);						
		}
		catch (UnsupportedEncodingException e) { // v1.5: resource file ukstops.txt incorrect encoding
			System.out.println("transxchange2GTFS NaPTAN stop file:");
			System.out.println(e.getMessage());
			System.exit(1);						
		}
 		catch (IOException e) {
			System.out.println("transxchange2GTFS IO parse error:");
			System.out.println(e.getMessage());
			System.exit(1);						
		}

       // Create final Google Transit output files
        try {
        	handler.writeOutput("", args[4]);
        } catch (IOException e) {
        	System.out.println("transxchange2GTFS write error:");
        	System.out.println(e.getMessage());
        	System.exit(1);
        }
       
    	System.exit(0);
    }
	
	private static String[] readConfigFile(String inputFileName, String configFilename) 
		throws IOException
	
	{
		String[] result = {inputFileName, "", "", "", "", ""};
		useAgencyShortname = false;
		
		BufferedReader in = new BufferedReader(new FileReader(configFilename));
		String line;
		int tokenCount;
		String tagToken = "", configurationValue;
		String txcMode = null;
		while ((line = in.readLine()) != null) {
			tokenCount = 0;
			StringTokenizer st = new StringTokenizer(line, "=");
			while (st.hasMoreTokens() && tokenCount < 2) {
				if (tokenCount == 0)
					tagToken = st.nextToken().trim().toLowerCase();
				else {
					configurationValue = st.nextToken().trim();
					if (tagToken.toLowerCase().equals("url"))
						result[1] = new String(configurationValue);
					if (tagToken.toLowerCase().equals("timezone"))
						result[2] = new String(configurationValue);
					if (tagToken.toLowerCase().equals("default-route-type"))
						result[3] = new String(configurationValue);
					if (tagToken.toLowerCase().equals("output-directory"))
						result[4] = new String(configurationValue);
					if (tagToken.toLowerCase().equals("stopfile")) {
						result[5] = new String(configurationValue);
						if (naptanStopnames == null)
							naptanStopnames = NaPTANHelper.readStopfile(configurationValue);
					}
					if (tagToken.toLowerCase().equals("naptanstopcolumn")) {
						if (stopColumns == null)
							stopColumns = new ArrayList();
						stopColumns.add(configurationValue);
					}
					if (tagToken.toLowerCase().equals("naptanstophelper"))
						if (stopColumns == null)
							naptanHelperStopColumn = 0;
						else
							naptanHelperStopColumn = stopColumns.size();
					
					if (tagToken.toLowerCase().equals("stopfilecolumnseparator"))
						stopfilecolumnseparator = new String(configurationValue);
						
					if (tagToken.toLowerCase().equals("useagencyshortname") && configurationValue != null && configurationValue.trim().toLowerCase().equals("true"))
						useAgencyShortname = true;
					if (tagToken.toLowerCase().equals("skipemptyservice") && configurationValue != null && configurationValue.trim().toLowerCase().equals("true"))
						skipEmptyService = true;
					if (tagToken.toLowerCase().equals("skiporphanstops") && configurationValue != null && configurationValue.trim().toLowerCase().equals("true"))
						skipOrphanStops = true;
					if (txcMode != null)
						if (txcMode.length() > 0 && configurationValue.length() > 0) {
							if (modeList == null)
								modeList = new HashMap();
							modeList.put(txcMode, configurationValue);
						}
						txcMode = null;
					}
					if (tagToken.length() >= 5 && tagToken.substring(0, 5).equals("mode:")) {
						txcMode = tagToken.substring(5, tagToken.length());
				}	
				tokenCount++;
			}
		}
		in.close();
			
		return result;
	}
}
