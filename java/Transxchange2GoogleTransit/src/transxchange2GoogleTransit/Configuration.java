package transxchange2GoogleTransit;

import java.util.List;
import java.util.Map;

public class Configuration {
  boolean useAgencyShortName = false;
  boolean skipEmptyService = false;
  boolean skipOrphanStops = false;
  boolean geocodeMissingStops = false;
  Map<String, String> modeList = null;
  List<String> stopColumns = null;
  String stopfileColumnSeparator = ",";
  int naptanHelperStopColumn = -1;
  /**
   * atco code to name of stop to display to user 
   */
  Map<String, Stop> naptanStops = null;
  Map<String, String> agencyMap = null;
  String url = null;
  String timezone = null;
  String defaultRouteType = null;
  String lang = "";
  String phone = "";
  String rootDirectory = "";
  String outputDirectory = null;
  String stopFile = null;
  String inputFileName = null;

  public Configuration() {
  }

  public Configuration(Configuration toCopy) {
    useAgencyShortName = toCopy.useAgencyShortName;
    skipEmptyService = toCopy.skipEmptyService;
    skipOrphanStops = toCopy.skipOrphanStops;
    geocodeMissingStops = toCopy.geocodeMissingStops;
    modeList = toCopy.modeList;
    stopColumns = toCopy.stopColumns;
    stopfileColumnSeparator = toCopy.stopfileColumnSeparator;
    naptanHelperStopColumn = toCopy.naptanHelperStopColumn;
    naptanStops = toCopy.naptanStops;
    agencyMap = toCopy.agencyMap;
    url = toCopy.url;
    timezone = toCopy.timezone;
    defaultRouteType = toCopy.defaultRouteType;
    lang = toCopy.lang;
    phone = toCopy.phone;
    rootDirectory = toCopy.rootDirectory;
    outputDirectory = toCopy.outputDirectory;
    stopFile = toCopy.stopFile;
    inputFileName = toCopy.inputFileName;
  }

  /**
   * @return the useAgencyShortName
   */
  public boolean useAgencyShortName() {
    return useAgencyShortName;
  }

  /**
   * @param useAgencyShortName the useAgencyShortName to set
   */
  public void setUseAgencyShortName(boolean useAgencyShortName) {
    this.useAgencyShortName = useAgencyShortName;
  }

  /**
   * @return the skipEmptyService
   */
  public boolean skipEmptyService() {
    return skipEmptyService;
  }

  /**
   * @param skipEmptyService the skipEmptyService to set
   */
  public void setSkipEmptyService(boolean skipEmptyService) {
    this.skipEmptyService = skipEmptyService;
  }

  /**
   * @return the skipOrphanStops
   */
  public boolean skipOrphanStops() {
    return skipOrphanStops;
  }

  /**
   * @param skipOrphanStops the skipOrphanStops to set
   */
  public void setSkipOrphanStops(boolean skipOrphanStops) {
    this.skipOrphanStops = skipOrphanStops;
  }

  /**
   * @return the geocodeMissingStops
   */
  public boolean geocodeMissingStops() {
    return geocodeMissingStops;
  }

  /**
   * @param geocodeMissingStops the geocodeMissingStops to set
   */
  public void setGeocodeMissingStops(boolean geocodeMissingStops) {
    this.geocodeMissingStops = geocodeMissingStops;
  }

  /**
   * @return the modeList
   */
  public Map<String, String> getModeList() {
    return modeList;
  }

  /**
   * @param modeList the modeList to set
   */
  public void setModeList(Map<String, String> modeList) {
    this.modeList = modeList;
  }

  /**
   * @return the stopColumns
   */
  public List<String> getStopColumns() {
    return stopColumns;
  }

  /**
   * @param stopColumns the stopColumns to set
   */
  public void setStopColumns(List<String> stopColumns) {
    this.stopColumns = stopColumns;
  }

  /**
   * @return the stopfileColumnSeparator
   */
  public String getStopfileColumnSeparator() {
    return stopfileColumnSeparator;
  }

