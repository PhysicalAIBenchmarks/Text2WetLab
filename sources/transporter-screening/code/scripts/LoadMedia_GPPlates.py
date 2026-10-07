          

   
metadata = {
    'protocolName': 'GP Load Glycerol Droplets',
    'author': 'Lachlan <lajamu@biosustain.dtu.dk',
    'source': 'DTU Biosustain',
    'apiLevel': '2.2'
}


def run(protocol):
    
        #Load Tips
        tips300  = [protocol.load_labware('opentrons_96_tiprack_300ul', slot) for slot in [1]]
        
        #Load Pipettes
        p300Multi = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=tips300)
        
        #Load labware
        plates = [
                protocol.load_labware("gp_plate_96", slot)
                for slot in [ 2, 3, 4, 6, 8]]
        

        reservoir = protocol.load_labware("agilent_1_reservoir_290ml", 5)

        #Innoculate

        def load(src, dst):
        	p300Multi.transfer(297, src, dst.top(), rate=0.5, new_tip="never")

        p300Multi.pick_up_tip()
        for p in plates:
        	for col in p.columns():
        	    load(reservoir["A1"], col[0])














        
