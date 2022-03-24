import dht11
import time
import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD

# logging to a file
import logging
logging.basicConfig(filename='/var/log/weath.log', filemode='w', format='%(levelname)s - %(asctime)s %(message)s')
logger=logging.getLogger()
logger.setLevel(logging.DEBUG) 

# for NRF24
import struct
from RF24 import RF24, RF24_PA_MAX
IRQ_PIN = 17  # pin used for interrupts

# initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

# for dht11
# read data using pin 2
instance = dht11.DHT11(pin=2)
# result = instance.read()

# CSV file writing
from os.path import exists
DATA_FILE = "/data/weather.csv"

# The global temperature info
temp_i = 0
hum_i = 0
temp_o = 0
hum_o = 0


def toF(temp_c):
    '''Exactly what it says on the tin'''
    return (temp_c * (9 / 5)) + 32


def getInfo():
    '''Get the information from the local DHT and update the global variables, on RPi DHT fails a lot so we jus keep trying'''
    global temp_i, hum_i
    result = instance.read()
    err_cnt = 0
    while err_cnt < 4:
        if result.is_valid():
            err_cnt = 0
            temp_c = result.temperature
            hum = result.humidity
            #print("\nT:%f  H:%f" % (temp_c, hum))
            logger.info("INSIDE T:%f  H:%f" % (temp_c, hum))
            temp_i = toF(temp_c)
            hum_i = hum
            return
        else:
            # wait 2s and Keep trying
            time.sleep(2)
            err_cnt += 1
            result = instance.read()
            #logger.error("DHT: %d" % result.error_code) # errors happen so often no need to log them


def writeCSV():
    '''Write the newest temperatures to a csv with the time'''
    global temp_i, hum_i, temp_o, hum_o
    if (not exists(DATA_FILE)): # if the file does not exist add it with the correct headers
        with open(DATA_FILE, "w") as f:
            f.write("time, temp_i, hum_i, temp_o, hum_o\n")
    else:
        with open(DATA_FILE, "a") as f:
            f.write(F"{time.time()}, {round(temp_i, 1)}, {hum_i}, {round(temp_o, 1)}, {hum_o}\n")        
    f.close()




def updateDisplay():
    '''Take the global weather var information and push it to the LCD'''
    global temp_i, hum_i, temp_o, hum_o
    #lcd.clear()
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
    '''This will run every 60 seconds and updates the inside temperature as well as pushing the info to the display and CSVs'''
    getInfo()
    updateDisplay()
    writeCSV()
    # wait 60 seconds
    time.sleep(60)
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
    '''This name is old, but all this function does is read a payload form the RF24 buffer and update the global variables'''
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
        logger.info("OUTSIDE T:%f  H:%f" % (payload[0], payload[1]))
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
    #time.sleep(1)

    ###################### NRF24 ############################################
    # initialize the nRF24L01 on the spi bus 0
    radio = RF24(22, 0)
    if not radio.begin():
        lcd.write_string("Radio not responding...")
        raise RuntimeError("radio hardware is not responding")
    # radio configs, TODO: clean up unnecessary ones
    # Addresses for tx from arduino (rx for ACK)
    address = [b"1Node", b"2Node"]
    # It is very helpful to think of an address as a path instead of as
    # an identifying device destination
    radio_number = 0  # the arduino is 1, means we use the first address to send and rx on 2nd
    radio.setPALevel(RF24_PA_MAX)

    # set the TX address of the RX node into the TX pipe
    radio.openWritingPipe(address[radio_number])  # always uses pipe 0

    # set the RX address of the TX node into a RX pipe
    radio.openReadingPipe(1, address[not radio_number])  # using pipe 1
    # our payload will be 2 floats(4 bytes * 2 = 8)
    radio.payloadSize = 8

    #radio.printPrettyDetails()  # debugging
    # SETUP DONE, time to register for data recieved interrupts
    radio.maskIRQ(1, 1, 0) # only wand IRQ on rx
    radio.startListening()
    GPIO.setup(IRQ_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(IRQ_PIN, GPIO.FALLING, callback=NrfInterrupt)
    wait()