  /**
   * @param stopfileColumnSeparator the stopfileColumnSeparator to set
   */
  public void setStopfileColumnSeparator(String stopfileColumnSeparator) {
    if (stopfileColumnSeparator != null) {
      this.stopfileColumnSeparator = stopfileColumnSeparator;
    }
  }

  /**
   * @return the naptanHelperStopColumn
   */
  public int getNaptanHelperStopColumn() {
    return naptanHelperStopColumn;
  }

  /**
   * @param naptanHelperStopColumn the naptanHelperStopColumn to set
   */
  public void setNaptanHelperStopColumn(int naptanHelperStopColumn) {
    this.naptanHelperStopColumn = naptanHelperStopColumn;
  }

  /**
   * @return the naptanStops
   */
  public Map<String, Stop> getNaptanStops() {
    return naptanStops;
  }

  public Stop getNaptanStop(String atcoCode) {
    if (null == naptanStops){
      return null;
    } else {
      return naptanStops.get(atcoCode);
    }
  }

  /**
   * @param naptanStops the naptanStops to set
   */
  public void setNaptanStops(Map<String, Stop> naptanStopnames) {
    this.naptanStops = naptanStopnames;
  }

  /**
   * @return the agencyMap
   */
  public Map<String, String> getAgencyMap() {
    return agencyMap;
  }

  /**
   * @param agencyMap the agencyMap to set
   */
  public void setAgencyMap(Map<String, String> agencyMap) {
    this.agencyMap = agencyMap;
  }

  /**
   * @return the url
   */
  public String getUrl() {
    return url;
  }

  /**
   * @param url the url to set
   */
  public void setUrl(String url) {
    this.url = url;
  }

  /**
   * @return the timezone
   */
  public String getTimezone() {
    return timezone;
  }

  /**
   * @param timezone the timezone to set
   */
  public void setTimezone(String timezone) {
    this.timezone = timezone;
  }

  /**
   * @return the defaultRouteType
   */
  public String getDefaultRouteType() {
    return defaultRouteType;
  }

  /**
   * @param defaultRouteType the defaultRouteType to set
   */
  public void setDefaultRouteType(String defaultRouteType) {
    this.defaultRouteType = defaultRouteType;
  }

  /**
   * @return the lang
   */
  public String getLang() {
    return lang;
  }

  /**
   * @param lang the lang to set
   */
  public void setLang(String lang) {
    this.lang = lang;
  }

  /**
   * @return the phone
   */
  public String getPhone() {
    return phone;
  }

  /**
   * @param phone the phone to set
   */
  public void setPhone(String phone) {
    this.phone = phone;
  }

  /**
   * @return the rootDirectory
   * @see #getQualifiedOutputDirectory()
   */
  public String getRootDirectory() {
    return rootDirectory;
  }

  /**
   * @param rootDirectory the rootDirectory to set
   */
  public void setRootDirectory(String rootDirectory) {
    this.rootDirectory = rootDirectory;
  }

  /**
   * @return the outputDirectory
   * @see #getQualifiedOutputDirectory()
   */
  public String getOutputDirectory() {
    return outputDirectory;
  }

  /**
   * @param outputDirectory the outputDirectory to set
   */
  public void setOutputDirectory(String outputDirectory) {
    this.outputDirectory = outputDirectory;
  }

  /**
   * @return the stopFile
   */
  public String getStopFile() {
    return stopFile;
  }

  /**
   * @param stopFile the stopFile to set
   */
  public void setStopFile(String stopFile) {
    this.stopFile = stopFile;
  }

  /**
   * @return the inputFileName
   */
  public String getInputFileName() {
    return inputFileName;
  }

  /**
   * @param inputFileName the inputFileName to set
   */
  public void setInputFileName(String inputFileName) {
    this.inputFileName = inputFileName;
  }

  public String getQualifiedOutputDirectory() {
    return rootDirectory + outputDirectory;
  }
}
