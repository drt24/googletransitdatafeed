package transxchange2GoogleTransit;

/**
 * Encapsulate information about routes
 * 
 * @author drt24
 * 
 */
public class Route {

  private final String id;
  private final String agencyId;
  private final String shortName;
  private final String longName;
  private final String description;
  private final String destination;
  private final String origin;
  private final String type;
  private final String serviceId;

  public Route(String id, String agencyId, String shortName, String longName, String description,
      String destination, String origin, String type, String serviceId) {
    this.id = id;
    this.agencyId = agencyId;
    this.shortName = shortName;
    this.longName = longName;
    this.description = description;
    this.destination = destination;
    this.origin = origin;
    this.type = type;
    this.serviceId = serviceId;
  }

  /**
   * @return the id
   */
  public String getId() {
    return id;
  }

  /**
   * @return the agencyId
   */
  public String getAgencyId() {
    return agencyId;
  }

  /**
   * @return the shortName
   */
  public String getShortName() {
    return shortName;
  }

  /**
   * @return the longName
   */
  public String getLongName() {
    return longName;
  }

  /**
   * @return the description
   */
  public String getDescription() {
    return description;
  }

  /**
   * @return the destination
   */
  public String getDestination() {
    return destination;
  }

  /**
   * @return the origin
   */
  public String getOrigin() {
    return origin;
  }

  /**
   * @return the type
   */
  public String getType() {
    return type;
  }

  /**
   * @return the serviceId
   */
  public String getServiceId() {
    return serviceId;
  }
}
