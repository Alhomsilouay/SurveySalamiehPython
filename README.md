# المسح الميدانيّ الخدميّ - سلمية (Python / Kivy)

Same 43-field street-segment survey as the HTML version, built with Kivy so
one codebase runs as a normal offline Windows app and as an offline Android
app (APK). Data is stored locally in SQLite; export to CSV/JSON and import
(merge) JSON from teammates' devices, same workflow as before.

## 1. Get an Arabic font (do this first)

Kivy's default font has no Arabic glyphs, so Arabic text won't render
without one. Download a free, open-license Arabic font, for example
**Noto Naskh Arabic** from Google Fonts:
https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic

Download it, then copy `NotoNaskhArabic-Regular.ttf` into this same folder
(next to `main.py`). The app picks it up automatically.

## 2. Run on Windows

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

This opens a normal desktop window. GPS capture isn't available on
Windows (no GPS hardware access) — the GPS field just stays a manual text
box there; on Android it's filled automatically by the button.

Data is saved in the app's user-data folder (Kivy prints/uses
`App.user_data_dir`, normally
`C:\Users\<you>\AppData\Roaming\salamiehsurvey\`). Exported CSV/JSON files
land in that same folder — the app shows you the exact path after each
export.

## 3. Build the Android APK

Buildozer (the tool that packages this into an .apk) only runs on Linux —
on Windows you need **WSL2** (Windows Subsystem for Linux) first:

1. Install WSL2 + Ubuntu: open PowerShell as admin, run `wsl --install`,
   reboot, then open the "Ubuntu" app from the Start menu.
2. Inside Ubuntu:
   ```
   sudo apt update
   sudo apt install -y python3-pip build-essential git zip unzip openjdk-17-jdk
   pip install buildozer cython
   ```
3. Copy this whole `salamieh_kivy` folder into the Ubuntu filesystem
   (e.g. `~/salamieh_kivy`) — building against a Windows-mounted `/mnt/c/...`
   path is much slower and sometimes fails.
4. From inside that folder:
   ```
   buildozer -v android debug
   ```
   First run downloads the Android SDK/NDK automatically (needs internet,
   can take 30-60 minutes). The resulting APK appears in `bin/`.
5. Copy the `.apk` from `bin/` to the Android phone (cable, cloud drive,
   whatever) and install it (you'll need to allow "install from unknown
   sources" once, since it's not from the Play Store).

Once installed, the app needs **no internet ever again** — it's a normal
offline Android app, and it will ask for location permission the first
time you tap the GPS button.

**Alternative if you don't want to set up WSL:** use a free GitHub Actions
workflow (search "buildozer github action") to build the APK in the cloud
and just download the finished file — no local Linux environment needed.

## 4. Combining data from the team

Same approach as the HTML version: each surveyor's device keeps its own
SQLite database. On the list screen, "تصدير JSON" writes a JSON export;
gather everyone's JSON files onto one device (laptop or a lead surveyor's
phone) and use "استيراد/دمج JSON" to merge them one at a time (duplicates
are skipped by ID). Then "تصدير CSV" gives you one combined file with
columns in the same order as the original Excel sheet.

## Notes / limitations

- This is a single-file app on purpose (`main.py`) to keep it easy to read
  and modify — feel free to split it up as it grows.
- The list screen re-renders the whole list on every add/delete; fine for
  a few hundred segments (a full town survey), would need a
  `RecycleView` if you ever get into the thousands of rows.
- If you want a nicer visual style, `kivymd` (Material Design widgets for
  Kivy) is a drop-in upgrade — ask and I can restyle it.
