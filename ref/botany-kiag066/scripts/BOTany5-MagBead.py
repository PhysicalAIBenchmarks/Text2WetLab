from opentrons import protocol_api
from opentrons import types
from opentrons.types import Point
import threading
from time import sleep
import math

# metadata
metadata = {
    "protocolName": "BOTany5-MagBead",
    "description": """Protocol for binding, washing, and elution steps using Zymo Zyppy-96 Plasmid MagBead Kit""",
    "author": "Voiniciuc Lab & Parrish Payne<protocols@opentrons.com>"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}

def add_parameters(parameters):
    parameters.add_int(
        variable_name="num_samp",
        display_name="Number of samples",
        description="Number of samples in 96-well plate.",
        default=48,
        minimum=1,
        maximum=96,
        unit="qty",
    )
    parameters.add_int(
        variable_name="starting_col",
        display_name="Sample Starting Column",
        description="Starting column in 96-well plate",
        choices=[
            {"display_name": "1st", "value": 0},
            {"display_name": "2nd", "value": 1},
            {"display_name": "3rd", "value": 2},
            {"display_name": "4th", "value": 3},
            {"display_name": "5th", "value": 4},
            {"display_name": "6th", "value": 5},
            {"display_name": "7th", "value": 6},
            {"display_name": "8th", "value": 7},
            {"display_name": "9th", "value": 8},
            {"display_name": "10th", "value": 9},
            {"display_name": "11th", "value": 10},
            {"display_name": "12th", "value": 11},
        ],
        default=0,
    )
    '''parameters.add_int(
        variable_name="bead_time",
        display_name="Settling Time",
        description="Length of time for magnetic beads to settle.",
        default=1,
        minimum=1,
        maximum=10,
        unit="minutes",
    )''' #Fixed to 1 min
    parameters.add_str(
        variable_name = "elution_plate_type", display_name = "Elution Plate", default = "zymoelution_96_wellplate_90ul", choices = [
            {"display_name": "Opentrons Tough PCR Plate, 200", "value": "opentrons_96_wellplate_200ul_pcr_full_skirt"},
            {"display_name": "NEST 96-well PCR Plate, 100 µL", "value": "nest_96_wellplate_100ul_pcr_full_skirt"},
            {"display_name": "ZymoElution 96-Well, 90 µL", "value": "zymoelution_96_wellplate_90ul"}
        ]
    )
    parameters.add_str(
        variable_name = "collection_plate_type", display_name = "Collection Plate", default = "zymocollection_96_wellplate_1200ul", choices = [
            {"display_name": "ZymoCollection 96-well, 1.2mL", "value": "zymocollection_96_wellplate_1200ul"}
        ]
    )
    parameters.add_bool(
        variable_name="dry_run",
        display_name="Dry Run",
        description=(
            "Skips duplicate steps and shortens incubations."
        ),
        default=False
    )
    #Parameter added to control location of pipette
    parameters.add_str(
        variable_name = "pipette_side",
        display_name = "8-channel P300 Location",
        default = "left",
        choices = [{"display_name": "Left", "value": "left"},
        {"display_name": "Right", "value": "right"}]
    )

# Definitions for deck light flashing
class CancellationToken:
    def __init__(self):
        self.is_continued = False

    def set_true(self):
        self.is_continued = True

    def set_false(self):
        self.is_continued = False


def turn_on_blinking_notification(hardware, pause):
    while pause.is_continued:
        hardware.set_lights(rails=True)
        sleep(1)
        hardware.set_lights(rails=False)
        sleep(1)


def create_thread(ctx, cancel_token):
    t1 = threading.Thread(target=turn_on_blinking_notification,
                          args=(ctx._hw_manager.hardware, cancel_token))
    t1.start()
    return t1

