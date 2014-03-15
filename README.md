# WARNING: UNDER DEVELOPMENT, NOT WORKING RIGHT NOW

# Introduction

collectd-influxdb is a [collectd](http://www.collectd.org/) plugin that
publishes collectd values to [InfluxDB Time Series 
Database](http://influxdb.org) using the InfluDB HTTP
[API](http://influxdb.org/docs/api/http.html). InfluxDB is a time series,
events, and metrics database.

Collectd-influxdb is a fork of
[collectd-librato](https://github.com/librato/collectd-librato).

# Requirements

* Collectd versions 4.9.5, 4.10.3, and 5.0.0 (or later). Earlier
  versions of 4.9.x and 4.10.x may require a patch to fix the Python
  plugin in collectd (See below).
* Python 2.6 or later.
* An InflxuDB instance (see
  [here](http://influxdb.org/docs/)).

## Troubleshooting
Check the logs: `/var/log/messages` or `/var/log/syslog`, etc.

`Starting collectd5: Could not find plugin rrdtool.`

The collectd daemon has been configured to load the collectd plugin named "rrdtool" but it can't find it.
If you are only sending data to InfluxDB this can be safely ignored and
the `LoadPlugin rrdtool` statement in the collectd configuration can be removed.


```
Unhandled python exception in init callback: Exception: Collectd-InfluxDB.py: ERROR: Unable to open TypesDB file: /usr/share/collectd/types.db.
plugin_dispatch_values: No write callback has been registered. Please load at least one output plugin, if you want the collected data to be stored.
Filter subsystem: Built-in target `write': Dispatching value to all write plugins failed with status 2 (ENOENT). Most likely this means you didn't load any write plugins.
```

The collectd daemon plugin for influxdb could not find a file that it needs.
This file is probably present but in a different location. Try the following:

```
cd /usr/share
ln -s collectd5 collectd
```


## From Source

Installation from source is provided by the Makefile included in the
project. Simply clone this repository and run make install as root:

```
$ git clone git@github.com:victorpoluceno/collectd-influxdb.git
$ cd collectd-influxdb
$ sudo make install
Installed collected-influxdb plugin, add this
to your collectd configuration to load this plugin:

    <LoadPlugin "python">
        Globals true
    </LoadPlugin>

    <Plugin "python">
        # collectd-influxdb.py is at /opt/collectd-influxdb-0.0.1/lib/collectd-influxdb.py
        ModulePath "/opt/collectd-influxdb-0.0.1/lib"

        Import "collectd-influxdb"

        <Module "collectd-influxdb">
            Host      "http://localhost:8086"
            User      "root"
            Password  "secret"
        </Module>
    </Plugin>
```

The output above includes a sample configuration file for the
plugin. Simply add this to `/etc/collectd.conf` or drop in the
configuration directory as `/etc/collectd.d/influxdb.conf` and restart
collectd. See the next section for an explanation of the plugin's
configuration variables.



# Configuration

The plugin requires some configuration. This is done by passing
parameters via the <Module> config section in your Collectd config.

The following parameters are required:

* `Host` - The host of your influxdb instance.

* `User` - The user of your influxdb instance.

* `Password` - The password of your influxdb instance.

The following parameters are optional:

* `TypesDB` - file(s) defining your Collectd types. This should be the
  sames as your TypesDB global config parameters. This will default to
  the file `/usr/share/collectd/types.db`. **NOTE**: This plugin will
  not work if it can't find the types.db file.

* `LowercaseMetricNames` - If preset, all metric names will be converted
  to lower-case (default no lower-casing).

* `MetricPrefix` - If present, all metric names will contain this string
  prefix. Do not include a trailing period or separation character
  (see `MetricSeparator`). Set to the empty string to disable any
  prefix. Defaults to "collectd".

* `MetricSeparator` - String to separate the components of a metric name
  when combining the plugin name, type, and instance name. Defaults to
  a period (".").

* `IncludeSingleValueNames` - Normally, any metric type listed in
  `types.db` that only has a single value will not have the name of
  the value suffixed onto the metric name. For most single value
  metrics the name is simply a placeholder like "value" or "count", so
  adding it to the metric name does not add any particular value. If
  `IncludeSingleValueNames` is set however, these value names will be
  suffixed onto the metric name regardless.

* `FlushIntervalSecs` - This value determines how frequently metrics
  are posted to the InfluxDB HTTP API. This **does not** control how
  frequently metrics are collected; that is controlled by the collectd
  option [`Interval`](http://collectd.org/wiki/index.php/Interval).
  Each interval period that collectd reads metrics, the InfluxDB plugin
  will calculate how long it has been since the last flush to InfluxDB
  API and will POST all collected metrics to InfluxDB if it has
  been longer than `FlushIntervalSecs` seconds.

  Internally there is a hard limit on the maximum number of metrics
  that the plugin will buffer before a flush is forced. This may
  supersede the `FlushIntervalSecs`. The default flush interval is 30
  seconds.

* `Source` - By default the source name is taken from the configured
  collectd hostname. If you want to override the source name that is
  used with InfluxDB you can set the `Source` variable to a
  different source name.

* `IncludeRegex` - This option can be used to control the metrics that
  are sent to InfluxDB. It should be set to a comma-separated
  list of regular expression patterns to match metric names
  against. If a metric name does not match one of the regex's in this
  variable, it will not be sent to InfluxDB. By default, all
  metrics in collectd are sent to InfluxDB. For example, the
  following restricts the set of metrics to CPU and select df metrics:

  `IncludeRegex "collectd.cpu.*,collectd.df.df.dev.free,collectd.df.df.root.free"`

* `FloorTimeSecs` - Set the time interval (in seconds) to floor all
  measurement times to. This will ensure that the real-time samples on
  graphs will align on the time interval boundary across multiple
  collectd hosts. By default, measurement times are not floored and use
  the exact timestamp emitted from collectd. This value should be set
  to the same `Interval` defined in the main *collectd.conf*.

## Example

The following is an example Collectd configuration for this plugin:

    <LoadPlugin "python">
        Globals true
    </LoadPlugin>

    <Plugin "python">
        # collectd-influxdb.py is at /opt/collectd-influxdb-0.0.1/lib/collectd-influxdb.py
        ModulePath "/opt/collectd-influxdb-0.0.1/lib"

        Import "collectd-influxdb"

        <Module "collectd-influxdb">
            Host      "http://localhost:8086"
            User      "root"
            Password  "secret"
        </Module>
    </Plugin>

## Supported Metrics

Collectd-InfluxDB currently supports the following collectd metric
types:

* GAUGE
* COUNTER
* DERIVE

Other metric types are currently ignored. This list will be expanded
in the future.

# Simpler CPU metrics

Collectd's CPU plugin will, by default, break out each CPU's
individual user, system, wait, etc. time as an individual metric. In
total there are eight different CPU times, so for a box with 24 cores
there will be 24 * 8 => 192 metrics published. In most cases you don't
actually need the granularity that the breakout provides, you simply
want to know user time vs. idle time, etc.

With collectd release 5.2 there is now an
[aggregation](https://collectd.org/wiki/index.php/Plugin:Aggregation)
plugin that can aggregate across collectd metrics before they are sent
on to the write plugins (and on to InfluxDB). To use this plugin we
follow the [example
configuration](https://collectd.org/wiki/index.php/Plugin:Aggregation/Config)
for aggregating CPU metrics across a host. Add the following to your
collectd.conf:

```
LoadPlugin aggregation

<Plugin "aggregation">
  <Aggregation>
    Plugin "cpu"
    Type "cpu"

    GroupBy "Host"
    GroupBy "TypeInstance"

    CalculateSum true
    CalculateAverage true
  </Aggregation>
</Plugin>
```

This will compute the sum and average of each CPU timing metric across
all CPUs. The metrics will be sent as:
*collectd.aggregation.cpu-sum.cpu.idle*,
*collectd.aggregation.cpu-sum.cpu.wait*, etc.

Once you have that working, the next step is to drop the breakout CPU
metrics from posting to your account. You can use the collectd
[chains](https://collectd.org/wiki/index.php/Chains) feature to filter
out the CPU metrics by adding the following to your collectd.conf:

```
LoadPlugin match_regex

<Chain "PostCache">
  <Rule "ignore_cpu" > # Send "cpu" values to the aggregation plugin.
    <Match "regex">
      Plugin "^cpu$"
    </Match>
    <Target "write">
      Plugin "aggregation"
    </Target>
    Target stop
  </Rule>
  Target "write"

</Chain>
```

Once you have this setup, create an instrument that stacks the eight
aggregated CPU timing metrics to get a break out of CPU performance:

![CPU Instrument](https://s3.amazonaws.com/librato-mike/images/Selection_238.png)

# Troubleshooting

## Collectd Python Write Callback Bug

Collectd versions through 4.10.2 and 4.9.4 have a bug in the Python
plugin where Python would receive bad values for certain data
sets. The bug would typically manifest as data values appearing to be
0. The *collectd-carbon* author identified the bug and sent a fix to
the Collectd development team.

Collectd versions 4.9.5, 4.10.3, and 5.0.0 are the first official
versions with a fix for this bug. If you are not running one of these
versions or have not applied the fix (which can be seen at
<https://github.com/indygreg/collectd/commit/31bc4bc67f9ae12fb593e18e0d3649e5d4fa13f2>),
you will likely dispatch wrong values to InfluxDB.

## Collectd on Redhat ImportError

Using the plugin with collectd on Redhat-based distributions (RHEL,
CentOS, Fedora) may produce the following error:

    Jul 20 14:54:38 mon0 collectd[2487]: plugin_load_file: The global flag is not supported, libtool 2 is required for this.
    Jul 20 14:54:38 mon0 collectd[2487]: python plugin: Error importing module "collectd_influxdb".
    Jul 20 14:54:38 mon0 collectd[2487]: Unhandled python exception in importing module: ImportError: /usr/lib64/python2.4/lib-dynload/_socketmodule.so: undefined symbol: PyExc_ValueError
    Jul 20 14:54:38 mon0 collectd[2487]: python plugin: Found a configuration for the "collectd_influxdb" plugin, but the plugin isn't loaded or didn't register a configuration callback.
    Jul 20 14:54:38 mon0 collectd[2488]: plugin_dispatch_values: No write callback has been registered. Please load at least one output plugin, if you want the collected data to be stored.
    Jul 20 14:54:38 mon0 collectd[2488]: Filter subsystem: Built-in target `write': Dispatching value to all write plugins failed with status 2 (ENOENT). Most likely this means you didn't load any write plugins.

This may also occur on other operating systems and collectd
versions. It is caused by a libtool/libltdl quirk described in
[this mailing list
thread](http://mailman.verplant.org/pipermail/collectd/2008-March/001616.html).
As per the workarounds detailed there, you may either:

 1. Modify the init script `/etc/init.d/collectd` to preload the
    libpython shared library:

        @@ -25,7 +25,7 @@
                echo -n $"Starting $prog: "
                if [ -r "$CONFIG" ]
                then
        -               daemon /usr/sbin/collectd -C "$CONFIG"
        +               LD_PRELOAD=/usr/lib64/libpython2.4.so daemon /usr/sbin/collectd -C "$CONFIG"
                        RETVAL=$?
                        echo
                        [ $RETVAL -eq 0 ] && touch /var/lock/subsys/$prog

 1. Modify the RPM and rebuild.

        @@ -182,7 +182,7 @@


         %build
        -%configure \
        +%configure CFLAGS=-"DLT_LAZY_OR_NOW='RTLD_LAZY|RTLD_GLOBAL'" \
             --disable-static \
             --disable-ascent \
             --disable-apple_sensors \

# Contributing

If you would like to contribute a fix or feature to this plugin please
feel free to fork this repo, make your change and submit a pull
request!
