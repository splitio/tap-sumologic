"""
Tap configuration related stuff
"""
from voluptuous import Schema, Required, Optional

CONFIG_CONTRACT = Schema([{
    Required('table_name'): str,
    Required('query'): str,
    Optional('max_lookback_days'): int,
    Optional('time_property'): str,
    Optional('exclude_properties'): [str]
}])
