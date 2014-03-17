# Copyright 2014 Victor Godoy Poluceno.
# Copyright 2011 Librato, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import collectd
import json
import urllib2
import time
import os
import sys
import math
import re
from string import maketrans
from copy import copy

# NOTE: This version is grepped from the Makefile, so don't change the
# format of this line.
version = "0.0.1"

config = {'types_db': '/usr/share/collectd/types.db',
          'metric_prefix': 'collectd',
          'metric_separator': '.',
          'source': None,
          'flush_interval_secs': 30,
          'flush_max_measurements': 600,
          'flush_timeout_secs': 15,
          'lower_case': False,
          'single_value_names': False}
plugin_name = 'Collectd-InfluxDB.py'
types = {}


def str_to_num(s):
    """
    Convert type limits from strings to floats for arithmetic.
    """

    return float(s)


def get_time():
    """
    Return the current time as epoch seconds.
    """

    return int(time.mktime(time.localtime()))


def sanitize_field(field):
    """
    Santize Metric Fields: delete paranthesis and split on periods
    """
    field = field.strip()

    # convert spaces to underscores
    trans = maketrans(' ', '_')

    # Strip ()
    field = field.translate(trans, '()')

    # Split based on periods
    return field.split(".")


#
# Parse the types.db(5) file to determine metric types.
#
def influxdb_parse_types_file(path):
    global types

    f = open(path, 'r')

    for line in f:
        fields = line.split()
        if len(fields) < 2:
            continue

        type_name = fields[0]

        if type_name[0] == '#':
            continue

        v = []
        for ds in fields[1:]:
            ds = ds.rstrip(',')
            ds_fields = ds.split(':')

            if len(ds_fields) != 4:
                collectd.warning('%s: cannot parse data source '
                                 '%s on type %s' %
                                 (plugin_name, ds, type_name))
                continue

            v.append(ds_fields)

        types[type_name] = v

    f.close()


def build_user_agent():
    try:
        uname = os.uname()
        system = "; ".join([uname[0], uname[4]])
    except:
        system = os.name()

    pver = sys.version_info
    user_agent = '%s/%s (%s) Python-Urllib2/%d.%d' % \
                 (plugin_name, version, system, pver[0], pver[1])
    return user_agent


def influxdb_config(c):
    global config

    for child in c.children:
        val = child.values[0]

        if child.key == 'Host':
            config['host'] = val
        elif child.key == 'User':
            config['user'] = val
        elif child.key == 'Password':
            config['password'] = val
        elif child.key == 'Database':
            config['database'] = val
        elif child.key == 'MetricPrefix':
            config['metric_prefix'] = val
        elif child.key == 'TypesDB':
            config['types_db'] = val
        elif child.key == 'MetricPrefix':
            config['metric_prefix'] = val
        elif child.key == 'MetricSeparator':
            config['metric_separator'] = val
        elif child.key == 'LowercaseMetricNames':
            config['lower_case'] = True
        elif child.key == 'IncludeSingleValueNames':
            config['single_value_names'] = True
        elif child.key == 'FloorTimeSecs':
            config['floor_time_secs'] = int(val)
        elif child.key == 'Source':
            config['source'] = val
        elif child.key == 'IncludeRegex':
            config['include_regex'] = val.split(',') if val else []
        elif child.key == 'FlushIntervalSecs':
            try:
                config['flush_interval_secs'] = int(str_to_num(val))
            except:
                msg = '%s: Invalid value for FlushIntervalSecs: %s' % \
                    (plugin_name, val)
                raise Exception(msg)

    if not 'host' in config:
        raise Exception('Host not defined')

    if not 'user' in config:
        raise Exception('User not defined')

    if not 'password' in config:
        raise Exception('Password not defined')

    if not 'database' in config:
        raise Exception('Database not defined')

    config['user_agent'] = build_user_agent()


