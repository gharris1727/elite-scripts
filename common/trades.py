#!/usr/bin/env python3

import requests
import time
import argparse
import re

from bs4 import BeautifulSoup, Tag, NavigableString


def exact_match(list_in, accessor, criteria):
    exact = [x for x in list_in if accessor(x) == criteria]
    if len(exact) != 1:
        raise Exception(
            "unable to find exact match \""
            + criteria
            + "\" among "
            + str([accessor(x) for x in list_in]))
    return exact[0]


def find_stations(system_name):
    params = {
        "system[name]": system_name,
        "expand": "station",
        "system[has_commodities]": 1,
        "system[version]": 2,
        "_": 163261048162
    }
    resp = requests.get("https://eddb.io/system/search", params=params)
    resp.raise_for_status()
    system = exact_match(resp.json(), lambda s: s.name, system_name)
    return system.id, system.stations


CSRF_HEADER = "eddb token"
CSRF_COOKIE = "eddb token"


def find_faction(faction_name):
    data = {
        "faction[name]": faction_name,
        "faction[page]": 0
    }
    headers = {
        "x-csrf-token": CSRF_HEADER,
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {
        "_csrf": CSRF_COOKIE
    }

    resp = requests.post("https://eddb.io/faction", data=data, headers=headers, cookies=cookies)
    resp.raise_for_status()
    doc = BeautifulSoup(resp.text, features="lxml")
    table = doc.find(class_="factionSearchResult").find("tbody")
    factions = [{
        "id": int(row["data-key"]),
        "name": row.find(href="/faction/" + row["data-key"]).string,
    } for row in table.find_all("tr")]
    faction = exact_match(factions, lambda f: f["name"], faction_name)

    return faction["id"]


def find_faction_systems(faction_id):
    resp = requests.get("https://eddb.io/faction/" + str(faction_id))
    resp.raise_for_status()
    doc = BeautifulSoup(resp.text, features="lxml")

    def parse_station(system_id, faction_id, item):
        station = {}
        title = item.find("strong").find("a")
        station["id"] = int(title['href'].split("/")[-1])
        station["name"] = str(title.string)
        station["system_id"] = system_id
        station["faction_id"] = faction_id

        strings = [str(ns).strip() for ns in item.children if isinstance(ns, NavigableString)]
        station["state"] = strings[-1]
        station["government"] = strings[-2]
        station["allegiance"] = strings[-3]
        station["economy"] = strings[-4]
        station["distance"] = strings[-5]
        station["pads"] = strings[-6]

        station["planetary"] = item.find(class_="icon-planet") is not None
        # The odyssey icon doesn't have a distinctive class yet
        station["odyssey"] = len(strings) > 10

        return station

    def parse_row(row):
        system_id = int(row.find("a")['href'].split("/")[-1])
        name = str(next(row.find("a").children).string)
        row = row.next_sibling
        factions = []
        faction = None
        while row:
            if isinstance(row, Tag):
                class_ = row["class"]
                if "systemRow" in class_:
                    factions.append(faction)
                    break
                if "systemFactionRow" in class_:
                    if faction is not None:
                        factions.append(faction)
                    faction = {}
                    title = row.find(class_="factionName").find("a")
                    faction["id"] = int(title['href'].split("/")[-1])
                    faction["name"] = str(title.string)
                    faction["influence"] = str(row.find(class_="factionInfluence").find("span").string)
                    faction["stations"] = []
                if "factionStationsRow" in class_:
                    station_list = row.find(class_="stationList")
                    if station_list:
                        faction["stations"] = [parse_station(system_id, faction["id"], item) for item in
                                               station_list.find_all("li")]
            row = row.next_sibling
        return {"id": system_id, "name": name, "factions": factions}

    return [parse_row(row) for row in doc.find_all(class_="systemRow")]


def stations_for_faction_system(faction_name, system_name):
    faction_id = find_faction(faction_name)
    systems = find_faction_systems(faction_id)
    system = exact_match(systems, lambda s: s["name"], system_name)
    return exact_match(system["factions"], lambda f: f["name"], faction_name)["stations"]


def single_route(sell_system_id, sell_station_id, amount, range, pad, planetary, odyssey, fleetcarrier):
    data = {
        "singleSettings": {
            "buySystemId": None,
            "sellSystemId": sell_system_id,
            "buyStationId": None,
            "sellStationId": sell_station_id,
            "implicitCommodities": [],
            "ignoredCommodities": [],
            "minSupply": amount,
            "minDemand": amount,
            "hopDistance": range,
            "cargoCapacity": amount,
            "credits": 1000000 * amount,
            "priceAge": None
        },
        "systemFilter": {
            "skipPermit": True,
            "powers": []
        },
        "stationFilter": {
            "landingPad": 30 if pad == "L" else None,
            "governments": [],
            "allegiances": [],
            "states": [],
            "economies": [],
            "distance": None,
            "loopDistance": 500,
            "singleRouteDistance": 0,
            "includePlanetary": planetary,
            "includeOdyssey": odyssey,
            "includeFleetCarriers": fleetcarrier
        },
    }
    routes = requests.post("https://eddb.io/route/search/single", json=data)
    routes.raise_for_status()
    return routes.json()


def pads_atleast(station, requirement):
    if station == "L":
        return True
    if station == "M":
        return requirement == "M" or requirement == "S"
    if station == "S":
        return requirement == "S"
    return False


def best_trade_routes_for_faction_system(faction_name, system_name, amount, radius, pad, planetary, odyssey,
                                         fleetcarrier):
    all_stations = stations_for_faction_system(faction_name, system_name)
    if len(all_stations) == 0:
        raise Exception("Faction "
                        + faction_name
                        + " does not control any stations in "
                        + system_name)

    def station_predicate(station):
        if station["odyssey"]:
            return odyssey
        if station["planetary"]:
            return planetary
        if not pads_atleast(station["pads"], pad):
            return False
        return True

    filtered_stations = [station for station in all_stations if station_predicate(station)]
    if len(filtered_stations) == 0:
        raise Exception("No stations matched the search criteria"
                        + " pad: " + str(pad)
                        + " planetary: " + str(planetary)
                        + " odyssey: " + str(odyssey))
    routes = []
    for station in filtered_stations:
        routes.extend(
            single_route(station["system_id"], station["id"], amount, radius, pad, planetary, odyssey, fleetcarrier))
    routes.sort(reverse=True, key=lambda r: int(r["totalProfit"]))
    routes = routes[:5]

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

    for route in routes:
        print("Buy %3d %30s at %30s (%1s, %10dLs, %4s) in %30s" % (
            int(route["unitCount"]),
            route["commodity"]["name"],
            route["buyStation"]["name"],
            route["buyStation"]["max_landing_pad_size"],
            route["buyStation"]["distance_to_star"],
            staleness(route["buyStation"]["market_updated_at"]),
            route["buySystem"]["name"]
        ))
        print("Sell to %30s at %30s (%1s, %10dLs, %4s) in %30s for a profit of %4.1fM (%4.1fk/t)" % (
            faction_name,
            route["sellStation"]["name"],
            route["sellStation"]["max_landing_pad_size"],
            route["sellStation"]["distance_to_star"],
            staleness(route["sellStation"]["market_updated_at"]),
            route["sellSystem"]["name"],
            float(route["totalProfit"]) / 1000000,
            float(route["unitProfit"]) / 1000
        ))


parser = argparse.ArgumentParser(description="Find trade routes")

parser.add_argument("--clipboard",
                    help="Load systems and factions from the clipboard, Enosis-formatted",
                    action="store_true")
parser.add_argument("--faction",
                    help="Faction name owning sell stations",
                    default=[],
                    action="append")
parser.add_argument("--system",
                    help="System name containing sell stations",
                    default=[],
                    action="append")
parser.add_argument("--include-planetary",
                    help="whether to include planetary bases",
                    dest="planetary",
                    default=False,
                    action="store_true")
parser.add_argument("--include-odyssey",
                    help="whether to include odyssey bases",
                    dest="odyssey",
                    default=False,
                    action="store_true")
parser.add_argument("--include-fleet-carrier",
                    help="whether to include odyssey bases",
                    dest="fleetcarrier",
                    default=False,
                    action="store_true")
parser.add_argument("--range",
                    help="Trading route range, in Ly")
parser.add_argument("--cargo",
                    help="Cargo capacity, in tons")
parser.add_argument("--pad",
                    help="Minimum size of landing pad",
                    choices=["S", "M", "L"])
parser.add_argument("--profile",
                    help="Standard ship profile to filter",
                    choices=["python", "type9"],
                    default="python")

args = parser.parse_args()

if args.clipboard:
    import pyperclip

    text = pyperclip.paste()
    regex = "--\n([^\n]+)\nNeeds ([0-9.]+) points in ([^.]+).\nCurrent state: ([^\n]+)"
    for match in re.finditer(regex, text):
        args.faction.append(match.group(1))
        args.system.append(match.group(3))

profiles = {
    "python": {"range": 28, "cargo": 280, "pad": "M"},
    "type9": {"range": 16, "cargo": 752, "pad": "L"}
}
profile = profiles[args.profile]
if not args.range:
    args.range = profile["range"]
if not args.cargo:
    args.cargo = profile["cargo"]
if not args.pad:
    args.pad = profile["pad"]

for system, faction in zip(args.system, args.faction):
    try:
        best_trade_routes_for_faction_system(
            faction,
            system,
            args.cargo,
            args.range,
            args.pad,
            args.planetary,
            args.odyssey,
            args.fleetcarrier)
    except Exception as e:
        print("Unable to find trade routes: " + str(e))
