# Change Log

## Pending

- Add support for `move_drops` RPC, which moves up to five drops at once using
  group capacitance as feedback and adds support for control of more move options,
  including the gain to use, the timeout, and how much trailing data to collect
  ("post_capture_time").
- Changes move_drop to report calibrated capacitance in its return data
- Change background threads to greenlets
- Add simulation mode to pdserver with --sim argument

## v0.5.0 (Jun 30, 2021)

- Add support for low-gain active capacitance measurement
- Drops support for embedded software v0.4.x
  - ActiveCapacitance message was updated to support low gain flag
- Adds support for per-electrode capacitance offset calibration, loaded
  automatically from a file or via the set_electrode_calibration RPC
- Adds board definition for misl v6.1 board
- Adds set_scan_gains and get_scan_gains RPCs

## v0.4.0 (Apr 28, 2021)

- Supports embedded software v0.4.x
  - It does *not* support older versions. Update of embedded software is required.
- Add support for feedback control commands, drive groups, and capacitance
scan groups
- Add support for electrode board definitions with multiple non-homogenous grids
- Add support for providing control points in command arguments for `pdcam measure`
- Add MISL v6 electrode board definition

## v0.3.0 (Mar 11, 2021)

- Add RPC call for GPIO control
- Add misl_v4.1 electrode board definition
- Incorporate pdcam into purpledrop project
- Add pd_log command for extracting video from recorded event logs
