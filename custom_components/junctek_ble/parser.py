"""Decoder for the Junctek KG-F Bluetooth protocol (BTG166 module).

Frames look like ``BB <BCD digits><tag> <BCD digits><tag> ... EE``.
Each byte whose two nibbles are 0-9 is a pair of decimal digits; the first
byte that is not BCD is a *tag* that closes the number before it and tells
what the number means. The monitor only sends fields that changed, so the
parser keeps the last known value of every field.

This module has no Home Assistant imports so it can be unit tested alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

FRAME_START = 0xBB
FRAME_END = 0xEE

TAG_VOLTAGE = 0xC0  # V * 100
TAG_CURRENT = 0xC1  # A * 100, always positive
TAG_DIRECTION = 0xD1  # 1 = charging
TAG_REMAINING_AH = 0xD2  # Ah * 1000
TAG_DISCHARGED_AH = 0xD3  # Ah * 1000, counter
TAG_CHARGED_AH = 0xD4  # Ah * 1000, counter
TAG_MINUTES_LEFT = 0xD6  # minutes
TAG_POWER = 0xD8  # W * 100, always positive
TAG_TEMPERATURE = 0xD9  # degC + 100

IDLE_CURRENT = 0.05  # A; below this the battery is considered idle


@dataclass
class JunctekState:
    """Last known values reported by the monitor."""

    voltage: float | None = None
    current_abs: float | None = None
    power_abs: float | None = None
    charging: bool | None = None  # None until the monitor tells the direction
    remaining_ah: float | None = None
    discharged_ah: float | None = None
    charged_ah: float | None = None
    minutes_left: float | None = None
    temperature: float | None = None
    capacity_ah: float = 100.0
    extra: dict[int, float] = field(default_factory=dict)

    @property
    def current(self) -> float | None:
        """Signed current: positive charging, negative discharging."""
        if self.current_abs is None:
            return None
        if self.current_abs < IDLE_CURRENT:
            return 0.0
        if self.charging is None:
            return None
        return self.current_abs if self.charging else -self.current_abs

    @property
    def power(self) -> float | None:
        """Signed power: positive charging, negative discharging."""
        if self.power_abs is None:
            return None
        if self.current_abs is not None and self.current_abs < IDLE_CURRENT:
            return 0.0
        if self.charging is None:
            return None
        return self.power_abs if self.charging else -self.power_abs

    @property
    def soc(self) -> float | None:
        """State of charge in percent, from remaining Ah and capacity."""
        if self.remaining_ah is None or self.capacity_ah <= 0:
            return None
        return max(0.0, min(100.0, self.remaining_ah * 100.0 / self.capacity_ah))

    @property
    def status(self) -> str | None:
        """charging / discharging / idle."""
        if self.current_abs is None:
            return None
        if self.current_abs < IDLE_CURRENT:
            return "idle"
        if self.charging is None:
            return None
        return "charging" if self.charging else "discharging"

    def as_dict(self) -> dict[str, float | str | None]:
        """Values exposed to the sensors."""
        return {
            "voltage": self.voltage,
            "current": self.current,
            "power": self.power,
            "soc": self.soc,
            "remaining_ah": self.remaining_ah,
            "discharged_ah": self.discharged_ah,
            "charged_ah": self.charged_ah,
            "time_left": self.minutes_left,
            "temperature": self.temperature,
            "status": self.status,
        }


class JunctekParser:
    """Stateful stream decoder. Feed it every notification payload."""

    def __init__(self, capacity_ah: float = 100.0) -> None:
        self.state = JunctekState(capacity_ah=capacity_ah)
        self._inside = False
        self._digits = ""

    def reset_stream(self) -> None:
        """Forget a half-received frame (call after a reconnect)."""
        self._inside = False
        self._digits = ""

    def feed(self, data: bytes | bytearray) -> bool:
        """Decode a chunk. Returns True if any known field changed."""
        changed = False
        for byte in data:
            if byte == FRAME_START:
                self._inside = True
                self._digits = ""
                continue
            if byte == FRAME_END:
                self._inside = False
                self._digits = ""
                continue
            if not self._inside:
                continue
            high, low = byte >> 4, byte & 0x0F
            if high < 10 and low < 10:
                self._digits += f"{high}{low}"
                continue
            if not self._digits:
                continue
            value = float(int(self._digits))
            self._digits = ""
            changed |= self._apply(byte, value)
        return changed

    def _apply(self, tag: int, value: float) -> bool:
        st = self.state
        if tag == TAG_VOLTAGE:
            st.voltage = value / 100.0
        elif tag == TAG_CURRENT:
            st.current_abs = value / 100.0
        elif tag == TAG_DIRECTION:
            st.charging = value == 1.0
        elif tag == TAG_REMAINING_AH:
            st.remaining_ah = value / 1000.0
        elif tag == TAG_DISCHARGED_AH:
            new = value / 1000.0
            # the discharged counter only grows while discharging
            if st.discharged_ah is not None and new > st.discharged_ah:
                st.charging = False
            st.discharged_ah = new
        elif tag == TAG_CHARGED_AH:
            new = value / 1000.0
            # the charged counter only grows while charging
            if st.charged_ah is not None and new > st.charged_ah:
                st.charging = True
            st.charged_ah = new
        elif tag == TAG_MINUTES_LEFT:
            st.minutes_left = value
        elif tag == TAG_POWER:
            st.power_abs = value / 100.0
        elif tag == TAG_TEMPERATURE:
            st.temperature = value - 100.0
        else:
            st.extra[tag] = value
            return False
        return True
