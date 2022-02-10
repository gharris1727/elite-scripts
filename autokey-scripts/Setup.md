AutoKey Script Setup
====================

These are instructions on configuring (AutoKey)[https://github.com/autokey/autokey] with the scripts in this directory.

1. Clone this repository to your desired location.
2. Install AutoKey following the (instructions for your distribution)[https://github.com/autokey/autokey/wiki/Installing]
3. Start the AutoKey GUI
4. Click 'New > Folder'
5. Select the `autokey-scripts` directory from this repository in the file browser, and confirm.
6. Select the `autokey-scripts` directory in the AutoKey GUI, and the 'Set' button for the 'Window Filter'
7. Paste `steam_app_359320.steam_app_359320` into the modal, select 'Apply recursively', and confirm.
8. Expand the `autokey-scripts` directory in the AutoKey GUI to see the individual scripts.
9. Select each, select 'Set', and configure the key that you would like to trigger that particular script.
10. Select 'Edit > Preferences > Script Engine > User Module Folder'
11. Select the `elite-scripts` parent directory and confirm.

# AutoKey compatibility patch for Elite Dangerous
Copy the following contents into a patch file:
```
@@ -820,7 +814,9 @@
     def __fakeKeypress(self, keyName):        
         keyCode = self.__lookupKeyCode(keyName)
         xtest.fake_input(self.rootWindow, X.KeyPress, keyCode)
+        self.localDisplay.sync()
         xtest.fake_input(self.rootWindow, X.KeyRelease, keyCode)
+        self.localDisplay.sync()
 
     def fake_keydown(self, keyName):
         self.__enqueue(self.__fakeKeydown, keyName)
@@ -828,6 +824,7 @@
     def __fakeKeydown(self, keyName):
         keyCode = self.__lookupKeyCode(keyName)
         xtest.fake_input(self.rootWindow, X.KeyPress, keyCode)
+        self.localDisplay.sync()
 
     def fake_keyup(self, keyName):
         self.__enqueue(self.__fakeKeyup, keyName)
@@ -835,6 +832,7 @@
     def __fakeKeyup(self, keyName):
         keyCode = self.__lookupKeyCode(keyName)
         xtest.fake_input(self.rootWindow, X.KeyRelease, keyCode)
+        self.localDisplay.sync()
 
     def send_modified_key(self, keyName, modifiers):
         """
```
This patch should be applied to the `interface.py` implementation of your AutoKey, wherever it is installed.
For example, the following command would apply it to autokey if it was in your system python site-packages:
```commandline
patch /usr/lib/python3.10/site-packages/autokey/interface.py elite-dangerous-autokey.patch
```

I've submitted a patch (upstream)[https://github.com/autokey/autokey/pull/660], but if your installation does not come 
with a suitable patch, you may need to apply it yourself before using AutoKey.

Script Descriptions and Precondition
====================================

Autodock
--------
Usage: Request docking permission for stations & settlements

Preconditions:
1. Left-side panel should be on the first tab 'Navigation'
2. Station/Settlement must not be selected in the third tab 'Contacts'
3. Station/Settlement must be within 7.5km shortly after pressing the hotkey.

Refuel
------
Usage: Refuel/Repair/Rearm your ship while docked at a station or settlement.

Preconditions:
1. Cursor must be on the 'Refuel' button in the main station UI.

StationScreenshots
------------------
Usage: Take a series of screenshots of the station's news feed, and submit them to an OCR script for parsing.

Preconditions:
1. A compatible OCR engine must be installed (Tesseract, Tesseract-eng)
2. Persistent storage for screenshots and temporary storage for crops/text should be writable by the user
3. Sqlite3 must be installed on the same python installation as AutoKey
4. Target sqlite3 database must not have an open client holding a lock
5. Cursor must be on the 'Refuel' button in the main station UI
