import dht11
from os import wait3
import time
import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD

import logging
logging.basicConfig(filename='../weath.log', filemode='w', format='%(levelname)s - %(asctime)s %(message)s')
logger=logging.getLogger()
logger.setLevel(logging.DEBUG) 

# for NRF
import struct
from RF24 import RF24, RF24_PA_MAX
IRQ_PIN = 17  # pin used for interrupts

# for dht11

# initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

# read data using pin 2
instance = dht11.DHT11(pin=2)
# result = instance.read()

temp_i = 0
hum_i = 0
temp_o = 0
hum_o = 0


def toF(temp_c):
    return (temp_c * (9 / 5)) + 32


def getInfo():
    global temp_i, hum_i
    result = instance.read()
    err_cnt = 0
    while err_cnt < 4:
        time.sleep(2)
        if result.is_valid():
            err_cnt = 0
            temp_c = result.temperature
            hum = result.humidity
            #print("\nT:%f  H:%f" % (temp_c, hum))
            logger.info("GOT INSIDE T:%f  H:%f" % (temp_c, hum))
            temp_i = toF(temp_c)
            hum_i = hum
            break
        else:
            err_cnt += 1
            result = instance.read()
            #print("E%d" % result.error_code, end="")
            logger.error("DHT: %d" % result.error_code)


def updateDisplay():
    global temp_i, hum_i, temp_o, hum_o
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
    # update our end of the deal
    getInfo()
    updateDisplay()
    # wait 5 seconds
    start_timer = time.monotonic()
    #print('wait...')
    while not time.monotonic() - start_timer < 5: # when we have not waited 5 seconds
        pass
    # call this func again
    wait()


def NrfInterrupt(pin):
    '''This is called when we get an interrupt from the NRF module'''
    tx_ds, tx_df, rx_dr = radio.whatHappened()  # update IRQ status flags
    if rx_dr:   # this should be the only thing that happens
        recvLoop()
    else:
        logger.error("Not rx IRQ; tx_ds: {tx_ds}, tx_df: {tx_df}, rx_dr: {rx_dr}")


def recvLoop():
    global temp_o, hum_o
    has_payload, pipe_number = radio.available_pipe()
    if has_payload:
        # fetch 1 payload from RX FIFO
        buffer = radio.read(radio.payloadSize)
        # use struct.unpack() to convert the buffer into usable data
        # expecting a little endian float, thus the format string "<f"
        # buffer[:4] truncates padded 0s in case payloadSize was not set
        payload = []
        payload.append(struct.unpack("<f", buffer[:4])[0])
        payload.append(struct.unpack("<f", buffer[4:9])[
            0])  # get both floats out
        # print details about the received packet
        logger.info("GOT INSIDE T:%f  H:%f" % (payload[0], payload[1]))
        # Write to global variables
        temp_o = toF(payload[0])
        hum_o = payload[1]
        # Update the LCD
        #updateDisplay()

    # recommended behavior is to keep in TX mode while idle
    # radio.stopListening()  # put the radio in TX mode


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
    radio_number = 0  # the arduino is 1
    radio.setPALevel(RF24_PA_MAX)  # RF24_PA_MAX is default

    # set the TX address of the RX node into the TX pipe
    radio.openWritingPipe(address[radio_number])  # always uses pipe 0

    # set the RX address of the TX node into a RX pipe
    radio.openReadingPipe(1, address[not radio_number])  # using pipe 1
    # our payload will be 2 floats(4 bytes)
    radio.payloadSize = 8

    radio.printPrettyDetails()  # debugging
    # SETUP DONE, time to register for data recieved interrupts
    radio.maskIRQ(1, 1, 0)
    #radio.listen = True  # listen for data
    radio.startListening()
    GPIO.setup(IRQ_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(IRQ_PIN, GPIO.FALLING, callback=NrfInterrupt)
    wait()
