#!/usr/bin/env python3

import sqlite3

DB_PATH = "/home/greg/ed/save.db"


def dump_res(res):
    if res:
        print([col[0] for col in res.description])
        for r in res:
            print(r)
    else:
        print("no results")


class Reader:
    def __init__(self, conn):
        self.conn = conn

    def rank_by_col(self, table, sort_column, sort_type, display_columns):
        res = self.execute(
            "SELECT %s FROM %s WHERE %s IS NOT NULL ORDER BY %s %s LIMIT 3" % (
                ",".join(display_columns),
                table,
                sort_column,
                sort_column,
                sort_type
            )
        )
        print("%s by %s %s" % (table, sort_column, sort_type))
        dump_res(res)

    MATERIAL_QUERY = """
        SELECT 
            Scan.BodyName body, 
            Scan.PlanetClass class, 
            json_extract(materials.value, '$.Name') material,
            json_extract(materials.value, '$.Percent') percent,
            json_extract(signals.value, '$.Type_Localised') signal_type,
            json_extract(signals.value, '$.Count') signal_count
        FROM 
            Scan, json_each(Scan.Materials) materials 
        JOIN 
            SAASignalsFound, json_each(SAASignalsFound.Signals) signals 
            ON Scan.BodyName = SAASignalsFound.BodyName
        WHERE (signal_type = 'Geological' OR signal_type = 'Biological')
        GROUP BY body, material
    """

    def all_best_materials(self):
        res = self.execute("SELECT * FROM ( %s ) GROUP BY material" % self.MATERIAL_QUERY)
        for material in [r[2] for r in res]:
            sql = """
            SELECT * FROM ( %s )
            WHERE material = ?
            ORDER BY percent DESC
            LIMIT 20
            """
            res = self.execute(sql % self.MATERIAL_QUERY, [material])
            print("best locations for %s" % material)
            dump_res(res)

    def all_body_rankings(self, table, sort_columns, always_display_columns):
        for sort_column in sort_columns:
            display_columns = []
            display_columns.extend(always_display_columns)
            display_columns.append(sort_column)
            self.rank_by_col(table, sort_column, "ASC", display_columns)
            self.rank_by_col(table, sort_column, "DESC", display_columns)

    def execute(self, sql, *values):
        return self.conn.execute(sql, *values)


def summarize_bodies(db_path):
    with sqlite3.connect(db_path) as conn:
        reader = Reader(conn)
        reader.all_body_rankings(
            "Scan", [
                "DistanceFromArrivalLS", "StellarMass", "Radius",
                "AbsoluteMagnitude", "Age_MY", "SurfaceTemperature", "Luminosity",
                "SemiMajorAxis",
                "Eccentricity", "OrbitalInclination", "Periapsis", "OrbitalPeriod",
                "RotationPeriod",
                "AxialTilt", "SurfacePressure", "SurfaceGravity", "MassEM"
            ],
            [
                "BodyName", "WasDiscovered", "WasMapped", "PlanetClass"
             ])
        reader.all_best_materials()


summarize_bodies(DB_PATH)
