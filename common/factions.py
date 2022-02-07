#!/usr/bin/env python3

import argparse
import os.path
import time
import requests
import json
import math

EDDB_API = {
        "factions": {
            "url": "https://eddb.io/archive/v6/factions.jsonl",
            "file": "factions.jsonl"
            },
        "systems_populated": {
            "url": "https://eddb.io/archive/v6/systems_populated.jsonl", 
            "file": "systems_populated.jsonl" 
            },
        }


def needs_cache_update(api):
    if not os.path.exists(api["file"]):
        return True
    age = time.time() - os.path.getmtime(api["file"])
    return age > 24*60*60


def update_cache(api):
    response = requests.get(api["url"])
    response.raise_for_status()
    with open(api["file"], "w") as file:
        file.write(response.text)


def get_data(data_type):
    with open(EDDB_API[data_type]["file"], "r") as file:
        return {e['id']: e for e in [json.loads(line) for line in file.readlines()]}


def faction_filter(government):
    def filter_lambda(faction):
        if government != 'all' and government != faction['government']:
            return False
        return True
    return filter_lambda


def single_system(systems, **kwargs):
    found = [system for system in systems.values() if all([system[k] == kwargs[k] for k in kwargs])]
    if len(found) == 0:
        raise Exception("No system found matching criteria " + str(kwargs))
    if len(found) > 1:
        raise Exception("Multiple systems found matching criteria " + str(kwargs) + " " + str(found))
    return found[0]


def system_filter_factions(factions):
    def filter_lambda(system):
        for faction_presence in system['minor_faction_presences']:
            faction_id = faction_presence['minor_faction_id']
            if faction_id in factions:
                return True
        return False
    return filter_lambda


def dist(a, b):
    def sq(coord):
        d = a[coord] - b[coord]
        return d*d
    return math.sqrt(sq('x') + sq('y') + sq('z'))


def system_filter_sphere(center_system, radius):
    def filter_lambda(system):
        if radius != -1:
            return dist(system, center_system) < radius
        return True
    return filter_lambda


def filter_and(*filter_fns):
    def filter_lambda(x):
        for filter_fn in filter_fns:
            if not filter_fn(x):
                return False
        return True
    return filter_lambda


def key_fn(sort_type):
    def key(system):
        if sort_type == 'updated-desc':
            return system['updated_at']
    return key


def staleness(ts):
    delta = int(time.time()) - ts
    units = "s"
    if delta > 60:
        delta /= 60
        units = "m"
    if delta > 60:
        delta /= 60
        units = "h"
    if delta > 24:
        delta /= 24
        units = "d"
    if delta > 365:
        delta /= 365
        units = "y"
    
    return str(int(delta)) + units


def print_system(system, factions):
    faction_ids = [presence["minor_faction_id"] for presence in system["minor_faction_presences"]]
    factions_present = [factions[faction_id]["name"] for faction_id in faction_ids if faction_id in factions]
    print("%30s last updated %4s ago has a presence of %s" % (
        system["name"], 
        staleness(system["updated_at"]),
        str(factions_present)
        ))


def filter_map(fn, map_in):
    def value_filter(item):
        return fn(item[1])
    return dict(filter(value_filter, map_in.items()))
    

def main():
    parser = argparse.ArgumentParser(
            description="Retrieve a list of factions")
    parser.add_argument(
            "--force-update", dest="update", 
            action="store_true", default=False, 
            help="Force retrieving a new copy of backing data")
    parser.add_argument(
            "--government", dest="government",
            default="Communism",
            help="Government type of factions shown")
    parser.add_argument(
            "--sort", dest="sort",
            default="updated-desc", 
            choices=["updated-desc"],
            help="Order to sort results in")
    parser.add_argument(
            "--center", dest="center",
            default="Sol",
            help="Center of search area")
    parser.add_argument(
            "--range", dest="range",
            default=-1,
            type=int,
            help="Range, in Ly around center to search, -1 for unlimited")

    args = parser.parse_args()

    for api in EDDB_API.values():
        if args.update or needs_cache_update(api):
            update_cache(api)
    all_factions = get_data("factions")
    filtered_factions = filter_map(faction_filter(args.government), all_factions)

    all_systems = get_data("systems_populated")
    center_system = single_system(all_systems, name=args.center)
    filtered_systems = filter_map(filter_and(
            system_filter_factions(filtered_factions), 
            system_filter_sphere(center_system, args.range)
        ), all_systems)
    sorted_systems = sorted(filtered_systems.values(), key=key_fn(args.sort))
    for system in sorted_systems:
        print_system(system, filtered_factions)


if __name__ == "__main__":
    main()
