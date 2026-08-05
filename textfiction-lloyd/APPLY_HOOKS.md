# Apply Lloyd hooks to stock TextFiction GameActivity

After `git clone https://github.com/onyxbits/TextFiction.git`:

## 1. Add file
`src/de/onyxbits/textfiction/lloyd/LloydAgentApi.java`  
(from `textfiction-lloyd/src/.../LloydAgentApi.java` in lloydchrisisai)

## 2. GameActivity.java edits

### Import
```java
import de.onyxbits.textfiction.lloyd.LloydAgentApi;
```

### Field (near `private ProgressBar loading;`)
```java
private LloydAgentApi lloydApi;
```

### End of onCreate()
```java
lloydApi = new LloydAgentApi(LloydAgentApi.DEFAULT_PORT);
final GameActivity self = this;
lloydApi.setCommandSink(new LloydAgentApi.CommandSink() {
  @Override
  public void submitCommand(final String command) {
    self.runOnUiThread(new Runnable() {
      @Override
      public void run() {
        if (command != null && command.length() > 0) {
          executeCommand((command + "\n").toCharArray());
        }
      }
    });
  }
});
lloydApi.start();
Log.i("LloydAgentApi", "listening on port " + LloydAgentApi.DEFAULT_PORT);
```

### Start of onDestroy()
```java
if (lloydApi != null) {
  lloydApi.stop();
  lloydApi = null;
}
```

### End of publishResult() — after figureMenuState();
```java
if (lloydApi != null && retainerFragment != null && retainerFragment.engine != null) {
  StringBuilder story = new StringBuilder();
  try {
    for (int i = 0; i < retainerFragment.messageBuffer.size(); i++) {
      StoryItem item = retainerFragment.messageBuffer.get(i);
      if (item != null && item.message != null) {
        if (story.length() > 0) story.append("\n");
        story.append(item.message.toString());
      }
    }
  } catch (Exception e) {
    Log.w("LloydAgentApi", e);
  }
  boolean waiting = retainerFragment.engine.getRunState() == ZMachine.STATE_WAIT_CMD;
  lloydApi.publishState(story.toString(), retainerFragment.upperWindow, waiting);
}
```

## 3. Manifest
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

Then build APK in Android Studio, sign, install, open a .z5 story, and Lloyd controls via port 8765.
