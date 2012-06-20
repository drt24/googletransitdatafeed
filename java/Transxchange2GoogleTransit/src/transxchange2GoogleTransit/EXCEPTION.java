package transxchange2GoogleTransit;

/**
 * The different types of calendar date exception
 * @author drt24
 *
 */
public enum EXCEPTION {
  /** 1 */
  ADD {
    @Override
    public String toString() {
      return "1";
    }
  },
  /** 2 */
  REMOVE {
    @Override
    public String toString() {
      return "2";
    }
  };
}