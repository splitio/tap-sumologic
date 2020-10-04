"""
Modules containing all Sumologic related features
"""
from typing import List, Dict

import backoff
import singer
import requests
from datetime import datetime
import time
from dateutil.relativedelta import *

from sumologic import SumoLogic

LOGGER = singer.get_logger()
RECORD_FETCHING_LIMIT = 10000

def retry_pattern():
    """
    Retry decorator to retry failed functions
    :return:
    """
    return backoff.on_exception(backoff.expo,
                                requests.HTTPError,
                                max_tries=5,
                                on_backoff=log_backoff_attempt,
                                factor=10)


def log_backoff_attempt(details):
    """
    For logging attempts to connect with Amazon
    :param details:
    :return:
    """
    LOGGER.info("Error detected communicating with Sumologic, triggering backoff: %d try", details.get("tries"))


@retry_pattern()
def get_schema_for_table(config: Dict, table_spec: Dict) -> Dict:
    """
    Detects json schema using a record set of query
    :param config: Tap config
    :param table_spec: tables specs
    :return: detected schema
    """
    schema = {}
    LOGGER.info('Getting records for query to determine table schema.')

    q = table_spec.get('query') # TODO get query from config
    from_time = (datetime.utcnow() + relativedelta(minutes=-15)).strftime('%Y-%m-%dT%H:%M:%S')
    to_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    time_zone = 'UTC'

    fields = get_sumologic_fields(config, q, from_time, to_time, time_zone)

    key_properties = []
    for field in fields:
        field_name = field['name']
        field_type = field['fieldType']
        key_field = field['keyField']

        schema[field_name] = {
            'type': ['null', 'string']
        }

        if field_type == 'int':
            schema[field_name]['type'].append('integer')
        elif field_type == 'long':
            schema[field_name]['type'].append('integer')
        elif field_type == 'double':
            schema[field_name]['type'].append('number')
        elif field_type == 'boolean':
            schema[field_name]['type'].append('boolean')

        if key_field:
            key_properties.append(field_name)

    return {
        'type': 'object',
        'properties': schema,
        'key_properties': key_properties
    }

def get_sumologic_fields(config, q, from_time, to_time, time_zone):
    fields = []

    sumologic_access_id = config['sumologic_access_id']
    sumologic_access_key = config['sumologic_access_key']
    sumologic_root_url = config['sumologic_root_url']

    LOGGER.info("Run query in sumologic")
    sumo = SumoLogic(sumologic_access_id, sumologic_access_key, sumologic_root_url)

    delay = 5
    search_job = sumo.search_job(q, from_time, to_time, time_zone)

    status = sumo.search_job_status(search_job)
    while status['state'] != 'DONE GATHERING RESULTS':
        if status['state'] == 'CANCELLED':
            break
        time.sleep(delay)
        status = sumo.search_job_status(search_job)

    LOGGER.info(status['state'])

    if status['state'] == 'DONE GATHERING RESULTS':
        response = sumo.search_job_records(search_job, limit=1)

        fields = response['fields']

    return fields

def get_sumologic_records(config, q, from_time, to_time, time_zone, limit):
    records = []

    sumologic_access_id = config['sumologic_access_id']
    sumologic_access_key = config['sumologic_access_key']
    sumologic_root_url = config['sumologic_root_url']

    LOGGER.info("Run query in sumologic")
    sumo = SumoLogic(sumologic_access_id, sumologic_access_key, sumologic_root_url)

    now_datetime = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    custom_columns = {
        '_SDC_EXTRACTED_AT': now_datetime,
        '_SDC_BATCHED_AT': now_datetime,
        '_SDC_DELETED_AT': None
    }
    delay = 5
    search_job = sumo.search_job(q, from_time, to_time, time_zone)
    LOGGER.info(search_job)

    status = sumo.search_job_status(search_job)
    while status['state'] != 'DONE GATHERING RESULTS':
        if status['state'] == 'CANCELLED':
            break
        time.sleep(delay)
        LOGGER.info(":check query status")
        status = sumo.search_job_status(search_job)
        LOGGER.info(status)

    LOGGER.info(status['state'])

    if status['state'] == 'DONE GATHERING RESULTS':
        record_count = status['recordCount']
        count = 0
        while count < record_count:
            LOGGER.info("Get records %d of %d, limit=%d", count, record_count, limit)
            response = sumo.search_job_records(search_job, limit=limit, offset = count)
            LOGGER.info("Got records %d of %d", count, record_count)

            recs = response['records']
            # extract the result maps to put them in the list of records
            for rec in recs:
                records.append({**rec['map'], **custom_columns})

            if len(recs) > 0:
                count = count + len(recs)
            else:
                break # make sure we exit if nothing comes back

    return records
