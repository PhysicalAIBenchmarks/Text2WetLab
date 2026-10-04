from opentrons import protocol_api
from opentrons.types import Point

# Note: all the protocol steps code are written in each step to facilitate reading and modification by non-programming users

metadata = {
    'protocolName': 'SARS-CoV-2 VIRAL RNA EXTRACTION',
    'source': 'Hospital Universitario La Paz - Madrid - Spain',
    'apiLevel': '2.2',
    'author': 'MicrobiologyGeneticHULP'}



def run(protocol: protocol_api.ProtocolContext):
    # EQUIPMENT

    ## Slots

    ### 1
    pool_1 = protocol.load_labware('usascientific_96_wellplate_2.4ml_deep', '1')

    ### 2
    tiprack_2 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '2')

    ### 3
    tiprack_3 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '3')

    ### 4
    mag_mod = protocol.load_module('magnetic module', '4')
    wellplate_4 = mag_mod.load_labware('usascientific_96_wellplate_2.4ml_deep')

    ### 5
    reservoir_5 = protocol.load_labware('nest_12_reservoir_15ml', '5')

    ### 6
    tempdeck = protocol.load_module('tempdeck', '6')
    wellplate_6 = tempdeck.load_labware('thermo_96_wellplate_200ul', 'Plate_thermo_96_elutions')

    ### 7
    tuberack_7 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '7')

    ### 8
    # empty

    ### 9
    tiprack_9 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '9')

    ### 10
    tuberack_10 = protocol.load_labware('opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '10')

    ### 11
    tiprack_11 = protocol.load_labware('opentrons_96_filtertiprack_1000ul', '11')


    ## Pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=[tiprack_11])
    p300multi = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=[tiprack_2, tiprack_3, tiprack_9])



    # STARTUP VARIABLES
    sample_number = 48
    columns_trail = [1, 3, 5, 7, 9, 11]
    mag_mod.disengage()



    # PROTOCOL STEPS

    ## 1
    txt_1 = '---> 1) 40 ul magnetic beads'
    protocol.comment(txt_1)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 1
    p300multi.well_bottom_clearance.dispense = 30

    ### Movements
    p300multi.pick_up_tip()
    for h in columns_trail:
        p300multi.transfer(40, reservoir_5.columns_by_name()['2'], wellplate_4.columns_by_name()[str(h)], new_tip='never')
        p300multi.blow_out(wellplate_4.wells()[(h - 1) * 8].top(z=-15))
    p300multi.drop_tip()



    ## 2
    txt_2 = '---> 2) 250 ul isopropanol'
    protocol.comment(txt_2)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 1
    p300multi.well_bottom_clearance.dispense = 30
    isopropanol = reservoir_5.columns_by_name()['6']

    ### Movements
    p300multi.pick_up_tip()
    for i in columns_trail:
        if i == 7:
            isopropanol = reservoir_5.columns_by_name()['7']
        for _ in range(2):
            p300multi.transfer(125, isopropanol, wellplate_4.columns_by_name()[str(i)], new_tip='never')
            p300multi.blow_out(wellplate_4.wells()[(i - 1) * 8].top(z=-15))
    p300multi.drop_tip()



    ## 3
    txt_3 = '---> 3) 250 ul inactivated samples'
    protocol.comment(txt_3)

    ### Variables
    p1000.well_bottom_clearance.aspirate = 1
    p1000.well_bottom_clearance.dispense = 7
    p1000.flow_rate.aspirate = 1000
    p1000.flow_rate.dispense = 1000

    ### Sample collection route
    route_sample_start = []
    for columns_start in range(6):
        route_start = tuberack_10.columns()[columns_start] + tuberack_7.columns()[columns_start]
        route_sample_start += route_start

    ### Sample dispensing (odd columns)
    route_sample_end = []
    for columns_end in range(12):
        if columns_end % 2 == 0:
            route_end = wellplate_4.columns()[columns_end]
            route_sample_end += route_end

    ### Movements
    for sample in range(sample_number):
        p1000.pick_up_tip()
        p1000.transfer(250, route_sample_start[sample], route_sample_end[sample], new_tip='never', mix_after=(5, 350))
        for _ in range(2):
            p1000.blow_out(route_sample_end[sample].top(z=-15))
            p1000.touch_tip(route_sample_end[sample], v_offset=-15)
        p1000.drop_tip()



    ### PAUSE
    protocol.pause('Remove the used tips in the fixed trash (slot 12 of the deck)')



    ## 4
    txt_4 = '---> 4) Pause for 5 minutes'
    protocol.comment(txt_4)

    ### Movements
    protocol.delay(minutes=5)



    ## 5
    txt_5 = '---> 5) Engage magnetic module'
    protocol.comment(txt_5)

    ### Movements
    mag_mod.engage(height_from_base=7)



    ## 6
    txt_6 = '---> 6) Pause for 4 minutes (magnetic activated and working)'
    protocol.comment(txt_6)

    ### Movements
    protocol.delay(minutes=4)



    ## 7
    txt_7 = '---> 7) 500 ul out'
    protocol.comment(txt_7)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 0
    p300multi.well_bottom_clearance.dispense = 20
    p300multi.flow_rate.dispense = 900

    ### Movements
    for j in columns_trail:
        p300multi.pick_up_tip()
        for _ in range(3):
            p300multi.transfer(175, wellplate_4.columns_by_name()[str(j)], pool_1.columns_by_name()[str(j)], new_tip='never')
            p300multi.blow_out(pool_1.wells()[(j-1)*8].top(z=-15))
            p300multi.touch_tip(pool_1.wells()[(j-1)*8], radius=0.60, v_offset=-15)
        p300multi.drop_tip()



    ## 8
    txt_8 = '---> 8) 500 ul ethanol absolute wash 1 in'
    protocol.comment(txt_8)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 1
    p300multi.well_bottom_clearance.dispense = 30
    p300multi.flow_rate.dispense = 200
    ethanol_first = reservoir_5.columns_by_name()['9']

    ### Movements
    p300multi.pick_up_tip()
    for k in columns_trail:
        if k == 7:
            ethanol_first = reservoir_5.columns_by_name()['10']
        for _ in range(3):
            p300multi.transfer(167, ethanol_first, wellplate_4.columns_by_name()[str(k)], new_tip='never')
    p300multi.drop_tip()



    ## 9
    txt_9 = '---> 9) 500 ul wash 1 out'
    protocol.comment(txt_9)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 0
    p300multi.well_bottom_clearance.dispense = 20
    p300multi.flow_rate.dispense = 900

    ### Movements
    for l in columns_trail:
        pool_column_end = pool_1.columns_by_name()[str(l+1)]
        pool_well_end = pool_1.wells()[(l-1)*8+8]
        p300multi.pick_up_tip()
        for _ in range(3):
            p300multi.transfer(175, wellplate_4.columns_by_name()[str(l)], pool_column_end, new_tip='never')
            p300multi.blow_out(pool_well_end.top(z=-15))
            p300multi.touch_tip(pool_well_end, radius=0.80, v_offset=-15)
        p300multi.drop_tip()



    ## 10
    txt_10 = '---> 10) 500 ul ethanol absolute wash 2 in'
    protocol.comment(txt_10)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 1
    p300multi.well_bottom_clearance.dispense = 30
    p300multi.flow_rate.dispense = 200
    ethanol_second = reservoir_5.columns_by_name()['11']

    ### Movements
    p300multi.pick_up_tip()
    for m in columns_trail:
        if sample_number == 48 and m == 7:
            ethanol_second = reservoir_5.columns_by_name()['12']
        for _ in range(3):
            p300multi.transfer(167, ethanol_second, wellplate_4.columns_by_name()[str(m)], new_tip='never')
    p300multi.drop_tip()



    ## 11
    txt_11 = '---> 11) 500 ul wash 2 out'
    protocol.comment(txt_11)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 0
    p300multi.well_bottom_clearance.dispense = 20
    p300multi.flow_rate.dispense = 900

    ### Movements
    for n in columns_trail:
        pool_column_end = pool_1.columns_by_name()[str(n+1)]
        pool_well_end = pool_1.wells()[(n-1)*8+8]
        p300multi.pick_up_tip()
        for _ in range(3):
            p300multi.transfer(175, wellplate_4.columns_by_name()[str(n)], pool_column_end, new_tip='never')
            p300multi.blow_out(pool_well_end.top(z=-15))
            p300multi.touch_tip(pool_well_end, radius=0.80, v_offset=-15)
        p300multi.drop_tip()



    ## 12
    txt_12 = '---> 12) Pause for 4 minutes (drying step, magnetic module activated and working)'
    protocol.comment(txt_12)

    ### Variables
    protocol.delay(minutes=4)



    ## 13
    txt_13 = '---> 13) Disengage magnetic module'
    protocol.comment(txt_13)

    ### Movements
    mag_mod.disengage()



    ## 14
    txt_14 = '---> 14) 100 ul elution'
    protocol.comment(txt_14)

    ### Variables
    p300multi.well_bottom_clearance.aspirate = 1
    p300multi.well_bottom_clearance.dispense = 30
    p300multi.flow_rate.dispense = 900
    minutes_drying = 1

    ### Movements
    p300multi.pick_up_tip()
    for p in columns_trail:
        protocol.delay(minutes=minutes_drying)
        p300multi.transfer(100, reservoir_5.columns_by_name()['4'], wellplate_4.columns_by_name()[str(p)], new_tip='never')
        p300multi.blow_out(wellplate_4.wells()[(p-1)*8].top(z=-15))
    p300multi.drop_tip()



    ## 15
    txt_15 = '---> 15) Final dispense (eluted viral RNA)'
    protocol.comment(txt_15)

    ### Variables
    tempdeck.set_temperature(4)

    ### Movements
    for o in columns_trail:

        ### Variables
        mag_mod.disengage()



        ## 15.1
        txt_15_1 = '---> 15.1) Mix'
        protocol.comment(txt_15_1)

        ### Variables
        p300multi.flow_rate.dispense = 1000
        p300multi.flow_rate.aspirate = 150

        ### Movements
        p300multi.pick_up_tip()
        p300multi.mix(20, 80, wellplate_4.wells()[(o-1)*8].bottom(z=0))
        for _ in range(2):
            p300multi.blow_out(wellplate_4.wells()[(o-1)*8].top(z=-15))
            p300multi.touch_tip(wellplate_4.wells()[(o-1)*8], v_offset=-15)
            p300multi.blow_out(wellplate_4.wells()[(o-1)*8].top(z=-15))
        p300multi.flow_rate.dispense = 900



        ## 15.2
        txt_15_2 = '---> 15.2) Pause for 30 seconds, engage magnetic module and pause for 1 minute and 30 seconds'
        protocol.comment(txt_15_2)

        ### Movements
        mag_mod.engage(height_from_base=7)
        protocol.delay(minutes=1, seconds=30)



        ## 15.3
        txt_15_3 = '---> 15.3) 80 ul recover eluted viral RNA'
        protocol.comment(txt_15_3)

        ### Variables
        p300multi.well_bottom_clearance.aspirate = 0
        p300multi.well_bottom_clearance.dispense = 5
        p300multi.flow_rate.aspirate = 50
        side_shift = -2

        ### Movements
        p300multi.transfer(80, wellplate_4.wells_by_name()['A' + str(o)].bottom(z=0).move(Point(x=side_shift, y=0, z=0)), wellplate_6.columns_by_name()[str(o)], new_tip='never')
        for _ in range(2):
            p300multi.blow_out(wellplate_6.wells()[(o-1)*8].top(z=-5))
            p300multi.touch_tip(wellplate_6.wells()[(o-1)*8], v_offset=-5)
            p300multi.blow_out(wellplate_6.wells()[(o-1)*8].top(z=-5))
        p300multi.drop_tip()



    ## 16 and END
    txt_16 = '---> 16 and END) Disengage magnetic module'
    protocol.comment(txt_16)

    ### Movements
    mag_mod.disengage()