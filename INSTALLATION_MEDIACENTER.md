# Installation Guide for Mediacenter Setup

This guide provides step-by-step instructions to install the PIAPortPlugin on your mediacenter Docker setup.

## Prerequisites

- Docker and Docker Compose running your mediacenter services
- Gluetun and Deluge containers (as configured in your docker-compose.yml)
- SSH access to your mediacenter host
- Deluge running and accessible

## Important: Network Configuration Note

Looking at your docker-compose.yml, **Deluge uses `network_mode: "service:gluetun"`**, which means Deluge shares Gluetun's network stack. This is important for the plugin configuration.

## Step 1: Enable Gluetun Control Server

Update your `~/Source/mediacenter/docker-compose.yml` to enable the HTTP control server in the Gluetun service:

```yaml
gluetun:
  image: qmcgaw/gluetun
  container_name: gluetun
  cap_add:
    - NET_ADMIN
  environment:
    - PUID=1012
    - PGID=1012
    - TZ=America/Chicago
    - VPN_SERVICE_PROVIDER=private internet access
    - VPN_TYPE=openvpn
    - OPENVPN_USER=YOUR_VPN_USERNAME
    - OPENVPN_PASSWORD=YOUR_VPN_PASSWORD
    - PORT_FORWARD_ONLY=true
    - VPN_PORT_FORWARDING=on
    - HTTP_CONTROL_SERVER=on  # ADD THIS LINE
    - HTTP_CONTROL_SERVER_ADDRESS=0.0.0.0:8000  # ADD THIS LINE (optional, but recommended for clarity)
  volumes:
    - ./gluetun:/gluetun
  devices:
    - /dev/net/tun:/dev/net/tun
  restart: unless-stopped
```

Then restart Gluetun:

```bash
cd ~/Source/mediacenter
docker-compose restart gluetun
```

## Step 2: Build the Plugin

Navigate to the plugin source directory and build the plugin package:

```bash
cd ~/Source/deluge-piaportplugin
python setup.py bdist_egg
```

This will create an egg file in the `dist/` directory with a name like `PIAPortPlugin-0.2-py3.X.egg`.

## Step 3: Install the Plugin

### Option A: Using Deluge Web UI (Recommended)

1. Open your Deluge web interface (typically at `http://localhost:8112` or the IP of your media center)
2. Go to **Preferences → Plugins → Install**
3. Click the file browser and navigate to the egg file created in Step 2
4. Select the `.egg` file and click **Install**
5. Enable the plugin by checking the box next to "PIAPortPlugin"

### Option B: Manual Installation via Container

1. Copy the egg file to your Deluge config directory:

```bash
cp ~/Source/deluge-piaportplugin/dist/PIAPortPlugin-*.egg \
  ~/Source/mediacenter/deluge/plugins/
```

2. Restart the Deluge container:

```bash
cd ~/Source/mediacenter
docker-compose restart deluge
```

3. Access Deluge web UI and verify the plugin appears in Preferences → Plugins

## Step 4: Configure the Plugin

1. In Deluge web UI, go to **Preferences → Plugins → PIAPortPlugin**
2. Configure the following settings:

   | Setting | Value | Notes |
   |---------|-------|-------|
   | **Gluetun Host** | `localhost` | Since Deluge shares Gluetun's network, use localhost |
   | **Gluetun Port** | `8000` | Default control server port |
   | **Poll Interval** | `300` | Check every 5 minutes (adjust as needed) |

3. Click **Apply** to save the configuration
4. The plugin should now begin monitoring and updating the port

## Step 5: Verify Installation

### Check Plugin Status

1. In Deluge, go to **Preferences → Plugins** and confirm "PIAPortPlugin" is listed and enabled
2. Check the Deluge logs for plugin activity:

```bash
docker logs -f mediacenter_deluge_1 | grep -i "portplugin\|piaport"
```

### Test Port Fetching

Verify that Gluetun's control server is responding:

```bash
# Access the Deluge container's network
docker exec gluetun curl -s http://localhost:8000/v1/portforward | jq .
```

You should see output like:
```json
{
  "port": 12345
}
```

### Monitor Plugin Activity

Watch the Deluge logs for plugin activity:

```bash
docker logs -f mediacenter_deluge_1 | grep -i "port"
```

You should see messages like:
```
Updated listen port to: 12345
```

## Step 6: Docker Compose Updates (Optional but Recommended)

For easier plugin updates and management, you can add a volumes section to mount the plugins directory:

```yaml
deluge:
  image: lscr.io/linuxserver/deluge:latest
  container_name: deluge
  network_mode: "service:gluetun"
  environment:
    - PUID=1012
    - PGID=1012
    - TZ=America/Chicago
    - DELUGE_LOGLEVEL=error
  volumes:
    - ./deluge:/config
    - /mnt/merged/Downloads:/downloads
    - ./deluge/plugins:/config/plugins  # Optional: explicit plugins directory
  restart: unless-stopped
  depends_on:
    - gluetun
```

## Troubleshooting

### Plugin doesn't appear in Preferences

1. Check the Deluge logs for load errors:
   ```bash
   docker logs mediacenter_deluge_1 | grep -i error
   ```

2. Ensure the egg file is in the correct location:
   ```bash
   ls -la ~/Source/mediacenter/deluge/plugins/
   ```

3. Try restarting Deluge:
   ```bash
   docker-compose restart deluge
   ```

### Plugin can't reach Gluetun control server

Since Deluge shares Gluetun's network (`network_mode: "service:gluetun"`), the following should work:

```bash
# Test from Deluge container
docker exec mediacenter_deluge_1 curl -v http://localhost:8000/v1/portforward
```

If this fails:
1. Verify Gluetun is running: `docker ps | grep gluetun`
2. Check Gluetun logs: `docker logs gluetun`
3. Verify HTTP_CONTROL_SERVER=on in gluetun environment

### Port not updating

1. Verify Deluge detects the port as blocked:
   ```bash
   docker logs -f mediacenter_deluge_1 | grep -i "blocked\|listen port"
   ```

2. Check if the port from Gluetun is being fetched correctly:
   ```bash
   docker exec gluetun curl http://localhost:8000/v1/portforward
   ```

3. Check plugin configuration matches your environment (host and port)

### Permission Issues

If you get permission errors when copying files:

```bash
sudo cp ~/Source/deluge-piaportplugin/dist/PIAPortPlugin-*.egg \
  ~/Source/mediacenter/deluge/plugins/
sudo chown 1012:1012 ~/Source/mediacenter/deluge/plugins/PIAPortPlugin-*.egg
```

## Updating the Plugin

To update to a newer version:

1. Pull the latest changes:
   ```bash
   cd ~/Source/deluge-piaportplugin
   git pull origin main
   ```

2. Rebuild the plugin:
   ```bash
   python setup.py bdist_egg
   ```

3. Follow **Step 3** to reinstall the new version

## Notes

- The plugin checks if the current port is blocked and only updates when necessary
- Default poll interval is 300 seconds (5 minutes) - adjust in preferences for more or less frequent checks
- No file mounting or port file is needed anymore
- The control server must be accessible from the Deluge container (which it is, since they share the network stack)

## Support

For issues or questions:

1. Check the Deluge logs: `docker logs mediacenter_deluge_1`
2. Check Gluetun logs: `docker logs gluetun`
3. Review the [Gluetun documentation](https://github.com/qdm12/gluetun-wiki)
4. Open an issue on [GitHub](https://github.com/jonkensta/deluge-piaportplugin)
