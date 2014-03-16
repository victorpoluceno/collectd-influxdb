PLUGIN = collectd-influxdb.py
PLUGIN_DIR = lib
VERSION := $(shell cat $(PLUGIN_DIR)/$(PLUGIN) | egrep ^'version =' | cut -d ' ' -f 3 | cut -d \" -f 2)
DEST_DIR = /opt/collectd-influxdb-$(VERSION)

install:
	@mkdir -p $(DEST_DIR)/$(PLUGIN_DIR)
	@cp $(PLUGIN_DIR)/$(PLUGIN) $(DEST_DIR)/$(PLUGIN_DIR)
	@echo "Installed collected-influxdb plugin, add this"
	@echo "to your collectd configuration to load this plugin:"
	@echo
	@echo '    <LoadPlugin "python">'
	@echo '        Globals true'
	@echo '    </LoadPlugin>'
	@echo
	@echo '    <Plugin "python">'
	@echo '        # $(PLUGIN) is at $(DEST_DIR)/$(PLUGIN_DIR)/$(PLUGIN)'
	@echo '        ModulePath "$(DEST_DIR)/$(PLUGIN_DIR)"'
	@echo
	@echo '        Import "collectd-influxdb"'
	@echo
	@echo '        <Module "collectd-influxdb">'
	@echo '            Host      "http://localhost:8086"'
	@echo '            User      "root"'
	@echo '            Password  "secret"'
	@echo '            Database  "foo"'
	@echo '        </Module>'
	@echo '    </Plugin>'
