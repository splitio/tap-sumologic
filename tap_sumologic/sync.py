"""
Syncing related functions
"""

import sys
from typing import Dict, List
from singer import metadata, get_logger, Transformer, utils, get_bookmark, write_bookmark, write_state, write_record
from tap_sumologic import sumologic
from datetime import datetime
from dateutil.relativedelta import *

LOGGER = get_logger()


def sync_stream(config: Dict, state: Dict, table_spec: Dict, stream: Dict) -> int:
    """
    Sync the stream
    :param config: Connection and stream config
    :param state: current state
    :param table_spec: table specs
    :param stream: stream
    :return: count of streamed records
    """
    table_name = table_spec['table_name']
    modified_since = get_bookmark(state, table_name, 'modified_since') or config['start_date']

    LOGGER.info('Syncing table "%s".', table_name)
    LOGGER.info('Getting records since %s.', modified_since)

    q = table_spec.get('query')
    # go as far as 89 days (three months) but no further
    max_lookback_date = (datetime.utcnow() + relativedelta(days=-7)).strftime('%Y-%m-%dT%H:%M:%S')
    from_time = modified_since if modified_since > max_lookback_date else max_lookback_date
    # we stop at 5 minutes ago because data may not all be there yet in Sumo
    # if we do real time we would have gaps of data for the data that comes in later.
    end_time = datetime.utcnow() + relativedelta(minutes=-5) 
    to_time = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    time_zone = 'UTC'

    records_streamed = 0

    LOGGER.info('Syncing query "%s".', q)

    # TODO need to get a pointer back to loop through records if more than one page
    records = sumologic.get_sumologic_records(config, q, from_time, to_time, time_zone, limit=1000000)

    records_synced = 0

    for record in records:
        with Transformer() as transformer:
            to_write = transformer.transform(record, stream['schema'], metadata.to_map(stream['metadata']))

        write_record(table_name, to_write)
        records_synced += 1

    state = write_bookmark(state, table_name, 'modified_since', end_time.isoformat())
    write_state(state)

    LOGGER.info('Wrote %s records for table "%s".', records_synced, table_name)

    return records_streamed

