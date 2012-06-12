package transxchange2GoogleTransit;

/**
 * Encapsulate information about a stop
 * @author drt24
 *
 */
public class Stop {

  private String code;
  private String name;
  private LatLong position;
  public Stop(String code, String name, LatLong position){
    this.code = code;
    this.name = name;
    this.position = position;
  }
  /**
   * @return the code
   */
  public String getCode() {
    return code;
  }
  /**
   * @return the name
   */
  public String getName() {
    return name;
  }
  /**
   * @return the position
   */
  public LatLong getPosition() {
    return position;
  }
}
