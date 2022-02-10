# Send key sequence to attempt docking
import time
import subprocess

from common.ocr import MultithreadOcr, import_news_results

NEWS_PATH = "/home/greg/ed/news/"
DB_PATH = "/home/greg/ed/save.db"


def send_key(keychar):
    print("sending " + keychar)
    keyboard.press_key(keychar)
    time.sleep(0.1)
    keyboard.release_key(keychar)
    time.sleep(0.1)


# Sleep to avoid race condition with background process
time.sleep(0.5)
now = int(time.time())
timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
send_key("<backspace>")
send_key("s")
send_key(" ")
time.sleep(5)
# Main menu, cursor on exit
send_key("d")
# Galnet
ocr = MultithreadOcr("/tmp/news")

for i in range(14):
    # Scroll through news feed and open item
    send_key("s")
    send_key(" ")
    time.sleep(0.3)
    # Take screenshot and post-process
    image_id = str(now) + "." + str(i)
    raw_file = NEWS_PATH + image_id + ".png"
    subprocess.run([
        "/usr/bin/xfce4-screenshooter",
        "--save",
        raw_file,
        "--window"
    ])
    ocr.submit(raw_file, (timestamp, i))
    # Close news feed item
    send_key(" ")
send_key("<backspace>")
try:
    import_news_results(ocr.get_all(), DB_PATH, True)
finally:
    ocr.shutdown()
