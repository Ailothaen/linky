#!/usr/bin/python3

# stdlib
import datetime, time, logging

# Self libraries
import linky


# ----------------------------- #
# Setup                         #
# ----------------------------- #

log = logging.getLogger('linky')

log.debug('Loading config...')
config = linky.load_config()
log.debug(f'Config loaded! Values: {config}')

terminal = linky.setup_serial(config['device']['file'])

# Trying to connect to db server and creating schema if not exists
linky.test_db_connection(config['database']['server'], config['database']['user'], config['database']['password'], config['database']['name'])


# ----------------------------- #
# Main loop                     #
# ----------------------------- #

current_loop_day = datetime.datetime.now(datetime.timezone.utc).day
previous_loop_day = datetime.datetime.now(datetime.timezone.utc).day

while True:
    log.debug("Cycle begins")
    data_BASE = None
    data_PAPP = None
    current_loop_day = datetime.datetime.now(datetime.timezone.utc).day

    # Now beginning to read data from Linky
    log.debug("Opening terminal...")
    terminal.open()

    # reading continously output until we have data that interests us
    while True:
        line = terminal.readline().decode('ascii')
        log.debug(f"Current line: {line}")

        if line.startswith('BASE'):
            data_BASE = int(line.split(' ')[1])
        if line.startswith('PAPP'):
            data_PAPP = int(line.split(' ')[1])

        # We have BASE and PAPP, we can now close the connection
        if data_BASE and data_PAPP:
            log.debug(f"Output parsed: BASE={data_BASE}, PAPP={data_PAPP}. Closing terminal.")
            terminal.close()
            break
    
    # Connecting to database
    log.debug("Connecting to database")
    db, cr = linky.open_db(config['database']['server'], config['database']['user'], config['database']['password'], config['database']['name'])

    # first record of the day? generating dailies
    if current_loop_day != previous_loop_day:
        log.debug(f"First record of the day! Inserting dailies record.")
        linky.insert_dailies(db, cr, data_BASE)
    previous_loop_day = datetime.datetime.utcnow().day

    # inserting values
    log.debug("Inserting stream record")
    linky.insert_stream(db, cr, data_BASE, data_PAPP)

    log.debug("Cycle ends, sleeping for 60 seconds")
    time.sleep(60)