def influxdb_flush_metrics(series, data):
    """
    POST a collection of gauges and counters to influxdb Metrics.
    """

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': config['user_agent']}

    pack = []
    for k, v in series.items():
        pack.append({'name': k, 'columns': ['time', 'value'], 'points': v})

    body = json.dumps(pack)

    url = "%s/db/%s/series?u=%s&p=%s&time_precision=s" %\
        (config['host'], config['database'],
         config['user'], config['password'])
    req = urllib2.Request(url, body, headers)
    try:
        f = urllib2.urlopen(req, timeout=config['flush_timeout_secs'])
        f.read()
        f.close()
    except urllib2.HTTPError as error:
        body = error.read()
        collectd.warning('%s: Failed to send metrics to influxdb: Code: %d. '
                         'Response: %s' % (plugin_name, error.code, body))
    except IOError as error:
        collectd.warning('%s: Error when sending metrics influxdb (%s)' %
                         (plugin_name, error.reason))


def influxdb_queue_measurements(series, data):
    # Updating shared data structures
    #
    data['lock'].acquire()

    for k, v in series.items():
        if k in data['series']:
            data['series'][k].extend(v)
        else:
            data['series'][k] = v

    curr_time = get_time()
    last_flush = curr_time - data['last_flush_time']
    length = sum([len(v) for k, v in data['series'].items()])

    if (last_flush < config['flush_interval_secs'] and
        length < config['flush_max_measurements']) or \
            length == 0:
        data['lock'].release()
        return

    flush_series = data['series']
    data['series'] = {}
    data['last_flush_time'] = curr_time
    data['lock'].release()

    influxdb_flush_metrics(flush_series, data)


def influxdb_write(v, data=None):
    global plugin_name, types, config

    if v.type not in types:
        collectd.warning('%s: do not know how to handle type %s. '
                         'do you have all your types.db files configured?' %
                         (plugin_name, v.type))
        return

    v_type = types[v.type]

    if len(v_type) != len(v.values):
        collectd.warning('%s: differing number of values for type %s' %
                         (plugin_name, v.type))
        return

    name = []

    if len(config['metric_prefix']) > 0:
        name.append(config['metric_prefix'])

    name.append(v.plugin)
    if v.plugin_instance:
        name.extend(sanitize_field(v.plugin_instance))

    name.append(v.type)
    if v.type_instance:
        name.extend(sanitize_field(v.type_instance))

    series = {}

    srcname = config['source']
    if srcname is None:
        srcname = v.host

    for i in range(len(v.values)):
        value = v.values[i]
        ds_name = v_type[i][0]
        ds_type = v_type[i][1]

        # We only support Gauges, Counters and Derives at this time
        if ds_type != 'GAUGE' and ds_type != 'COUNTER' and \
                ds_type != 'DERIVE':
            continue

        # Can value be None?
        if value is None:
            continue

        # Skip NaN values. These can be emitted from plugins like `tail`
        # when there are no matches.
        if math.isnan(value):
            continue

        # Skip counter values that are negative.
        if ds_type != 'GAUGE' and value < 0:
            continue

        name_tuple = copy(name)
        if len(v.values) > 1 or config['single_value_names']:
            name_tuple.append(ds_name)

        metric_name = config['metric_separator'].join(name_tuple)
        if config['lower_case']:
            metric_name = metric_name.lower()

        regexs = config.get('include_regex', [])
        matches = len(regexs) == 0
        for regex in regexs:
            if re.match(regex, metric_name):
                matches = True
                break

        if not matches:
            continue

        # Floor measure time?
        m_time = int(v.time)
        if 'floor_time_secs' in config:
            m_time /= config['floor_time_secs']
            m_time *= config['floor_time_secs']

        if metric_name in series:
            series[metric_name].append((m_time, value))
        else:
            series[metric_name] = [(m_time, value)]

    influxdb_queue_measurements(series, data)


def influxdb_init():
    import threading

    try:
        influxdb_parse_types_file(config['types_db'])
    except:
        msg = '%s: ERROR: Unable to open TypesDB file: %s.' % \
              (plugin_name, config['types_db'])
        raise Exception(msg)

    d = {'lock': threading.Lock(),
         'last_flush_time': get_time(),
         'series': {}}

    collectd.register_write(influxdb_write, data=d)

collectd.register_config(influxdb_config)
collectd.register_init(influxdb_init)
