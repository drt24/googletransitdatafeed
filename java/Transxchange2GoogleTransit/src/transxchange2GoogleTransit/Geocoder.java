package transxchange2GoogleTransit;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLEncoder;
import java.util.StringTokenizer;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;

import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

/**
 * Provides utility method for geocoding names of places to {@link LatLong}
 * 
 * @see #geocodeMissingStop(String)
 * 
 */
public class Geocoder {
  private Geocoder() {
  }

  public static LatLong geocodeMissingStop(String stopname) throws MalformedURLException,
      UnsupportedEncodingException, XPathExpressionException, IOException,
      ParserConfigurationException, SAXException {
    float[] coordFloat = {-999999, -999999};
    String broadenedStopname;
    String token;
    StringTokenizer st;

    geocodeStop(stopname, coordFloat);

    // If no result: Broaden search. First try: remove cross street
    if ((coordFloat[0] == -999999 || coordFloat[1] == -999999) && stopname.contains("/")) {
      broadenedStopname = "";
      st = new StringTokenizer(stopname, ",");
      while (st.hasMoreTokens()) {
        token = st.nextToken();
        if (token.contains("/"))
          token = token.substring(0, token.indexOf("/"));
        if (broadenedStopname.length() > 0)
          broadenedStopname += ", ";
        broadenedStopname += token;
      }
      if (!broadenedStopname.equals(stopname)) {
        stopname = broadenedStopname;
        geocodeStop(stopname, coordFloat);
      }
    }

    // Next try: Remove qualifiers in brackets
    if ((coordFloat[0] == -999999 || coordFloat[1] == -999999) && stopname.contains("(")) {
      broadenedStopname = "";
      st = new StringTokenizer(stopname, ",");
      while (st.hasMoreTokens()) {
        token = st.nextToken();
        if (token.contains("("))
          token = token.substring(0, token.indexOf("("));
        if (broadenedStopname.length() > 0)
          broadenedStopname += ", ";
        broadenedStopname += token;
      }
      if (!broadenedStopname.equals(stopname)) {
        stopname = broadenedStopname;
        geocodeStop(stopname, coordFloat);
      }
    }

    // Go for broke: remove elements from least specific to broadest
    while ((coordFloat[0] == -999999 || coordFloat[1] == -999999) && stopname.lastIndexOf(",") >= 0) {
      stopname = stopname.substring(0, stopname.lastIndexOf(","));
      geocodeStop(stopname, coordFloat);
    }

    String latitude = null;
    if (coordFloat[0] != -999999) {
      latitude = "" + coordFloat[0];
    }
    String longitude = null;
    if (coordFloat[1] != -999999) {
      longitude = "" + coordFloat[1];
    }

    return new LatLong(latitude, longitude);
  }

  private static void geocodeStop(String stopname, float[] coordinates)
      throws MalformedURLException, UnsupportedEncodingException, XPathExpressionException,
      IOException, ParserConfigurationException, SAXException {
    final String geocoderPrefix = "http://maps.google.com/maps/api/geocode/xml?address=";
    final String geocoderPostfix = "&sensor=false";

    if (stopname == null || coordinates == null || coordinates.length != 2)
      return;
    String geoaddress = geocoderPrefix + stopname + geocoderPostfix;
    System.out.println("  Trying: " + geoaddress);
    URL url = new URL(geocoderPrefix + URLEncoder.encode(stopname, "UTF-8") + geocoderPostfix);
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    conn.connect();
    InputSource inputStream = new InputSource(conn.getInputStream());
    Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(inputStream);

    XPath xp = XPathFactory.newInstance().newXPath();
    NodeList geocodedNodes =
        (NodeList) xp.evaluate("/GeocodeResponse/result[1]/geometry/location/*", doc,
            XPathConstants.NODESET);
    float lat = -999999;
    float lon = -999999;
    Node node;
    for (int i = 0; i < geocodedNodes.getLength(); i++) {
      node = geocodedNodes.item(i);
      if ("lat".equals(node.getNodeName()))
        lat = Float.parseFloat(node.getTextContent());
      if ("lng".equals(node.getNodeName()))
        lon = Float.parseFloat(node.getTextContent());
    }
    coordinates[0] = lat;
    coordinates[1] = lon;
  }
}
