package transxchange2GoogleTransit;

import java.util.List;
import java.util.StringTokenizer;

import transxchange2GoogleTransit.handler.ValueList;

/**
 * Utility methods for reading transxchange files and writing csvs
 * 
 */
public final class Util {
  private Util() {
  }

  /*
   * Read time in transxchange specific format
   */
  public static void readTransxchangeTime(int[] timehhmmss, String inString) {
  	StringTokenizer st = new StringTokenizer(inString, ":");
  	int i = 0;
  	while (st.hasMoreTokens() && i < 3) {
  		timehhmmss[i] = Integer.parseInt(st.nextToken());
  		i++;
  	}
  }

  /**
   * Read frequency in transxchange specific format
   */
  public static int readTransxchangeFrequency(String inString) {
  	int freq = 0;
  
  	inString = inString.substring(2, inString.length()); // Skip "PT"
  	if (inString.indexOf('H') > 0) { // Hours
  		StringTokenizer st = new StringTokenizer(inString, "H");
  		int i = 0;
  		while (st.hasMoreTokens() && i < 1) {
  			freq = Integer.parseInt(st.nextToken()) * 60 * 60;
  			i++;
  		}
  		inString = inString.substring(inString.indexOf('H') + 1, inString.length());
  	}
  	if (inString.indexOf('M') > 0) { // Minutes
  		StringTokenizer st = new StringTokenizer(inString, "M");
  		int i = 0;
  		while (st.hasMoreTokens() && i < 1) {
  			freq += Integer.parseInt(st.nextToken()) * 60;
  			i++;
  		}
  		inString = inString.substring(inString.indexOf('M') + 1, inString.length());
  	}
  	if (inString.indexOf('S') > 0) { // Seconds
  		StringTokenizer st = new StringTokenizer(inString, "S");
  		int i = 0;
  		while (st.hasMoreTokens() && i < 1) {
  			freq += Integer.parseInt(st.nextToken());
  			i++;
  		}
  	}
  	return freq;
  }

  /*
   * Read date in transxchange specific format
   */
  public static String readTransxchangeDate(String inString) {
  	StringTokenizer st = new StringTokenizer(inString, "-");
  	String ret = "";
  	int i = 0;
  	while (st.hasMoreTokens() && i < 3) {
  		ret = ret + st.nextToken();
  		++i;
  	}
  	return ret;
  }

  /**
   * CSV-"proof" field
   */
  public static void csvProofList(List<ValueList> values) {
    int i, j;
    ValueList iterator;
  
    for (i = 0; i < values.size(); i++) {
      iterator = values.get(i);
      for (j = 0; j < iterator.size(); j++) {
        iterator.setValue(j, Util.csvProof(iterator.getValue(j)));
      }
    }
  }

  /**
   * Correctly escape a string so that it can be inserted into a CSV file
   * @param string
   * @return
   */
  public static String csvProof(String string) {
    if (string != null) { // v1.6.3: may contain null value
      if (string.lastIndexOf(",") != -1) // || s.lastIndexOf("\"") != -1) // v1.7.2: Remove addition of \" here, leads to duplication if \" used in configuration file
        string = "\"" + string + "\"";
    } else {
      string = "";// set to empty string when null
    }
    return string;
  }

  /**
   * Return date in GTFS format
   * introduced to support Java 1.4.2
   */
  public static String formatDate(int year, int month, int day_of_month) {
  
  	String result = Integer.toString(year);
  
  	String digis = Integer.toString(month);
  	if (digis.length() == 1)
  		digis = "0" + digis;
  	result = result + digis;
  
  	digis = Integer.toString(day_of_month);
  	if (digis.length() == 1)
  		digis = "0" + digis;
  	result = result + digis;
  
  	return result;
  }

  /**
   * Return time in GTFS format
   * introduced to support Java 1.4.2
   */
  public static String formatTime(int hour, int mins) {
  	String result = "";
  
  	String digis = Integer.toString(hour);
  	if (digis.length() == 1)
  		digis = "0" + digis;
  	result = result + digis;
  
  	result = result + ":";
  
  	digis = Integer.toString(mins);
  	if (digis.length() == 1)
  		digis = "0" + digis;
  	result = result + digis;
  
  	result = result + ":00";
  
  	return result;
  }

}
