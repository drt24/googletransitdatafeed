/*
 * Copyright 2007, 2008, 2009, 2010, 2011, 2012 GoogleTransitDataFeed
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */

package transxchange2GoogleTransitHandler;

import java.util.ArrayList;
import java.util.List;

public class ValueList {
  private String keyName;
  private List<String> values;

  public void addValue(String value) {
    values.add(value);
  }

  public String getValue(int i) {
    if (i < 0 || i >= values.size())
      return null;

    return values.get(i);
  }

  public void setValue(int i, String value) {
    if (i < 0 || i >= values.size())
      return;

    values.set(i, value);
  }

  public void dumpValues() {
    System.out.println(toString());
  }

  @Override
  public String toString() {
    return keyName + ": "+ values;
  }

  public String getKeyName() {
    return keyName;
  }

  public int size() {
    return values.size();
  }

  public ValueList(String key) {
    keyName = key;
    values = new ArrayList<String>();
  }
}
