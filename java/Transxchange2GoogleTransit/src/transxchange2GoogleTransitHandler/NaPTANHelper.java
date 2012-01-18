package transxchange2GoogleTransitHandler;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.util.StringTokenizer;
import java.util.HashMap;

public class NaPTANHelper {

	public static HashMap readStopfile(String stopsFileName)
		throws UnsupportedEncodingException, IOException {

		if (!(stopsFileName != null && stopsFileName.length() > 0)) 
			return null;
		   
		HashMap result = new HashMap();
		
	    BufferedReader bufFileIn = new BufferedReader(new FileReader(stopsFileName));
		
	    String line;
	    int smscodeIx;
	    int stopcodeAltIx;
	    int latIx;
	    int lonIx;
	    int commonNameIx;
	    int indicatorIx;
	    int directionIx;
	    int streetIx;
	    int localityIx;
	    int parentLocalityIx;
	    int busStopTypeIx;
	    if ((line = bufFileIn.readLine()) != null) {
	        if ((stopcodeAltIx = findColumn(line, "\"ATCOCode\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column ATCOCode not found");
	        if ((latIx = findColumn(line, "\"Lat\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column Lat not found");
	        if ((lonIx = findColumn(line, "\"Lon\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column Lon not found");
	        if ((commonNameIx = findColumn(line, "\"CommonName\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column CommonName not found");
	        if ((indicatorIx = findColumn(line, "\"Identifier\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column Identifier not found");
	        if ((directionIx = findColumn(line, "\"Direction\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column Direction not found");
	        if ((streetIx = findColumn(line, "\"Street\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column Street not found");
	        if ((localityIx = findColumn(line, "\"NatGazLocality\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column NatGazLocality not found");
	        if ((parentLocalityIx = findColumn(line, "\"ParentLocality\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column ParentLocality not found");
	        if ((busStopTypeIx = findColumn(line, "\"BusStopType\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column BusStopType not found");
	        if ((smscodeIx = findColumn(line, "\"SMSNumber\"")) == -1)
	            throw new UnsupportedEncodingException("stopfile column SMSNumber not found");
	    } else
	        throw new UnsupportedEncodingException("stopfile is empty");

	    String commonName;
	    String atcoCode;
	    String stopcode;
	    String smscode;
	    String stopname;
	    String rawIndicator, indicator;
	    String direction;
	    String street;
	    String locality;
	    String parentLocality;
	    String busStopType;
	    String tokens[] = {"", "", "", "", "", "", "", "", "", "",
	            "", "", "", "", "", "", "", "", "", "",
	            "", "", "", "", "", "", "", "", "", "",
	            "", "", "", "", "", "", "", "", "", "",
	            "", "", "", "", "", "", "", "", "", ""};

	    int i;
	    initializeIndicatorMap();
	    boolean indicatorSet;
	    while((line = bufFileIn.readLine()) != null) {
	    	
	    	try { // v1.7.4
	            StringTokenizer st = new StringTokenizer(line, ",");
	            i = 0;
	            while (st.hasMoreTokens() && i < 30) {
	                tokens[i] = st.nextToken();
	                i++;
	            }
	            
	            // Stop code (for queries to server and display as "stop number"
	            atcoCode = tokens[stopcodeAltIx].substring(1, tokens[stopcodeAltIx].length() - 1);
	            smscode = tokens[smscodeIx].substring(1, tokens[smscodeIx].length() - 1); // Use SMS code as stop code - Remove quotation marks
	            if (smscode == null || smscode.length() == 0)
		            stopcode = atcoCode; // In the absence of SMS code: Go for alternative stop code		            	
	            else
	            	stopcode = smscode;
			            
	            // Read CommonName, locality and the other relevant columns; remove quotation marks as necessary
	            commonName = tokens[commonNameIx].substring(1, tokens[commonNameIx].length() - 1);
	            rawIndicator = tokens[indicatorIx].substring(1, tokens[indicatorIx].length() - 1);
	            direction = tokens[directionIx].substring(1, tokens[directionIx].length() - 1);
	            street = tokens[streetIx].substring(1, tokens[streetIx].length() - 1);
	            locality = tokens[localityIx].substring(1, tokens[localityIx].length() - 1);
	            parentLocality = tokens[parentLocalityIx].substring(1, tokens[parentLocalityIx].length() - 1);
	            busStopType = tokens[busStopTypeIx].substring(1, tokens[busStopTypeIx].length() - 1);
	            
	            // Create NaPTAN stop name following rules
	            stopname = "";
			            
	            // Locality and parent locality
	            if (locality != null && locality.length() > 0 || parentLocality != null && parentLocality.length() > 0) {
		            if (locality != null && locality.length() > 0)
		            	stopname += locality;
		            if (parentLocality != null && parentLocality.length() > 0 && !locality.contains(parentLocality))
		            	stopname += " " + parentLocality;
	            }
			            
	            // Indicator
	            indicatorSet = false;
	            switch (analyzeIndicator(rawIndicator)) {
	            	case INDICATOR_BEFORE:
	            		indicator = getPreferredIndicator(rawIndicator, indicatorsbefore);
	            		stopname += ", " + indicator; // + " " + stopname2;
	            		indicatorSet = true;
	            		break;
	            	default:
	//            		if (rawIndicator.length() > 0 && !rawIndicator.equals("---"))
	//            			stopname += ", " + rawIndicator;
		            	if (rawIndicator.length() <= 2 && rawIndicator.length() > 0)
		            		stopname += ", Stop " + rawIndicator; // Use Stop position code
		            	else
		            		if (!direction.toUpperCase().equals("NA") && direction.length() > 0)
		            			stopname += ", (" + direction + "-bound)"; // No preferred indicator, use direction instead, unless NA"
	            		break;
	            }
		            
	            // CommonName
	            stopname += " " + commonName;
	
	            // After-indicator
	            switch (analyzeIndicator(rawIndicator)) {
	            	case INDICATOR_AFTER:
	            		indicator = getPreferredIndicator(rawIndicator, indicatorsafter);
	            		stopname += " (" + indicator + ")";
	        		break;
	            	default:
		            break;
	            }
		            
	            // on-Street
	            if (street != null && street.length() > 0 && !street.toUpperCase().equals("N/A") && !street.equals("---"))
	            	stopname += " (on " + street + ")";
		            
	            // SMS code
	            if (smscode != null && smscode.length() > 0)
	            	stopname += " [SMS: " + smscode + "]";
		            
	            stopname = stopname.trim();
	            
	            if (busStopType.equals("CUS"))
	            	stopname += " (unmarked)";
	            if (busStopType.equals("HAR"))
	            	stopname += " (Hail-and-Ride)";
	
	            if (!busStopType.equals("FLX")) // Do not include flex service stops
	            	result.put(atcoCode, stopname);
            
	    	} catch (Exception e) { // v1.7.4
	    		System.out.println("Exception: " + e.getMessage());
	    		System.out.println("At line: " + line);
		    }
	    }
	    bufFileIn.close();
	    
        return result;

	}	
	
	public static int findColumn(String headline, String code) {
		if (headline == null || code == null)
	        return -1;
	       
	    StringTokenizer st = new StringTokenizer(headline, ",");
	    String token;
	    int counter = 0;
	    boolean found = false;
        while (!found && st.hasMoreTokens()) {
        	token = st.nextToken();
	        if (token.equals(code))
                found = true;
	        else
	            counter++;
        }
	    if (!found)
	    	return -1;
	    return counter;
	}	
	
	private static String removeBrackets(String inString, String brackIn, String brackOut) {
		if (inString == null || brackIn == null || brackOut == null || inString.length() == 0 || brackIn.length() == 0 || brackOut.length() == 0)
			return null;

		int inIx, outIx;
		int carryOverIx = 0;
		boolean broken = false;
		while (inString.contains(brackIn) && inString.contains(brackOut) && !broken) {
			inIx = inString.indexOf(brackIn);
			outIx = inString.indexOf(brackOut);
			if (outIx > inIx) {
				inString = inString.substring(carryOverIx, inIx);
				carryOverIx = outIx + brackOut.length();
			} else 
				broken = true;
		}
		return inString;
	}
	
	// Preferred indicator values. Key = preferred, value = preferred normalised
	private static String[] indicatorkeysbefore = {"opposite", "outside", "adjacent", "near", "behind", "inside", "by", "in", "at", "on", "just before", "just after", "corner of"};
	private static String[] indicatorvaluesbefore = {"opp", "o/s", "adj", "nr", "behind", "inside", "by", "in", "at", "on", "just before", "just after", "corner of"};
	private static HashMap indicatorsbefore = null;
	private static String[] indicatorkeysafter = {"corner", "cnr", "drt", "Stop", "stance", "stand", "bay", "platform", "entrance", "main entrance", "side entrance", "front entrance", "back entrance", "rear entrance", "north entrance", "east entrance", "south entrance", "west entrance", "north east entrance", "NE entrance", "north west entrance", "NW entrance", "south east entrance", "SE entrance", "south west entrance", "SW entrance", "N entrance", "E entrance", "S entrance", "W entrance", "arrivals", "departures", "Northbound", "N-bound", "Southbound", "S-bound", "Eastbound", "E-bound", "Westbound", "W-bound", "NE-bound", "NW-bound", "SW-bound", "SE-bound", "N bound", "E bound", "S bound", "W bound", "NE bound", "SE bound", "SW bound", "NW bound"};
	private static String[] indicatorvaluesafter = {"corner", "cnr", "drt", "Stop", "stance", "stand", "bay", "platform", "entrance", "main entrance", "side entrance", "front entrance", "back entrance", "rear entrance", "north entrance", "east entrance", "south entrance", "west entrance", "NE entrance", "NE entrance", "NW entrance", "NW entrance", "SE entrance", "SE entrance", "SW entrance", "SW entrance", "N entrance", "E entrance", "S entrance", "W entrance", "arrivals", "departures", "N-bound", "N-bound", "S-bound", "S-bound", "E-bound", "E-bound", "W-bound", "W-bound", "NE-bound", "NW-bound", "SW-bound", "SE-bound", "N-bound", "E-bound", "S-bound", "W-bound", "NE-bound", "SE-bound", "SW-bound", "NW-bound"};
	private static HashMap indicatorsafter = null;
	private static final int INDICATOR_UNKNOWN = 0;
	private static final int INDICATOR_BEFORE = 1;
	private static final int INDICATOR_AFTER = 2;
	private static void initializeIndicatorMap() {
		indicatorsbefore = new HashMap();
		for (int i = 0; i < indicatorkeysbefore.length; i++) {
			indicatorsbefore.put(indicatorkeysbefore[i], indicatorvaluesbefore[i]);
		}
		indicatorsafter = new HashMap();
		for (int i = 0; i < indicatorkeysafter.length; i++) {
			indicatorsbefore.put(indicatorkeysafter[i], indicatorvaluesafter[i]);
		}
	}

	private static String getPreferredIndicator(String in, HashMap indicator) {
		if (in == null || indicator == null)
			return null;
		in = in.toLowerCase();
		if (indicator.containsValue(in)) {
			return in;
		}
		if (indicator.containsKey(in)) {
			return (String)indicator.get(in);
		}
		return "";
	}
	private static int analyzeIndicator(String in) {
		if (in == null || indicatorsbefore == null || indicatorsafter == null)
			return INDICATOR_UNKNOWN;
		in = in.toLowerCase();
		if (indicatorsbefore.containsKey(in) || indicatorsbefore.containsValue(in))
			return INDICATOR_BEFORE;
		if (indicatorsafter.containsKey(in) || indicatorsafter.containsValue(in))
			return INDICATOR_AFTER;
		return INDICATOR_UNKNOWN;
	}
}
