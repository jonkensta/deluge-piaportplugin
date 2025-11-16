# deluge-piaportplugin

This is a simple plugin for [Deluge](https://www.deluge-torrent.org/) that's meant to be used with [Gluetun](https://github.com/qdm12/gluetun).

Getting VPN port forwarding set up when using containers can be a pain since the port number is dynamic. This plugin automatically updates the incoming port for Deluge based on the current forwarded port.

## Usage

1. Download a recent version from [releases](https://github.com/jawilson/deluge-piaportplugin/releases).
2. Add to Deluge by going to Preferences -> Plugins -> Install.
3. Enable the Gluetun control server and ensure network connectivity between Deluge and Gluetun containers.

	When using Docker Compose, configure both containers on the same network:

	```yaml
	services:
	  vpn:
	    image: qmcgaw/gluetun:latest
	    ...
	    environment:
	      ...
	      PORT_FORWARDING: 'on'
	      HTTP_CONTROL_SERVER: 'on'
	    networks:
	      - vpn_network

	  deluge:
	    image: ghcr.io/linuxserver/deluge:latest
	    ...
	    depends_on:
	      - vpn
	    networks:
	      - vpn_network

	networks:
	  vpn_network:
	    driver: bridge
	```

4. Configure the plugin in Deluge Preferences -> Plugins -> PIAPortPlugin:
   - **Gluetun Host**: The hostname or IP of your Gluetun container (e.g., `vpn` if using Docker Compose on the same network, or `localhost` if on the host)
   - **Gluetun Port**: The control server port (default: `8000`)
   - **Poll Interval**: How often to check if the port is blocked (in seconds, default: `300`)

5. Make sure you're using a VPN region that supports port forwarding. Here's [a list for PIA](https://www.privateinternetaccess.com/pages/client-support/#portforward).

## Notes

- The plugin fetches the forwarded port from the Gluetun control server API (`GET /v1/portforward`).
- No file mounting or port file is needed anymore.
- The control server must be accessible from the Deluge container.

