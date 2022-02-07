#!/usr/bin/env python3

import json
import os
import sqlite3

from personaldb import Writer, StructuredImport, GroupImport

DB_PATH = "/home/greg/ed/save.db"
SAVE_PATH = "/home/greg/ed/journals/"


def load_file(file_path):
    if "Journal." not in file_path.name:
        return []
    with open(file_path, 'r') as file:
        return [json.loads(line) for line in file.readlines()]


def import_save_to_db(save_path, db_path):
    with sqlite3.connect(db_path) as conn:
        writer = Writer(conn, False)
        importer = StructuredImport(writer)
        with os.scandir(save_path) as files:
            for file_path in files:
                contents = load_file(file_path)
                import_obj = GroupImport(file_path.path, writer, importer, len(contents))
                count = import_obj.events(lambda: contents)
                if count > 0:
                    print(f"Imported {count} events from {file_path.path}")


if __name__ == "__main__":
    import_save_to_db(SAVE_PATH, DB_PATH)

