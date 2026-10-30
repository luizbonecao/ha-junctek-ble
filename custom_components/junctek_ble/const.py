"""Constants for the Junctek KG-F Bluetooth integration."""

DOMAIN = "junctek_ble"

CONF_CAPACITY_AH = "capacity_ah"
DEFAULT_CAPACITY_AH = 100

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Bluetooth names used by the Junctek KG-F Bluetooth modules
NAME_PREFIXES = ("BTG", "KG")

MANUFACTURER = "Junctek"
MODEL = "KG-F (Bluetooth)"

# Seconds to wait before trying to connect again after a failure
RECONNECT_DELAY = 10
# The monitor sends several frames per second; publish at most this often
PUBLISH_INTERVAL = 1.0
