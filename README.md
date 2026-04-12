# LazyVolt for Home Assistant

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/lazyvolt/home-assistant.svg)](https://github.com/lazyvolt/home-assistant/releases)

Connect your [LazyVolt](https://lazyvolt.com) account to Home Assistant. LazyVolt automatically schedules your EV charging around cheap grid hours and solar production — this integration applies those decisions directly to your Peblar charger.

## How it works

Every 30 seconds the integration:

1. Fetches the current charge decision from LazyVolt Cloud (`SOLAR`, `MAX`, or `STANDBY`)
2. Applies the decision to your Peblar charger via the Peblar HA integration
3. Reports charger state and session energy back to LazyVolt Cloud

**SOLAR** → sets Peblar to *Smart Solar* mode (Peblar's built-in solar intelligence handles P1 load-balancing)
**MAX** → sets Peblar to *Default* mode (charge at full speed)
**STANDBY** → turns the charger off

## Requirements

- A [LazyVolt](https://lazyvolt.com) account
- The [Peblar integration](https://www.home-assistant.io/integrations/peblar/) installed and configured in Home Assistant
- Home Assistant 2024.1 or newer

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/lazyvolt/home-assistant` with category **Integration**
3. Search for **LazyVolt** and install
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/lazyvolt` folder to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **LazyVolt**
3. Enter the email and password you use on [lazyvolt.com](https://lazyvolt.com)
4. Give this Home Assistant instance a name (shown in your LazyVolt dashboard)
5. Select your Peblar charger — if you only have one it is selected automatically

## Troubleshooting

**Charger not responding to mode changes**
Make sure the Peblar integration is installed and the charger is reachable. Check that the `smart_charging` select entity is enabled in Home Assistant.

**"Cannot connect" during setup**
Verify your lazyvolt.com credentials and that Home Assistant has internet access.

**Integration shows unavailable**
Check the Home Assistant logs (`Settings → System → Logs`) for errors from the `lazyvolt` component.

## Contributing

Issues and pull requests welcome at [github.com/lazyvolt/home-assistant](https://github.com/lazyvolt/home-assistant/issues).
