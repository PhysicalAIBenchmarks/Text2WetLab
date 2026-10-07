"""IR + deck -> an Opentrons Python protocol that does exactly what the IR says. The reference solution for every IR task.

    compile_ir(protocol, deck) -> str

It is deliberately plain: one pipette.transfer per step, volumes routed to the right pipette, fresh tips per step, manual
steps become comments. It exists so each task has an oracle that the checker must accept, and so the checker can be
tested against a solution that is correct by construction. It says nothing about what a good protocol looks like.
"""
from paper2protocol.models import Protocol
from paper2protocol.timeline import pairs


def _var(label: str) -> str:
    return "lw_" + "".join(ch if ch.isalnum() else "_" for ch in label)


def compile_ir(proto: Protocol, deck: dict) -> str:
    kinds = {c.name: c.kind for c in proto.containers}
    cont = deck["containers"]

    def real(container, well):
        spec = cont[container]
        return f"{_var(spec['label'])}['{well or spec.get('well', 'A1')}']"

    lines = ["metadata = {'apiLevel': '2.13'}", "", "", "def run(protocol):"]
    for size, t in deck["tips"].items():
        lines.append(f"    tips{size} = protocol.load_labware('{t['load_name']}', {t['slot']})")
    for name, p in deck["pipettes"].items():
        lines.append(f"    p{p['tips']} = protocol.load_instrument('{name}', '{p['mount']}', tip_racks=[tips{p['tips']}])")
    for slot, spec in deck["slots"].items():
        lines.append(f"    {_var(spec['label'])} = protocol.load_labware('{spec['load_name']}', {slot}, label='{spec['label']}')")
    for i, s in enumerate(proto.steps, 1):
        lines.append(f"    # step {i}: {s.kind}")
        lines.append("    p20.reset_tipracks(); p300.reset_tipracks()")
        if s.kind == "transfer" and s.volume_ul:
            ps = pairs(s, kinds)
            assert ps, f"step {i}: source/destination wells do not pair up"
            pip = "p20" if s.volume_ul <= 20 else "p300"
            assert s.volume_ul >= 1, f"step {i}: {s.volume_ul} uL is below the smallest pipette volume"
            mix = f", mix_after=({s.mix_cycles}, {min(s.volume_ul, 300)})" if s.mix_cycles else ""
            if len({p[0] for p in ps}) == 1:
                dests = ", ".join(real(s.dest, d) for _, d in ps)
                lines.append(f"    {pip}.transfer({s.volume_ul}, {real(s.source, ps[0][0])}, [{dests}], new_tip='once'{mix})")
            else:
                srcs = ", ".join(real(s.source, a) for a, _ in ps)
                dests = ", ".join(real(s.dest, d) for _, d in ps)
                lines.append(f"    {pip}.transfer({s.volume_ul}, [{srcs}], [{dests}], new_tip='always'{mix})")
        elif s.kind == "mix" and s.dest:
            vol = s.volume_ul or 20
            pip = "p20" if vol <= 20 else "p300"
            from paper2protocol.check import expand_wells
            for w in expand_wells(s.dest_wells, kinds[s.dest]):
                lines.append(f"    {pip}.pick_up_tip(); {pip}.mix({s.mix_cycles or 3}, {vol}, {real(s.dest, w)}); {pip}.drop_tip()")
        else:
            lines.append(f"    protocol.comment({(s.action or s.note or 'manual step')!r})")
    return "\n".join(lines) + "\n"
