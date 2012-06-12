package transxchange2GoogleTransit;

/**
 * Store the latitude and longitude as strings
 * 
 * @author drt24
 * 
 */
public class LatLong {

  public final String latitude;
  public final String longitude;

  public LatLong(String latitude, String longitude) {
    this.latitude = latitude;
    this.longitude = longitude;
  }

  /**
   * Return whether this LatLong has actually been set to real values
   * 
   * @return
   */
  public boolean notSet() {
    return latitude == null || longitude == null || latitude.length() == 0 || longitude.length() == 0;
  }
}
