import sqlite3
import sys
import tkinter as tk
import pathlib
import json
import myNotebook as nb
from config import config
import logging
import os

from config import appname

from common.personaldb import Writer, StructuredImport

DB_PATH = "/home/greg/ed/save.db"

this = sys.modules[__name__]

# This could also be returned from plugin_start3()
plugin_name = os.path.basename(os.path.dirname(__file__))

# A Logger is used per 'found' plugin to make it easy to include the plugin's
# folder name in the logging output format.
# NB: plugin_name here *must* be the plugin's folder name as per the preceding
#     code, else the logger won't be properly set up.
logger = logging.getLogger(f'{appname}.{plugin_name}')

# If the Logger has handlers then it was already set up by the core code, else
# it needs setting up here.
if not logger.hasHandlers():
    level = logging.INFO  # So logger.info(...) is equivalent to print()

    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)


def plugin_start3(plugin_dir):
    return plugin_start()


def plugin_start():
    this.marketId = None
    return 'TradeResearch'


def plugin_app(parent):
    label = tk.Label(parent, text="Trade Research:")
    this.status = tk.Label(parent, text="Ready", anchor=tk.W)
    return label, this.status


def plugin_prefs(parent, cmdr, is_beta):
    frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)
    
    return frame


def prefs_changed(cmdr, is_beta):
    pass


def journal_entry(cmdr, is_beta, system, station, entry, state):
    event = entry['event'] if 'event' in entry else None
    this.status['text'] = f"Writing {event}"
    try:
        if not state['Captain'] and entry['event'] in ('Market', 'Outfitting', 'Shipyard'):
            if this.marketId != entry['MarketID']:
                this.commodities = this.outfitting = this.shipyard = None
                this.marketId = entry['MarketID']

            journaldir = config.get_str('journaldir')
            if journaldir is None or journaldir == '':
                journaldir = config.default_journal_dir

            path = pathlib.Path(journaldir) / f'{entry["event"]}.json'

            with path.open('rb') as f:
                entry = json.load(f)

        with sqlite3.connect(DB_PATH) as conn:
            writer = Writer(conn, False)
            importer = StructuredImport(writer)
            importer.event(entry)
            writer.commit()
        this.status['text'] = f"Wrote {event}"
    except Exception as e:
        this.status['text'] = 'Error'
        raise e

