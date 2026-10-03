          

   
metadata = {
    'protocolName': 'GP Load Glycerol Droplets',
    'author': 'Lachlan <lajamu@biosustain.dtu.dk',
    'source': 'DTU Biosustain',
    'apiLevel': '2.2'
}


def run(protocol):
    
        #Load Tips
        tips20  = [protocol.load_labware('opentrons_96_tiprack_20ul', slot) for slot in [1]]
        
        #Load Pipettes
        p20Multi = protocol.load_instrument('p20_multi_gen2', 'left', tip_racks=tips20)
        
        #Load labware
        plates = [
                protocol.load_labware("gp_plate_96", slot)
                for slot in [3, 4, 5, 6, 7, 8]]
        
        
        ecoli = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", "2")

        #Innoculate

        def innoculate(col):
            p20Multi.pick_up_tip()
            p20Multi.aspirate(20, ecoli.columns()[col][0])
            for p in plates:
                p20Multi.dispense(3, p.columns()[col][0])
                p20Multi.move_to(p.columns()[col][0].bottom())
            p20Multi.drop_tip()

        for col in range(12):
        	innoculate(col)














        
