import sqlite3
import csv
import sys

DB_PATH = "/home/greg/ed/save.db"


def dump_res(res):
    if res:
        print([col[0] for col in res.description])
        for r in res:
            print(r)
    else:
        print("no results")

# Assumptions:
# At least one jump into the system recorded
# Second measurement of traffic/influence occurred more than 4 hours after the setup,
# and after the influence tick has passed (don't visit twice in one day >4h apart).


def get_trade_data(db_path):
    tick_cutoff = '+4 hours'
    tick_duration = '1 day'
    # There's some sort of clock skew between the timestamp captured when taking screenshots, and timestamps from EDMC.
    # Screenshots were recorded as taking place ~25s before the docking event
    # Artificially add this skew back into the timestamp so that it lines up.
    screenshot_fudge = '+1 minute'

    writer = csv.writer(sys.stdout)
    with sqlite3.connect(db_path) as conn:
        for transaction_type, inventory_type in [("Buy", "Stock"), ("Sell", "Demand")]:
            res = conn.execute(f"""
            SELECT 
                date(TransactTime) Date,
                Trades.StarSystem,
                Population,
                Trades.Faction,
                StatusBefore.Influence,
                "{transaction_type}" Type,
                Commodity_Localised Commodity,
                Count,
                Inventory,
                Inventory-Count,
                Bracket,
                Price,
                Count*Price Total,
                Traffic.TotalTraffic,
                StatusAfter.Influence,
                Traffic.Ships,
                Traffic.text RawTraffic,
                StatusBefore.text RawStatusBefore,
                StatusAfter.text RawStatusAfter
            FROM (
                -- Get all of the non-OCR details of the transaction, should always exist from EDMC.
                SELECT 
                    *
                FROM (
                    -- Details of the transaction itself
                    SELECT
                        MarketId,
                        Market{transaction_type}.Type Commodity,
                        Count,
                        datetime(timestamp) TransactTime,
                        datetime(timestamp, '{tick_cutoff}') TickCutoff,
                        datetime(timestamp, '+{tick_duration}') TickWindow,
                        datetime(timestamp, '-{tick_duration}') PreviousTickWindow
                    FROM Market{transaction_type}
                    JOIN events ON event_id = events.id
                ) Transact
                JOIN (
                    -- Details of the market performing the transaction, such as demand come from the market event
                    SELECT 
                        MarketId,
                        StarSystem,
                        json_extract(item.value, '$.Name_Localised') Commodity_Localised,
                        replace(lower(json_extract(item.value, '$.Name_Localised')), ' ', '') Commodity,
                        json_extract(item.value,'$.{transaction_type}Price') Price, 
                        json_extract(item.value,'$.{inventory_type}') Inventory, 
                        json_extract(item.value,'$.{inventory_type}Bracket') Bracket, 
                        datetime(timestamp) MarketTime 
                    FROM Market, json_each(Market.Items) item
                    JOIN events ON event_id = events.id
                ) Market
                ON Market.MarketId = Transact.MarketID
                AND Market.Commodity = Transact.Commodity
                AND MarketTime < TransactTime
                JOIN (
                    -- Details about the system population come from an arbitrary jump into the system
                    SELECT
                        Population,
                        StarSystem
                    FROM FSDJump
                ) FSDJump
                ON FSDJump.StarSystem = Market.StarSystem
                JOIN (
                    -- Details about the faction come from the most recent docking event
                    SELECT
                        StationName,
                        StarSystem,
                        json_extract(StationFaction, '$.Name') Faction,
                        MarketId,
                        datetime(timestamp) DockedTime
                    FROM Docked
                    JOIN events ON event_id = events.id
                ) Docked
                ON Docked.MarketId = Market.MarketId
                AND DockedTime < TransactTime
                GROUP BY TransactTime
                HAVING MAX(MarketTime) AND MAX(DockedTime)
            ) Trades
            -- Left join all of the OCR details in case they are missing, show incomplete tests.
            LEFT JOIN (
                SELECT 
                    *
                FROM (
                    -- Details about the traffic in the system during the measured tick
                    SELECT
                        total TotalTraffic, 
                        ships Ships,
                        datetime(timestamp, '{screenshot_fudge}') TrafficTime,
                        replace(text, '\n', '\\n') text
                    FROM DetailedTrafficReport
                    JOIN events ON event_id = events.id
                ) Traffic
                JOIN (
                    SELECT
                        StarSystem,
                        datetime(timestamp) DockedTime
                    FROM Docked
                    JOIN events ON event_id = events.id
                ) Docked
                ON DockedTime < TrafficTime
                GROUP BY TrafficTime
                HAVING MAX(DockedTime)
            ) Traffic
            ON Traffic.StarSystem = Trades.StarSystem
            AND Trades.TickCutoff < TrafficTime
            AND TrafficTime < Trades.TickWindow
            JOIN (
                SELECT
                    StarSystem,
                    faction StatusFaction,
                    influence Influence,
                    DockedTime,
                    datetime(timestamp, '{screenshot_fudge}') StatusBeforeTime,
                    replace(text, '\n', '\\n') text
                FROM LocalFactionStatusSummary
                JOIN events ON event_id = events.id
                JOIN (
                    SELECT
                        StarSystem,
                        datetime(timestamp) DockedTime
                    FROM Docked
                    JOIN events ON event_id = events.id
                ) Docked
                ON DockedTime < StatusBeforeTime
                GROUP BY StatusFaction, StatusBeforeTime
                HAVING MAX(DockedTime)
            ) StatusBefore
            ON StatusBeforeTime < Trades.TickCutoff
            AND Trades.PreviousTickWindow < StatusBeforeTime
            AND StatusBefore.StarSystem = Trades.StarSystem
            AND StatusBefore.StatusFaction = upper(Trades.Faction)
            LEFT JOIN (
                SELECT
                    StarSystem,
                    faction StatusFaction,
                    influence Influence,
                    datetime(timestamp, '{screenshot_fudge}') StatusAfterTime,
                    replace(text, '\n', '\\n') text
                FROM LocalFactionStatusSummary
                JOIN events ON event_id = events.id
                JOIN (
                    SELECT
                        StarSystem,
                        datetime(timestamp) DockedTime
                    FROM Docked
                    JOIN events ON event_id = events.id
                ) Docked
                ON DockedTime < StatusAfterTime
                GROUP BY StatusFaction, StatusAfterTime
                HAVING MAX(DockedTime)
            ) StatusAfter
            ON Trades.TickCutoff < StatusAfterTime
            AND StatusAfterTime < Trades.TickWindow
            AND StatusAfter.StarSystem = Trades.StarSystem
            AND StatusAfter.StatusFaction = upper(Trades.Faction)
            GROUP BY Trades.TransactTime
            HAVING 
                (MIN(TrafficTime) OR TrafficTime IS NULL)
                AND
                (MAX(StatusBeforeTime) OR StatusBeforeTime IS NULL)
                AND
                (MIN(StatusAfterTime) OR StatusAfterTime IS NULL)
            """)
            for r in res:
                writer.writerow(r)


if __name__ == "__main__":
    get_trade_data(DB_PATH)
