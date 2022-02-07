Elite Scripts
=============

A set of basic scripts for automating some more tedious parts of the Elite: Dangerous experience.

There are three major components these scripts:
1. A Plugin for EDMarketConnector to stream data from the game
2. AutoKey scripts for manually interacting with the game via the player UI
3. Backend scripts for examining the information gathered from the plugin and player UI.

Current features:
* AutoKey script for requesting docking access to a station
* AutoKey script for 3Rs at a station
* AutoKey script for taking screenshots of the station news feed and processing the images with OCR
* Storage of collected information to an on-disk Sqlite3 database for later analysis
* Batch script for backfilling journal entries if EDMarketConnector was not running.
* Batch script for computing personal best exploration finds
* Batch script for computing trade routes targeting a specific faction & system

Scripts are extremely immature and leave files in strange locations, rely on hardcoded paths and resolutions,
and are basically guaranteed to break on your system. Please be patient, or come in ready to hack your way to success.

Roadmap:
* Setup guide for Linux
* Cleaner temporary file management
* Build, Test, and Packaging scripts
* GitHub Workflows for Releases
* More configurability and standardization across invocation environments
* AutoHotKey ports of AutoKey scripts
* Portability improvements for running under Windows
* Setup guide for Windows
* Single entry point CLI for executable scripts