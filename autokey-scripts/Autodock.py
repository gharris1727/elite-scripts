# Send key sequence to attempt docking
import time


def send_key(keychar):
    print("sending " + keychar)
    keyboard.press_key(keychar)
    time.sleep(0.1)
    keyboard.release_key(keychar)
    time.sleep(0.1)


# Sleep to avoid race condition with background process
time.sleep(0.5)
send_key("i")
send_key("x")
send_key("<backspace>")
send_key("1")
time.sleep(0.5)
send_key("q")
send_key(" ")
time.sleep(0.5)
send_key("d")
send_key(" ")
send_key("e")
send_key("<backspace>")
