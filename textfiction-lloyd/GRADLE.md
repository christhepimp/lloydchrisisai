# Build Lloyd TextFiction with Gradle

## One-click (GitHub Actions)

1. Open https://github.com/christhepimp/lloydchrisisai/actions
2. Run workflow **Build Lloyd TextFiction APK**
3. Download artifact **lloyd-textfiction-apk** → install the debug APK

The workflow:
- Clones official [onyxbits/TextFiction](https://github.com/onyxbits/TextFiction)
- Sets up Gradle (`com.android.application` 8.2 + compileSdk 28)
- Installs `LloydAgentApi.java`
- Patches `GameActivity` (state + command hooks)
- Adds `INTERNET` permission
- Runs `./gradlew assembleDebug`
- Uploads `app-debug.apk`

Package id: **`ai.lloyd.textfiction`** (side-by-side with stock TextFiction)
Agent API: **port 8765** — `GET /state`, `POST /command`

## Local Gradle (optional)

```bash
git clone https://github.com/onyxbits/TextFiction.git
# create app/ structure, copy sources into app/src/main/
# add LloydAgentApi + GameActivity hooks (see APPLY_HOOKS.md)
# use the app/build.gradle from the CI workflow
./gradlew assembleDebug
```

Requires Android SDK + JDK 17.
