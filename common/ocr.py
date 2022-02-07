import concurrent.futures
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from personaldb import StructuredImport, Writer

NEWS_PATH = "/home/greg/ed/news/"
DB_PATH = "/home/greg/ed/save.db"


def _ocr_gocr(input_file, output_file):
    subprocess.run([
        "gocr",
        "-i",
        input_file,
        "-o",
        output_file,
        "-a",
        "99",
    ])


def _ocr_tesseract(input_file, output_file):
    subprocess.run([
        "tesseract",
        "-l",
        "eng",
        input_file,
        output_file[:-4],  # automatically appends it's own .txt
    ])


def _ocr_ocrad(input_file, output_file):
    subprocess.run([
        "ocrad",
        "-o",
        output_file,
        "--charset",
        "ascii",
        "--format",
        "utf8",
        input_file,
    ])


def _crop_news(input_file, output_file):
    subprocess.run([
        "convert",
        input_file,
        "-crop",
        "700x600+920+580",
        "-channel",
        "RGB",
        "-threshold",
        "32%",
        "-set",
        "colorspace",
        "Gray",
        "-separate",
        "-average",
        "-negate",
        output_file,
    ])


def _read_result(input_file):
    with open(input_file, 'r') as file:
        out = "\n".join(file.readlines())
    return out


_OCR_FUNCTIONS = {
    'gocr': _ocr_gocr,
    'tesseract': _ocr_tesseract,
    'ocrad': _ocr_ocrad,
}


class MultithreadOcr:

    def __init__(self, tmp_location):
        self.pool = concurrent.futures.ThreadPoolExecutor()
        self.tmp_dir = Path(tmp_location)
        self.futures = {}

    def _wait_and_submit(self, future, *args):
        def sub_job():
            future.result()
            return args[0](*args[1:])

        return self.pool.submit(sub_job)

    def submit(self, input_file, key):
        input_path = Path(input_file)
        base = input_path.stem
        cropped = str(self.tmp_dir.joinpath(base + ".cropped.png"))
        text = str(self.tmp_dir.joinpath(base + ".txt"))
        crop_future = self.pool.submit(_crop_news, input_file, cropped)
        ocrad_future = self._wait_and_submit(crop_future, _ocr_tesseract, cropped, text)
        read_future = self._wait_and_submit(ocrad_future, _read_result, text)
        self.futures[key] = read_future
        return read_future

    def get_all(self):
        return {k: self.futures[k].result() for k in self.futures}

    def shutdown(self):
        self.pool.shutdown()


def _cleanup_number(fn):
    def cleanup(s, strict):
        subs = s.replace("l", "1").replace("O", "0").replace("I", "1")
        pat = re.compile(r"\d+\.?\d?")
        match = pat.search(subs)
        if match:
            return fn(match.group())
        elif strict:
            raise Exception('Unable to match ' + str(pat) + " against " + subs)
        else:
            return None
    return cleanup


def _extract_ships(string, strict):
    match = re.search("follows:", string)
    if match:
        rows = [s.strip().rsplit('-', 1) for s in string[match.end():].split('\n') if len(s.strip()) != 0]
        return {s.strip(): _cleanup_number(int)(c.strip(), strict) for s, c in rows}
    elif strict:
        raise Exception("Unable to parse ships from " + string)
    else:
        print("Unable to parse ships from " + string)
        return {}


NEWS_REGEXES = {
    re.compile(r"DETAILED\s+TRAFFIC\s+RE[P_]O?RT"): {
        'event': 'DetailedTrafficReport',
        'total': (re.compile(r"(\S+)\s+ships"), _cleanup_number(int)),
        'ships': _extract_ships,
    },
    re.compile(r"STATUS\s+SUMMA[AR]Y"): {
        'event': 'LocalFactionStatusSummary',
        'faction': re.compile(r"^(.+)\s+STATUS\s+SUMMA[AR]Y"),
        'influence': (re.compile(r"in[fr]luence: (\S+)"), _cleanup_number(float))
    },
    re.compile(r"LOCAL\s+BOUNTIES"): {
        'event': 'LocalFactionBounties',
    },
    re.compile(r"LOCAL\s+POWER\s+BOUNTIES"): {
        'event': 'LocalPowerBounties',
    },
    re.compile(r"POWER\s+UPDATE"): {
        'event': 'LocalPowerUpdate',
    },
    re.compile(r"TRADE\s+REPORT"): {
        'event': 'LocalTradeReport',
    },
    re.compile(r"CRIME\s+REPORT"): {
        'event': 'LocalCrimeReport',
    },
    re.compile(r"BOUNTY\s+REPORT"): {
        'event': 'LocalBountyReport',
        'value': (re.compile(r"(\S+)\s+cred"), _cleanup_number(int))
    },
}


def parse_news_string(string, strict):
    # None -> None
    # str -> str
    # re -> re(string)
    # tuple(re, fn) -> fn(re(string))
    # tuple(fn_a, fn_b) -> fn_b(fn_a(string))
    def extract(v):
        if v is None or type(v) == str:
            return v

        def post_process(x, _):
            return x
        if type(v) == tuple:
            post_process = v[1]
            v = v[0]
        if type(v) == re.Pattern:
            match = v.search(string)
            if match:
                str_v = match.group(1)
            elif strict:
                raise Exception("Unable to parse item matching " + str(v) + " from " + json.dumps(string))
            else:
                print("skipping parse of item matching " + str(v) + " from " + json.dumps(string), file=sys.stderr)
                return None
        else:
            str_v = v(string, strict)
        return post_process(str_v, strict)

    for category_regex, parsers in NEWS_REGEXES.items():
        if category_regex.search(string):
            return {k: extract(v) for k, v in parsers.items()}
    return {}


def import_news_results(results, db_path, strict):
    with sqlite3.connect(db_path) as conn:
        writer = Writer(conn, False)
        importer = StructuredImport(writer)
        for k in results:
            ts, i = k
            parsed = parse_news_string(results[k], True)
            event = {
                'timestamp': ts,
                'index': i,
                'text': results[k],
                **parsed
            }
            if 'event' not in event or event['event'] is None:
                if strict:
                    raise Exception("Unable to parse event data from " + json.dumps(results[k]))
                else:
                    print("skipping unknown news item", file=sys.stderr)
                    print(json.dumps(results[k]), file=sys.stderr)
                    continue
            importer.event(event)
        writer.commit()


if __name__ == '__main__':
    ocr = MultithreadOcr("/tmp/news")
    with os.scandir(NEWS_PATH) as files:
        for file_path in files:
            str_epoch, str_index, ignored = file_path.name.split('.')
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(str_epoch)))
            index = int(str_index)
            ocr.submit(file_path, (timestamp, index))

    import_news_results(ocr.get_all(), DB_PATH, False)
    ocr.shutdown()
