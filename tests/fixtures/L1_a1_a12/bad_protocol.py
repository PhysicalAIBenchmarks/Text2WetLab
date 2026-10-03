metadata = {"apiLevel": "2.16"}
def run(p):
    tr = p.load_labware("opentrons_96_tiprack_300ul", 1)
    pl = p.load_labware("corning_96_wellplate_360ul_flat", 2)
    rs = p.load_labware("agilent_1_reservoir_290ml", 3)
    pip = p.load_instrument("p300_single_gen2", "right", tip_racks=[tr])
    pip.pick_up_tip()
    left = 0
    for i in range(12):
        if i == 0:
            pip.aspirate(300, rs["A1"]); left += 300
        pip.dispense(100, pl.wells()[i]); left -= 100
    pip.drop_tip()
