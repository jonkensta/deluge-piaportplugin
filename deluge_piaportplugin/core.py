# -*- coding: utf-8 -*-
# Copyright (C) 2019 Jeff Wilson <jeff@jeffalwilson.com>
#
# Basic plugin template created by the Deluge Team.
#
# This file is part of PIAPortPlugin and is licensed under GNU GPL 3.0, or later,
# with the additional special exception to link portions of this program with
# the OpenSSL library. See LICENSE for more details.
from __future__ import unicode_literals

import json
import logging
import sys

import deluge.configmanager
from deluge.core.rpcserver import export
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
from twisted.internet.task import LoopingCall
from twisted.web.client import readBody, Agent
from twisted.internet import reactor

log = logging.getLogger(__name__)

DEFAULT_PREFS = {
    'gluetun_host': 'localhost',
    'gluetun_port': 8000,
    'poll_interval': 300
}


class Core(CorePluginBase):
    def enable(self):
        self.config = deluge.configmanager.ConfigManager(
            'piaportplugin.conf', DEFAULT_PREFS)
        self.check_timer = LoopingCall(self.update_if_blocked)
        self.check_timer = self.check_timer.start(int(self.config['poll_interval']))

    def disable(self):
        if self.check_timer:
            self.check_timer.stop()

    def update(self):
        pass

    def update_if_blocked(self):
        core = component.get("Core")
        log.debug("Current listen port: %d" % core.get_listen_port())
        def update_port(is_open):
            blocked = not is_open
            log.debug("Listen port %d is %s" % (core.get_listen_port(), (blocked and
                        "blocked" or "not blocked")))
            if blocked:
                log.info("Attempting to update listen port")
                d = self._fetch_gluetun_port()
                d.addCallback(self._update_deluge_port, core)
                d.addErrback(self._handle_fetch_error)
                return d

        core.test_listen_port().addCallback(update_port)

    def _fetch_gluetun_port(self):
        """Fetch the forwarded port from gluetun API"""
        host = self.config["gluetun_host"]
        port = int(self.config["gluetun_port"])
        url = "http://%s:%d/v1/portforward" % (host, port)

        log.debug("Fetching port from gluetun at %s" % url)
        agent = Agent(reactor)
        d = agent.request(
            b'GET',
            url.encode('utf-8'),
            None,
            None
        )
        d.addCallback(self._parse_gluetun_response)
        return d

    def _parse_gluetun_response(self, response):
        """Parse the JSON response from gluetun API"""
        if response.code != 200:
            raise Exception("Gluetun API returned status code %d" % response.code)

        d = readBody(response)
        d.addCallback(self._extract_port_from_body)
        return d

    def _extract_port_from_body(self, body):
        """Extract port number from JSON response body"""
        try:
            data = json.loads(body.decode('utf-8'))
            port = int(data.get('port'))
            log.debug("Parsed port from gluetun: %d" % port)
            return port
        except Exception as e:
            raise Exception("Failed to parse gluetun response: %s" % str(e))

    def _update_deluge_port(self, port, core):
        """Update Deluge's listening port"""
        current_port = core.get_listen_port()

        if current_port == port:
            log.warning("Port from gluetun is same as current port: %d" % port)
            return

        log.info("Attempting to update listen port from %d to %d" % (current_port, port))

        try:
            core.set_config({"listen_ports": [port, port]})
            torrents = core.get_session_state()
            core.force_reannounce(torrents)
            log.info("Updated listen port to: %d" % port)
        except Exception as e:
            log.error("Failed to update listen port: %s" % str(e))
            raise

    def _handle_fetch_error(self, failure):
        """Handle errors when fetching port from gluetun"""
        log.error("Failed to fetch port from gluetun: %s" % failure.getErrorMessage())

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        changed = self.config != config
        for key in config:
            self.config[key] = config[key]
        self.config.save()
        if changed:
            self.disable()
            self.enable()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config
