package transxchange2GoogleTransit;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;

/**
 * Support iterating over the input streams from a set of files
 * @author drt24
 *
 */
public class FileSet implements StreamSet {

  public static class FileIterator implements Iterator<InputStream> {

    private Iterator<File> fileIterator;

    public FileIterator(Collection<File> fileList) {
      this.fileIterator = fileList.iterator();
    }

    public boolean hasNext() {
      return fileIterator.hasNext();
    }

    /**
     * @throws IllegalStateException if the next file has been removed from the file system
     */
    public InputStream next() {
      try {
        return new FileInputStream(fileIterator.next());
      } catch (FileNotFoundException e) {
        // We validate input so this shouldn't be possible unless someone concurrently removes the
        // file. We can't throw a normal exception as we are constrained by the Iterator interface
        throw new IllegalStateException(e);
      }
    }

    public void remove() {
      fileIterator.remove();
    }

  }

  private final Collection<File> fileList;

  public FileSet(File file) throws FileNotFoundException {
    if (!file.canRead()) {
      throw new FileNotFoundException("File not readable: " + file);
    }
    fileList = new ArrayList<File>(1);
    fileList.add(file);
  }

  public FileSet(Collection<File> files) throws FileNotFoundException {
    for (File file : files) {
      if (!file.canRead()) {
        throw new FileNotFoundException("File not readable: " + file);
      }
    }
    fileList = files;
  }

  public Iterator<InputStream> iterator() {
    return new FileIterator(fileList);
  }

}