# protocol run function
def run(ctx: protocol_api.ProtocolContext):
    # Setup for flashing lights notification to empty trash
    cancellationToken = CancellationToken()

    # run time parameters
    num_samp = ctx.params.num_samp  
    starting_col = ctx.params.starting_col
    settling_time = 1 # bead settling time on mag mod
    elution_plate_type = ctx.params.elution_plate_type
    collection_plate_type = ctx.params.collection_plate_type
    dry_run = ctx.params.dry_run     ## ctx.params.dry_run skips steps & shorthens incubations for quicker run-time/testing
    pipette_location = ctx.params.pipette_side


    # variables
    m300_mount = str(pipette_location)

    if (num_samp < 1) or (num_samp > (96 - ((starting_col - 1) * 8))):
        raise Exception('\n\n~~~~~~~Parameters Out of Bounds~~~~~~~~\n')
    
    full_cols = int(num_samp//8)
    if num_samp%8 == 0: 
        num_cols = full_cols
    else:
        num_cols = full_cols + 1

    adj_col=num_cols+starting_col
    
    flash = True

    # Deck Setup
    mag_mod = ctx.load_module('magnetic module gen2', location=1)
    mag_mod.disengage()

    hs_mod = ctx.load_module('heaterShakerModuleV1', location=10)
    # hs_adapter = hs_mod.load_adapter("opentrons_96_deep_well_adapter")
    hs_mod.close_labware_latch()

    # optimization parameters
    # mag_time = 3        # number of minutes on magnetic block
    # num_mix = 10        ## number of aspirate/dispense cycles
    # dry_time = 3        #  delay to dry the beads in minutes
    # airgap = 5         ## volume of airgap in µL
    # mag_block_asp_height = 3    ## distance from bottom of well in mm

    # labware
    elution_plate = ctx.load_labware(elution_plate_type, location=4, label="Elution Plate") # 'opentrons_96_wellplate_200ul_pcr_full_skirt' Replaced with custom labware definition
    collection_plate = hs_mod.load_labware(collection_plate_type, label="Collection Plate")  # 'nest_96_wellplate_2ml_deep' Replaced with custom labware definition
    dw_plate = ctx.load_labware("nest_96_wellplate_2ml_deep", location=2, label="NEST 2 mL Deepwell Plate") # requested slot 7, moved due to conflict with H-S mod
    reservoir = ctx.load_labware("nest_12_reservoir_15ml", location= 3, label="NEST 12-well Reservoir")
    waste = ctx.load_labware('nest_1_reservoir_195ml', location= 8, label="NEST 1-well Reservoir").wells()[0].top()  # empty (trash)
    tips300 = [ctx.load_labware("opentrons_96_tiprack_300ul", location = slot, label="300 µL Tiprack")
                               for slot in ['5', '6']] 
    
    parkingrack = ctx.load_labware(
        'opentrons_96_tiprack_300ul', '9', 'tiprack for parking')
    parking_spots = parkingrack.rows()[0][starting_col:adj_col]
   

    # pipettes
    m300 = ctx.load_instrument(
        'p300_multi_gen2', m300_mount, tip_racks=tips300)
    
    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 300
    
    # mapping
    binding_buffer = dw_plate.rows()[0][0]          # Binding bead buffer in column 1 (400uL in each well)
    elution_buffer = dw_plate.rows()[0][1]          # Elution buffer in column 2 (560uL in each well)    
    endo_wash = reservoir.rows()[0][:2]             # Endo wash buffer in columns 1-2 (12mL in each well)
    zyppy_wash = reservoir.rows()[0][2:8]           # Zyppy wash buffer in columns 3-8 (12mL in each well)
    collection_wells = collection_plate.rows()[0][starting_col:adj_col]   # Heater shaker module with Zymo collection plate (650uL clear lysate loaded in each well)
    elution_wells = elution_plate.rows()[0][:num_cols]

    # LOADING LIQUID
    binding_buffer_color = ctx.define_liquid(
    name="Binding Bead Buffer",
    description="µL per sample",
    display_color="#008000", # Green
    )
    binding_buffer_vol = 30 # µL per sample

    elution_buffer_color = ctx.define_liquid(
    name="Elution Buffer",
    description="µL per wash",
    display_color="#FFFF00", # Yellow
    )
    elution_buffer_vol = 40 # µL per sample 

    endo_wash_color = ctx.define_liquid(
    name="Endo Wash Buffer",
    description="µL per well",
    display_color="#0000FF", # Blue
    )
    endo_wash_vol = 200 

    zyppy_wash_color = ctx.define_liquid(
    name="Zyppy Wash Buffer",
    description="µL per well",
    display_color="#FFA500", # Orange
    )
    zyppy_wash_vol = 600 # µL of sample

    sample_color = ctx.define_liquid(
    name="Samples",
    description="µL per well",
    display_color="#FF0000", # Red
    )
    sample_vol = 50 # 50 µL of sample

    for well in dw_plate.columns()[0]:
        well.load_liquid(liquid=binding_buffer_color, volume=binding_buffer_vol)
    for well in dw_plate.columns()[1]:
        well.load_liquid(liquid=elution_buffer_color, volume=elution_buffer_vol)
    
    for well in reservoir.rows()[0][:2]:
        well.load_liquid(liquid=endo_wash_color, volume=endo_wash_vol)
    for well in reservoir.rows()[0][2:8]:
        well.load_liquid(liquid=zyppy_wash_color, volume=endo_wash_vol)

    adj_well = starting_col*8
    for well in collection_plate.wells()[adj_well:num_samp+adj_well]:
        well.load_liquid(liquid=sample_color, volume=sample_vol)
    
    # helper functions
    #Made a tip_log dictionary where 'count' is the key
    tip_log = {'count': {}}
    #Not sure what ctx.is_simulating means...
    if not ctx.is_simulating():
            #Add a value to tip_log where the key is 'count' and val is m300 pipette loaded object, including the tiprack it uses. 
            #Then m300 is a nested key-value pair, where m300 : 0
            tip_log['count'][m300] = 0
    else:
        tip_log['count'] = {m300: 0}

    

    #For each tip rack, and for each row in the racks, give total count of columns
    tip_log['tips'] = {
        m300: [tip for rack in tips300 for tip in rack.rows()[0]]}
    
    #After printing these, found that tip_log['tips'] stores the first wells for each column of the various tipracks, ex. 
    ctx.comment("tip_log[tips]")
    ctx.comment(str(tip_log['tips']))
    
    #Get the maximum amt of tips in m300
    tip_log['max'] = {m300: len(tip_log['tips'][m300])}

    ctx.comment("tip_log[max]")
    ctx.comment(str(tip_log['max']))
    ctx.comment("tip_log[count]")
    ctx.comment(str(tip_log['count']))


    def _pick_up(pip, loc=None):
        #Allows you to assign tip_log to an outside of loop scope, but not glocal
        nonlocal tip_log

        #If all the tips have been used, then tell user to add another tiprack before resuming.
        if tip_log['count'][pip] == tip_log['max'][pip] and not loc:
            ctx.pause('\n\n~~~~Replace ' + str(pip.max_volume) + 'µl tipracks before resuming~~~~\n')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        #Allows pipette to go to a specific location
        if loc:
            pip.pick_up_tip(loc)
        else:
            pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
            ctx.comment("Picking up tips from:")
            ctx.comment(str(tip_log['tips'][pip][tip_log['count'][pip]]))
            tip_log['count'][pip] += 1
            ctx.comment("Current count value:")
            ctx.comment(str(tip_log['count']))

   
    drop_count = 0
    # number of tips trash will accommodate before prompting user to empty
    drop_threshold = 120

    def _drop(pip):
        nonlocal drop_count
        pip.drop_tip()
        if pip.type == 'multi':
            drop_count += 8
        else:
            drop_count += 1
        if drop_count >= drop_threshold:
            # Setup for flashing lights notification to empty trash
            if flash:
                if not ctx._hw_manager.hardware.is_simulator:
                    cancellationToken.set_true()
                thread = create_thread(ctx, cancellationToken)
            pip.home()
            ctx.pause('\n\n~~~~Please empty tips from waste before resuming.~~~~\n')
            ctx.home()  # home before continuing with protocol
            if flash:
                cancellationToken.set_false()  # stop light flashing after home
                thread.join()
            drop_count = 0

    waste_vol = 0
    waste_threshold = 250000

    def remove_supernatant(vol, park):
        """
        `remove_supernatant` will transfer supernatant from the deepwell
        extraction plate to the liquid waste reservoir.
        :param vol (float): The amount of volume to aspirate from all deepwell
                            sample wells and dispense in the liquid waste.
        :param park (boolean): Whether to pick up sample-corresponding tips
                               in the 'parking rack' or to pick up new tips.
        """
        def _waste_track(vol):
            nonlocal waste_vol

            if waste_vol + vol >= waste_threshold:
                # Setup for flashing lights notification to empty liquid waste
                if flash:
                    if not ctx._hw_manager.hardware.is_simulator:
                        cancellationToken.set_true()
                    thread = create_thread(ctx, cancellationToken)
                m300.home()
                ctx.pause('\n\n~~~~Please empty liquid waste before resuming.~~~~\n')

                ctx.home()  # home before continuing with protocol
                if flash:
                    # stop light flashing after home
                    cancellationToken.set_false()
                    thread.join()

                waste_vol = 0
            waste_vol += vol

        m300.flow_rate.aspirate = 30
        num_trans = math.ceil(vol/m300.max_volume)
        vol_per_trans = vol/num_trans
        for i, (m, spot) in enumerate(zip(collection_wells, parking_spots)):
            if park:
                _pick_up(m300, spot)
            else:
                _pick_up(m300)
            side = -1 if i % 2 == 0 else 1
            loc = m.bottom(z=4).move(Point(x=side*1.3))
            for _ in range(num_trans):
                _waste_track(vol_per_trans*8)
                if m300.current_volume > 0:
                    # void air gap if necessary
                    m300.dispense(m300.current_volume, m.top())
                    m300.blow_out()
                m300.move_to(m.center())
                m300.transfer(vol_per_trans, loc, waste, new_tip='never',
                              air_gap=20)
                m300.blow_out(waste)
                m300.air_gap(20)
            if park:
                m300.drop_tip(spot)
            else:
                _drop(m300)
        m300.flow_rate.aspirate = 150

    def resuspend_pellet(well, mvol, reps):
            """
            'resuspend_pellet' will forcefully dispense liquid over the pellet
            after the mag_mod engage in order to more thoroughly resuspend the
            pellet.'
            :param well: The current well that the resuspension will occur in. 
]           :param mvol: The volume that is transferred before the mixing steps.
            :param reps: The number of mix repetitions that should occur. Note~
            During each mix rep, there are 2 cycles of aspirating from center,
            dispensing at the top and 2 cycles of aspirating from center,
            dispensing at the bottom (5 mixes total)
            """

            rightLeft = int(str(well).split(' ')[0][1:]) % 2
            """
            'rightLeft' will determine which value to use in the list of 'top' and
            'bottom' (below), based on the column of the 'well' used.
            In the case that an Even column is used, the first value of 'top' and
            'bottom' will be used, otherwise, the second value of each will be
            used.
            """
            center = well.bottom().move(types.Point(x=0, y=0, z=1))
            top = [
                well.bottom().move(types.Point(x=-1, y=1, z=3)),
                well.bottom().move(types.Point(x=1, y=1, z=3))
            ]
            bottom = [
                well.bottom().move(types.Point(x=-1, y=-1, z=3)),
                well.bottom().move(types.Point(x=1, y=-1, z=3))
            ]

            m300.flow_rate.dispense = 300
            m300.flow_rate.aspirate = 150

            mix_vol = 0.9 * mvol

            m300.move_to(center)
            for _ in range(reps):
                for _ in range(2):
                    m300.aspirate(mix_vol, center)
                    m300.dispense(mix_vol, top[rightLeft])
                for _ in range(2):
                    m300.aspirate(mix_vol, center)
                    m300.dispense(mix_vol, bottom[rightLeft])

    def mix_bind(vol, mix_reps):
        """
        `mix_bind` will mix each channel of binding beads then transfer binding buffer. 
        :param vol (float): The amount of volume to aspirate from the elution
                            buffer source and dispense to each well containing
                            beads.
        :param mix_reps (int): The number of repititions to mix the beads before transfer.
        """
        first_col = True #Boolean for whether this is the mix/transfer for the first column of beads or not.

        for m in collection_wells:
            #If we're getting the beads for the first column, pick up tips. Else reuse
            if first_col == True:
                _pick_up(m300)

            first_col = False #Now set it to false

            ctx.comment("Current count value for mix_bind():")
            ctx.comment(str(tip_log['count']))
            for _ in range(mix_reps):
                m300.aspirate(vol, binding_buffer.bottom(1))
                m300.dispense(vol, binding_buffer.bottom(5))
            m300.transfer(vol, binding_buffer, m.top(), air_gap=20,
                            new_tip='never')
            m300.blow_out(m.top(-2))
            m300.air_gap(20)
            #m300.drop_tip()

        _drop(m300)
    
    def wash(vol, source, mix_reps, resuspend=False):
        """
        `wash` will perform bead washing for the extraction protocol.
        :param vol (float): The amount of volume to aspirate from each
                            source and dispense to each well containing beads.
        :param source (List[Well]): A list of wells from where liquid will be
                                    aspirated. If the length of the source list
                                    > 1, `wash` automatically calculates
                                    the index of the source that should be
                                    accessed.
        :param mix_reps (int): The number of repititions to mix the beads with
                               specified wash buffer (ignored if resuspend is
                               False).
        :param resuspend (boolean): Whether to resuspend beads in wash buffer.
        """

        if resuspend and mag_mod.status == 'engaged':
            mag_mod.disengage()

        #Calculating how many transfers are needed for each (well?)
        num_trans = math.ceil(vol/200)
        #Vol calc for each transfer
        vol_per_trans = vol/num_trans

        _pick_up(m300)

        for i, m in enumerate(collection_wells):
            #Pick up col of multichannel tips
            
            ctx.comment("Current count value for wash():")
            ctx.comment(str(tip_log['count']))
            #Go to well that contains the liquid, calculate which well depending on liquid???
            src = source[i//(12//len(source))]
            for n in range(num_trans):
                if m300.current_volume > 0:
                    m300.dispense(m300.current_volume, src.top())
                m300.transfer(vol_per_trans, src, m.top(), air_gap=20,
                              new_tip='never')
                if n < num_trans - 1:  # only air_gap if going back to source
                    m300.air_gap(20)
            if resuspend:
                resuspend_pellet(m, mvol=200, reps=mix_reps)

            m300.blow_out(m.top())
            m300.air_gap(20)
            
        _drop(m300)

    def custom_transfer(vol, source):
        _pick_up(m300)
        for i, m in enumerate(collection_wells):
            m300.transfer(vol, source, m.top(), air_gap=20, new_tip='never')
            m300.blow_out()
        _drop(m300)

    def elute(vol):
        """
        `elute` will transfer eluate from the deepwell extraciton plate to the
        final clean elutions PCR plate to complete the extraction protocol.
        :param vol (float): The amount of volume to aspirate from the elution
                            buffer source and dispense to each well containing
                            beads.
        """
        m300.flow_rate.aspirate = 47 #About 1/2 of default
        for i, (m, e) in enumerate(zip(collection_wells, elution_wells)):
            _pick_up(m300)
            side = -1 if i % 2 == 0 else 1
            loc = m.bottom(z=2).move(Point(x=side*1.3))
            m300.transfer(vol, loc, e.bottom(3), air_gap=20, new_tip='never')
            m300.blow_out(e.top(-2))
            m300.air_gap(20)
            _drop(m300)    

        m300.flow_rate.aspirate = 94 #Change back to default


    ##### requested partial tip pick up if the sample number is not divisible by 8. 

    #### Protocol Steps Begin Here ####

    # 1: Mix the binding buffer at the default rate for 5 times in the first column of NEST 96 Deep Well Plate (slot 7).
    # 2: transfer 30uL binding bead buffer from NEST 96 Deep Well Plate (column 1; slot 7) to each well of Zymo collection plate (on heater shaker). IMPORTANT, must mix as step 1 before each aspiration.
    
    ctx.comment('\n\n~~~Mix & Transfer Binding Bead Buffer to Collection Plate~~~~\n')
    mix_bind(30,  mix_reps=5)

    # 3: Vortex Zymo collection plate (on heater shaker) at 1800 rpm 5 seconds per 30 seconds for 5 minutes.
    ctx.comment('\n\n~~~Shake 5 seconds @ 1800 RPM every 30 seconds for 5 min~~~~~\n')
    hs_mod.close_labware_latch()
    # CHANGE to 5 minute , 1000rpm
    hs_mod.set_and_wait_for_shake_speed(1000)
    ctx.delay(minutes=5)
    '''for i in range (9):
        hs_mod.set_and_wait_for_shake_speed(1800)
        ctx.delay(seconds=5)
        hs_mod.deactivate_shaker()
        ctx.delay(seconds=25)
    hs_mod.set_and_wait_for_shake_speed(1800)
    ctx.delay(seconds=5)'''
    hs_mod.deactivate_shaker()

    

    # 4: Move Zymo collection plate from the heater shaker onto the magnetic module and engage magnetics to the height of 3.9mm. Pause for 1 minute.
    hs_mod.open_labware_latch()
    ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Magnetic Module~~~~~~~\n')
    ctx.move_labware(labware=collection_plate, new_location=mag_mod, use_gripper=False)
    mag_mod.engage(height_from_base=3.9)
    ctx.delay(minutes=settling_time if not dry_run else 0.1, msg='\n\n~~~~~Incubating on mag_mod for ' + str(settling_time) + ' minutes~~~~~~\n')

    # 5: Aspirate 650uL liquid from each well of Zymo collection plate and discard it into the waste reservoir (slot 8). 
    # Park the tips back on the rack (use the tip rack on slot 9 particularly to discard supernatant and tip parking).
    ctx.comment('\n\n~~~~~~~~~~~~Remove Supernatant~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
    remove_supernatant(650, park=True)

    # 6: Disengage the magnet and move Zymo collection plate from the magnetic module onto the heater shaker.
    mag_mod.disengage()
    ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Heater-Shaker~~~~~~~~~\n')
    ctx.move_labware(labware=collection_plate, new_location=hs_mod, use_gripper=False)
    hs_mod.close_labware_latch()

    # 7: Distribute 200uL Endo wash buffer (slot 11, column 1-2) to each well of Zymo collection plate.
    ctx.comment('\n\n~~~~~~Transfer Endo Wash Buffer to Collection Plate~~~~~~~~~~\n')
    wash(200, endo_wash, mix_reps=0, resuspend=False)

    # 8: Vortex Zymo collection plate (on heater shaker) at 1800 rpm for 30 seconds.
    ctx.comment('\n\n~~~~~~~~~~Shake 30 seconds @ 1800 RPM~~~~~~~~~~~~~~~~~~~~~~~~\n')
    hs_mod.set_and_wait_for_shake_speed(1100)
    ctx.delay(seconds=90)
    hs_mod.deactivate_shaker()

    # 9: Move Zymo collection plate from the heater shaker onto the magnetic module and engage magnetics to the height of 3.9mm. Pause for 1 minute.
    hs_mod.open_labware_latch()
    ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Magnetic Module~~~~~~~\n')
    ctx.move_labware(labware=collection_plate, new_location=mag_mod, use_gripper=False)
    mag_mod.engage(height_from_base=3.9)
    ctx.delay(minutes=settling_time if not dry_run else 0.1, msg='\n\n~~~~~Incubating on mag_mod for ' + str(settling_time) + ' minutes~~~~~~~\n')

    # 10: Aspirate 200uL liquid from each well of Zymo collection plate and discard it into the waste reservoir (slot 8). 
    # Use the previous tips in Step 5. Park the tips back on the rack (use the tip rack on slot 9 particularly to discard supernatant and tip parking).
    ctx.comment('\n\n~~~~~~~~~~~~Remove Supernatant~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n')
    remove_supernatant(200, park=True)

    # 11: Disengage the magnet and move Zymo collection plate from the magnetic module onto the heater shaker.
    mag_mod.disengage()
    ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Heater-Shaker~~~~~~~~~\n')
    ctx.move_labware(labware=collection_plate, new_location=hs_mod, use_gripper=False)
    hs_mod.close_labware_latch()

    # 12: Distribute 300uL Zyppy wash buffer (slot 11, column 3-7) to each well of Zymo collection plate.
    ctx.comment('\n\n~~~~~~1st Wash with Zyppy Wash Buffer~~~~~~~~~~~~~~~~~~~~~~~~\n')
    wash(300, zyppy_wash, mix_reps=0, resuspend=False)

    # 13: Vortex Zymo collection plate (on heater shaker) at 1800 rpm for 30 seconds.
    hs_mod.set_and_wait_for_shake_speed(1200)
    ctx.delay(seconds=90)
    hs_mod.deactivate_shaker()

    # 14: Move Zymo collection plate from the heater shaker onto the magnetic module and engage magnetics to the height of 3.9mm. Pause for 1 minute.
    hs_mod.open_labware_latch()
    ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Magnetic Module~~~~~~~\n')
    
    ctx.move_labware(labware=collection_plate, new_location=mag_mod, use_gripper=False)
    mag_mod.engage(height_from_base=3.9)
    ctx.delay(minutes=settling_time if not dry_run else 0.1, msg='\n\n~~~~~Incubating on mag_mod for ' + str(settling_time) + ' minutes~~~~~~~\n')

    # 15: Aspirate 300uL liquid from each well of Zymo collection plate and discard it into the waste reservoir (slot 8). Use the previous tips in Step 5. Park the tips back on the rack (use the tip rack on slot 9 particularly to discard supernatant and tip parking).
    remove_supernatant(300, park=True)

    # 16: Disengage the magnet and move Zymo collection plate from the magnetic module onto the heater shaker.
    mag_mod.disengage()
    ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Heater-Shaker~~~~~~~~~\n')
    ctx.move_labware(labware=collection_plate, new_location=hs_mod, use_gripper=False)
    hs_mod.close_labware_latch()

    # 17: Repeat Step 12-16.
    # Distribute 300uL Zyppy wash buffer (slot 11, column 3-7) to each well of Zymo collection plate.
    if not dry_run:    
        ctx.comment('\n\n~~~~~~2nd Wash with Zyppy Wash Buffer~~~~~~~~~~~~~~~~~~~~~~~~\n')
        wash(300, zyppy_wash, mix_reps=0, resuspend=False)

    # Vortex Zymo collection plate (on heater shaker) at 1800 rpm for 30 seconds.
    if not dry_run:   
        hs_mod.set_and_wait_for_shake_speed(1200)
        ctx.delay(seconds=90)
        hs_mod.deactivate_shaker()

    # Move Zymo collection plate from the heater shaker onto the magnetic module and engage magnetics to the height of 3.9mm. Pause for 1 minute.
    if not dry_run:   
        hs_mod.open_labware_latch()
        ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Magnetic Module~~~~~~~\n')
        ctx.move_labware(labware=collection_plate, new_location=mag_mod, use_gripper=False)
        mag_mod.engage(height_from_base=3.9)
        ctx.delay(minutes=settling_time if not dry_run else 0.1, msg='\n\n~~~~Incubating on mag_mod for ' + str(settling_time) + ' minutes~~~~\n')

    #If there's too much liquid inside, Moni can further modify the number below
    # Aspirate 300uL liquid from each well of Zymo collection plate and discard it into the waste reservoir (slot 8). Use the previous tips in Step 5. Park the tips back on the rack (use the tip rack on slot 9 particularly to discard supernatant and tip parking).
    if not dry_run:   
        remove_supernatant(300, park=True)

    # Disengage the magnet and move Zymo collection plate from the magnetic module onto the heater shaker.
    if not dry_run:   
        mag_mod.disengage()
        ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Heater-Shaker~~~~~~~~~\n')
        ctx.move_labware(labware=collection_plate, new_location=hs_mod, use_gripper=False)
        hs_mod.close_labware_latch()

    # 18: Manually turn on the HEPA module.
    ctx.pause('\n\n~~~~~~~~~~~~Manually Turn On the HEPA Module~~~~~~~~~~~~~~~~~~~\n')

    #If this doesn't work, Moni can further modify it
    # 18: Vortex Zymo collection plate (on heater shaker) at 1800 rpm at 65C for 6 minutes.
    ctx.comment('\n\n~~~~~~~~~~Shake 6 Minutes @ 1800 RPM 65C~~~~~~~~~~~~~~~~~~~~~\n')
    hs_mod.set_and_wait_for_temperature(75)
    hs_mod.set_and_wait_for_shake_speed(1800)
    ctx.delay(minutes=10 if not dry_run else 0.1)
    hs_mod.deactivate_shaker()
    hs_mod.deactivate_heater()

    # 19: Manually turn off the HEPA module and deactivate the heater shaker.
    ctx.pause('\n\n~~~~~~~~~~~~Manually Turn Off the HEPA Module~~~~~~~~~~~~~~~~~~\n')

    # 20: Distribute 40uL Elution buffer (slot 7, column 2) to each well of Zymo collection plate.
    ctx.comment('\n\n~~~~~~~~~~Transfer Elution Buffer to Collection Plate~~~~~~~~\n')
    custom_transfer(40, elution_buffer)

    # 21: Vortex Zymo collection plate (on heater shaker) at 2000 rpm 5 seconds per 30 seconds for 5 minutes.
    ctx.comment('\n\n~~~Shake 5 seconds @ 1800 RPM every 30 seconds for 5 min~~~~~\n')
    hs_mod.close_labware_latch()
    #Do 3 minutes, 1000rpm instead. No loop
    hs_mod.set_and_wait_for_shake_speed(1000)
    ctx.delay(minutes=3)
    '''for i in range (9):
        hs_mod.set_and_wait_for_shake_speed(1000)
        ctx.delay(seconds=5)
        hs_mod.deactivate_heater()
        ctx.delay(seconds=25)
    hs_mod.set_and_wait_for_shake_speed(1800)
    ctx.delay(seconds=5)'''
    hs_mod.deactivate_shaker()
    


    # 22: Move Zymo collection plate from the heater shaker onto the magnetic module and engage magnetics to the height of 3.9mm. Pause for 1 minute.
    hs_mod.open_labware_latch()
    ctx.pause('\n\n~~~~~~~Manually Move Collection Plate to Magnetic Module~~~~~~~\n')
    ctx.move_labware(labware=collection_plate, new_location=mag_mod, use_gripper=False)
    mag_mod.engage(height_from_base=3.9)
    ctx.delay(minutes=settling_time if not dry_run else 0.1, msg='\n\n~~~~Incubating on mag_mod for ' + str(settling_time) + ' minutes~~~~\n')

    # 23: Transfer 30uL liquid from each well of Zymo collection plate into the Elution plate (slot 4). Use new tips.
    ctx.comment('\n\n~~~~~~~~~~Transfer Eluate to Elution Plate~~~~~~~~~~~~~~~~~~~\n')
    elute(30)
    
    ctx.comment('\n\n~~~~~~~~~~~~~~~~~~~Protocol Complete~~~~~~~~~~~~~~~~~~~~~~~~~\n')
