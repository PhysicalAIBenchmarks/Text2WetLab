from unitelabs.labware.azenta import AzentaFluidXTube_1900uL_ExternalThread
from unitelabs.labware.corning_costar import Cos_96_FB
from unitelabs.labware.falcon import Standard15mLTube, Standard50mLTube
from unitelabs.labware.hamilton import (
    PLT_CAR_L5MD_A00, SMP_CAR_12_A00, SMP_CAR_24_A00, SMP_CAR_32_A00, TIP_CAR_480_A00,
    HamiltonTip_10, HamiltonTip_50, HamiltonTip_300, HamiltonTipRack_10, HamiltonTipRack_50, HamiltonTipRack_300,
)
from unitelabs.labware.liquids import PredefinedLiquids

TUBES = ["q5_buffer", "dntp", "q5_pol", "pcr_mm", "rcutsmart", "dpni", "t4_buffer", "gg_enzyme"]
PLATES = ["primer_plate", "template_plate", "pcr_plate", "assembly_plate", "cells_plate"]
FRAGMENTS = [f"{row}1" for row in "ABCDEFG"]            # pcr_plate A1:G1 = fragments 1-7
ASSEMBLIES = ["A1", "B1", "C1", "D1"]


def tip_for(volume):
    return HamiltonTip_10 if volume <= 10 else HamiltonTip_50 if volume <= 50 else HamiltonTip_300


