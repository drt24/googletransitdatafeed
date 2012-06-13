package transxchange2GoogleTransit;

/**
 * Encapsulate information about an Agency
 * 
 * @author drt24
 * 
 */
public class Agency {

  private final String id;
  private final String name;
  private final String url;
  private final String timeZone;
  private final String lang;
  private final String phone;

  public Agency(String id, String name, String url, String timeZone, String lang, String phone) {
    this.id = id;
    this.name = name;
    this.url = url;
    this.timeZone = timeZone;
    this.lang = lang;
    this.phone = phone;
  }

  /**
   * @return the id
   */
  public String getId() {
    return id;
  }

  /**
   * @return the name
   */
  public String getName() {
    return name;
  }

  /**
   * @return the url
   */
  public String getUrl() {
    return url;
  }

  /**
   * @return the timeZone
   */
  public String getTimeZone() {
    return timeZone;
  }

  /**
   * @return the lang
   */
  public String getLang() {
    return lang;
  }

  /**
   * @return the phone
   */
  public String getPhone() {
    return phone;
  }
}
