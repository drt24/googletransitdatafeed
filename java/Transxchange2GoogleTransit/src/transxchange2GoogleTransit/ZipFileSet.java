package transxchange2GoogleTransit;

import java.io.IOException;
import java.io.InputStream;
import java.util.Enumeration;
import java.util.Iterator;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Iterate through the input streams in a zip file
 * @author drt24
 *
 */
public class ZipFileSet implements StreamSet {

  public class ZipFileIterator implements Iterator<InputStream> {

    private Enumeration<? extends ZipEntry> zipFileEnum;

    public ZipFileIterator(ZipFile zipFile) {
      zipFileEnum = zipFile.entries();
    }

    public boolean hasNext() {
      return zipFileEnum.hasMoreElements();
    }

    /**
     * @throws IllegalStateException on IOException
     */
    public InputStream next() {
      try {
        return zipFile.getInputStream(zipFileEnum.nextElement());
      } catch (IOException e) {
        throw new IllegalStateException(e);
      }
    }

    /**
     * @throws UnsupportedOperationException if called
     */
    @Deprecated
    public void remove() {
      throw new UnsupportedOperationException("Cannot remove a zipentry from a zip file");
    }

  }

  private ZipFile zipFile;

  public ZipFileSet(ZipFile zipFile) {
    this.zipFile = zipFile;
  }

  public Iterator<InputStream> iterator() {
    return new ZipFileIterator(zipFile);
  }

}
