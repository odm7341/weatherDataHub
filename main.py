import time
import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD
# for NRF
import struct
from RF24 import RF24, RF24_PA_MAX
# for dht11
import RPi.GPIO as GPIO
import dht11

# initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

# read data using pin 2
instance = dht11.DHT11(pin=2)
# result = instance.read()

temp_c = 0
hum = 0

def toF(temp_c):
    return (temp_c * (9 / 5)) + 32

def getInfo():
    result = instance.read()
    global temp_c, hum
    err_cnt = 0
    while err_cnt < 4:
        if result.is_valid():
            err_cnt = 0
            temp_c = result.temperature
            hum = result.humidity
            print("\nT:%f  H:%f" % (temp_c, hum))
            break
        else:
            err_cnt += 1
            time.sleep(5)
            result = instance.read()
            print("E%d" % result.error_code, end = "")
    temp = toF(temp_c)
    return temp, hum


def showInfo(temp_i, hum_i, temp_o, hum_o):

    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string("INSIDE Temp: " + str(round(temp_i, 1)) + chr(223) + "F")
    lcd.cursor_pos = (1, 0)
    lcd.write_string("Humidity: " + str(hum_i) + "%")
    lcd.cursor_pos = (2, 0)
    lcd.write_string("OUTSIDE Temp: " + str(round(temp_o, 1)) + chr(223) + "F")
    lcd.cursor_pos = (3, 0)
    lcd.write_string("Humidity: " + str(hum_o) + "%")
    return


def wait():
    for i in range(20):
        lcd.cursor_pos = (0, i)
        lcd.write_string("#")
        time.sleep(2)
    return

def recvLoop():
    radio.startListening()  # put radio in RX mode

    start_timer = time.monotonic()
    while (1):                                            # YEP for now ill do an infinate loop
        has_payload, pipe_number = radio.available_pipe()
        if has_payload:
            # fetch 1 payload from RX FIFO
            buffer = radio.read(radio.payloadSize)
            # use struct.unpack() to convert the buffer into usable data
            # expecting a little endian float, thus the format string "<f"
            # buffer[:4] truncates padded 0s in case payloadSize was not set
            payload = []
            payload.append(struct.unpack("<f", buffer[:4])[0])
            payload.append(struct.unpack("<f", buffer[4:9])[0]) # get both floats out
            # print details about the received packet
            print(
                "Received {} bytes on pipe {}: {}".format(
                    radio.payloadSize,
                    pipe_number,
                    payload
                )
            )
            # get our own tmperature
            t_i, h_i = getInfo()
            # and write both to the LCD
            showInfo(t_i, h_i, toF(payload[0]), payload[1])




    # recommended behavior is to keep in TX mode while idle
    radio.stopListening()  # put the radio in TX mode



if __name__ == "__main__":

    ####################################### LCD #################################
    lcd = CharLCD(
        pin_rs=4,
        pin_e=15,
        pins_data=[18, 23, 24, 25],
        numbering_mode=GPIO.BCM,
        cols=20,
        rows=4,
        dotsize=8,
        charmap="A02",
        auto_linebreaks=True,
    )
    lcd.clear()
    lcd.write_string("Starting Up...")
    time.sleep(1)

    ###################### NRF24 ############################################
    # initialize the nRF24L01 on the spi bus
    radio = RF24(22, 0)
    if not radio.begin():
        lcd.write_string("Radio not responding...")
        raise RuntimeError("radio hardware is not responding")
    # radio configs, TODO: clean up unnecessary ones
    # An address need to be a buffer protocol object (bytearray)
    address = [b"1Node", b"2Node"]
    # It is very helpful to think of an address as a path instead of as
    # an identifying device destination
    radio_number = 0 # the arduino is 1
    radio.setPALevel(RF24_PA_MAX)  # RF24_PA_MAX is default

    # set the TX address of the RX node into the TX pipe
    radio.openWritingPipe(address[radio_number])  # always uses pipe 0

    # set the RX address of the TX node into a RX pipe
    radio.openReadingPipe(1, address[not radio_number])  # using pipe 1
    # our payload will be 2 floats(4 bytes)
    radio.payloadSize = 8

    radio.printPrettyDetails() #debugging
    ## DONE, time to start the recieve loop
    recvLoop()
