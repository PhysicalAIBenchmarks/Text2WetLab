"""
REFERENCE protocol — correct implementation of the test criteria:
  1. Pick up tip BEFORE any liquid
  2. Aspirate 200uL (enough for 2x 100uL dispenses)
  3. Dispense 100uL → well A1, then 100uL → well B1 (same tip load)
  4. Drop tip when finished
  5. No crashes — all z-lifts handled by Opentrons automatically

Run with:  opentrons_simulate protocol_correct.py
"""

metadata = {
    "apiLevel": "2.16",
    "protocolName": "NL2WetLab — Correct Reference",
    "description": "200uL aspirate, 2x 100uL dispense, tip management",
}


def run(protocol):
    # Deck layout
    tiprack = protocol.load_labware("opentrons_96_tiprack_1000ul", 1)
    plate   = protocol.load_labware("corning_96_wellplate_360ul_flat", 2)
    trough  = protocol.load_labware("agilent_1_reservoir_290ml", 3)
    pipette = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tiprack])

    # CRITERION 1: pick up tip before any liquid movement
    pipette.pick_up_tip()

    # CRITERION 2+3: aspirate 200uL, dispense in two 100uL doses (same tip load)
    pipette.aspirate(200, trough["A1"])
    pipette.dispense(100, plate["A1"])   # 100uL remaining in tip
    pipette.dispense(100, plate["B1"])   # 0uL remaining

    # CRITERION 4: drop tip
    pipette.drop_tip()

    # CRITERION 5 (implicit): Opentrons API always lifts to safe-z before
    # lateral moves. No manual move_to() needed.