async def run(vantage, comment):
    tips = TIP_CAR_480_A00()
    tips[0] = HamiltonTipRack_10("tips10_1", filled_with=HamiltonTip_10)
    tips[1] = HamiltonTipRack_10("tips10_2", filled_with=HamiltonTip_10)
    tips[2] = HamiltonTipRack_50("tips50_1", filled_with=HamiltonTip_50)
    tips[3] = HamiltonTipRack_50("tips50_2", filled_with=HamiltonTip_50)
    tips[4] = HamiltonTipRack_300("tips300_1", filled_with=HamiltonTip_300)
    vantage.deck.add(tips, track=1)

    plate_carrier = PLT_CAR_L5MD_A00()
    plates = {}
    for site, name in enumerate(PLATES):
        plates[name] = plate_carrier[site] = Cos_96_FB(name)
    vantage.deck.add(plate_carrier, track=7)

    tube_carrier = SMP_CAR_32_A00()
    tubes = {}
    for site, name in enumerate(TUBES):
        tube_carrier[site] = AzentaFluidXTube_1900uL_ExternalThread(name)
        tubes[name] = tube_carrier[site].children[0]
    vantage.deck.add(tube_carrier, track=13)
    lb_carrier = SMP_CAR_24_A00()
    lb_carrier[0] = Standard15mLTube("lb_dextrose")
    tubes["lb_dextrose"] = lb_carrier[0].children[0]
    vantage.deck.add(lb_carrier, track=14)
    water_carrier = SMP_CAR_12_A00()
    water_carrier[0] = Standard50mLTube("water")
    tubes["water"] = water_carrier[0].children[0]
    vantage.deck.add(water_carrier, track=15)

    for name in ("q5_buffer", "dntp", "q5_pol", "rcutsmart", "dpni", "t4_buffer", "gg_enzyme"):
        tubes[name].container.add_liquid(PredefinedLiquids.WATER, 1500)
    tubes["lb_dextrose"].container.add_liquid(PredefinedLiquids.WATER, 13000)
    tubes["water"].container.add_liquid(PredefinedLiquids.WATER, 45000)
    primer, template, pcr = plates["primer_plate"], plates["template_plate"], plates["pcr_plate"]
    assembly, cells = plates["assembly_plate"], plates["cells_plate"]
    for row in "ABCDEFG":
        primer[f"{row}1"].container.add_liquid(PredefinedLiquids.WATER, 50)
        primer[f"{row}2"].container.add_liquid(PredefinedLiquids.WATER, 50)
    for well in ("A1", "B1", "C1", "D1"):
        template[well].container.add_liquid(PredefinedLiquids.WATER, 20)
        cells[well].container.add_liquid(PredefinedLiquids.WATER, 50)

    async def one_tip(volume, source, dests, mix=None):
        """One tip for a stock going to several wells (OT-2 transfer(new_tip='once'))."""
        await vantage.pipettes.pick_up_tips(channels=[0], tip_type=tip_for(max(volume, mix[1] if mix else 0)))
        for dest in dests:
            await vantage.pipettes.aspirate(source, channels=[0], volume=volume)
            await vantage.pipettes.dispense(dest, channels=[0], volume=volume)
        await vantage.pipettes.discard_tips(channels=[0])

    async def tip_each(volume, pairs, mix=None):
        """A fresh tip per source/destination pair (new_tip='always'); mix = (cycles, volume) after dispensing."""
        for source, dest in pairs:
            await vantage.pipettes.pick_up_tips(channels=[0], tip_type=tip_for(volume))
            await vantage.pipettes.aspirate(source, channels=[0], volume=volume)
            if mix:
                await vantage.pipettes.dispense(dest, channels=[0], volume=volume, mix_cycles=mix[0], mix_volume=mix[1])
            else:
                await vantage.pipettes.dispense(dest, channels=[0], volume=volume)
            await vantage.pipettes.discard_tips(channels=[0])

    async def mix(wells, cycles, volume):
        for well in wells:
            await vantage.pipettes.pick_up_tips(channels=[0], tip_type=tip_for(volume))
            for _ in range(cycles):
                await vantage.pipettes.aspirate(well, channels=[0], volume=volume)
                await vantage.pipettes.dispense(well, channels=[0], volume=volume)
            await vantage.pipettes.discard_tips(channels=[0])

    frag = [pcr[w] for w in FRAGMENTS]
    asm = [assembly[w] for w in ASSEMBLIES]
    mm = tubes["pcr_mm"]

    # PCR master mix, then the seven fragment PCRs
    await one_tip(106, tubes["water"], [mm])
    await one_tip(40, tubes["q5_buffer"], [mm])
    await one_tip(4, tubes["dntp"], [mm])
    await one_tip(2, tubes["q5_pol"], [mm])
    await mix([mm], 5, 100)
    await one_tip(19, mm, frag)
    await tip_each(2.5, zip([primer[f"{r}1"] for r in "ABCDEFG"], frag))
    await tip_each(2.5, zip([primer[f"{r}2"] for r in "ABCDEFG"], frag))
    await tip_each(1, zip([template[w] for w in ("A1", "A1", "B1", "C1", "A1", "A1", "D1")], frag))
    await mix(frag, 3, 15)
    comment("Seal pcr_plate (or move the PCR tubes) and transfer manually to the Bio-Rad C100 gradient thermocycler. "
            "Run: 98°C 30 s; 34 cycles of 98°C 10 s, annealing 30 s at the AssemblyTron/j5 optimal-gradient temperature "
            "for each fragment, 72°C extension at the time set by AssemblyTron (about 20-30 s/kb); final extension 72°C "
            "5 min; hold 4°C. Take a sample of each reaction for gel electrophoresis, then return to the Vantage.")

    # DpnI digest
    await one_tip(19, tubes["water"], frag)
    await one_tip(5, tubes["rcutsmart"], frag)
    await one_tip(1, tubes["dpni"], frag)
    await mix(frag, 3, 30)
    comment("Incubate pcr_plate A1:G1 at 37°C for 30 min, then 65°C for 20 min (DpnI inactivation) on the thermocycler block.")
    comment("Pause the protocol. Clean and concentrate each of the 7 fragments with a Zymo DNA Clean & Concentrator-5 "
            "column: 5:1 DNA Binding Buffer to sample (250 µL per 50 µL), spin 30 s, wash 2 x 200 µL DNA Wash Buffer "
            "(30 s spins), elute in 20 µL water after 1 min at room temperature (30 s spin). Return the eluted fragments "
            "to their original positions pcr_plate A1:G1 (fragments 1-7) and resume the protocol.")

    # Golden Gate assembly
    await one_tip(7, tubes["water"], asm)
    await one_tip(2, tubes["t4_buffer"], asm)
    await one_tip(3, pcr["B1"], asm)
    await one_tip(2, pcr["E1"], asm)
    await one_tip(3, pcr["F1"], asm)
    await tip_each(2, zip([pcr[w] for w in ("A1", "C1", "D1", "G1")], asm))
    await tip_each(1, [(tubes["gg_enzyme"], a) for a in asm], mix=(5, 1))
    comment("Run Golden Gate program on assembly_plate in a thermocycler: 30 cycles of 37°C 5 min then 16°C 5 min; "
            "then 60°C 5 min; hold at 4°C. Lid about 85°C.")
    comment("Clean and concentrate each assembly with a Zymo DNA Clean & Concentrator-5 column (5:1 binding buffer, "
            "2 x 200 µL wash) and elute in 10 µL molecular grade water; return the eluates to assembly_plate A1:D1.")

    # Transformation
    await tip_each(5, zip(asm, [cells[w] for w in ASSEMBLIES]))
    comment("Measure DNA concentration of the remaining 5 µL of each eluate with a NanoDrop-2000c for CFU/µg calculation.")
    comment("Incubate cells_plate A1:D1 for 30 min on ice, heat shock at 42°C for 60 s, then return to ice for about 2 min.")
    await one_tip(250, tubes["lb_dextrose"], [cells[w] for w in ASSEMBLIES])
    comment("Recover cells at 37°C for 60 min with shaking (about 250 rpm).")
    comment("Plate 50-200 µL of each recovery (neat or a 10x dilution, depending on predicted efficiency) onto separate "
            "LB agar plates containing kanamycin 50 µg/mL; incubate at 37°C overnight.")
    comment("Manually count colonies per plate and score the fraction showing the expected chromoprotein colour "
            "(purple, orange, blue, green); report CFU/µg of DNA plated.")
