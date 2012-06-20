package transxchange2GoogleTransit;

/**
 * Encapsulate a Calendar date
 * 
 * @author drt24
 * 
 */
public class CalendarDate implements Comparable<CalendarDate> {
  private final String serviceId;
  private final String date;
  private final EXCEPTION exception;

  public CalendarDate(String serviceId, String date, EXCEPTION exception) {
    this.serviceId = serviceId;
    this.date = date;
    this.exception = exception;
  }

  /**
   * @return the serviceId
   */
  public String getServiceId() {
    return serviceId;
  }

  /**
   * @return the date
   */
  public String getDate() {
    return date;
  }

  /**
   * @return the exception
   */
  public EXCEPTION getException() {
    return exception;
  }
  @Override
  public String toString() {
    return serviceId + "," + date + "," + exception;
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((date == null) ? 0 : date.hashCode());
    result = prime * result + ((exception == null) ? 0 : exception.hashCode());
    result = prime * result + ((serviceId == null) ? 0 : serviceId.hashCode());
    return result;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (!(obj instanceof CalendarDate))
      return false;
    CalendarDate other = (CalendarDate) obj;
    if (date == null) {
      if (other.date != null)
        return false;
    } else if (!date.equals(other.date))
      return false;
    if (exception != other.exception)
      return false;
    if (serviceId == null) {
      if (other.serviceId != null)
        return false;
    } else if (!serviceId.equals(other.serviceId))
      return false;
    return true;
  }

  public int compareTo(CalendarDate o) {
    if (equals(o)) {
      return 0;
    }
    int service = serviceId.compareTo(o.serviceId);
    if (service != 0) {
      return service;
    }
    int dateComparison = date.compareTo(o.date);
    if (dateComparison != 0) {
      return dateComparison;
    }
    return exception.compareTo(o.exception);
  }
}