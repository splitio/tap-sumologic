"""
Tap configuration related stuff
"""
from voluptuous import Schema, Required, Optional

CONFIG_CONTRACT = Schema([{
    Required('table_name'): str,
    Required('query'): str,
    Optional('bookmark_property'): [str],
    Optional('exclude_properties'): [str]
}])
