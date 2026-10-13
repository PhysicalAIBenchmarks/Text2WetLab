# Text2WetLab simulator image: runs third-party lab-automation protocols with no hardware and no network.
#   Opentrons OT-2 / Flex : opentrons_simulate (Opentrons 7.5.0, the benchmark's grader version)
#   Hamilton STAR / STARlet, Tecan EVO and others : PyLabRobot simulated backends
# Run untrusted protocol code with:  docker run --rm --network none -v <repo>:/work:ro -v <out>:/out t2w-sim ...
FROM python:3.10-slim
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 OT_SMOOTHIE_ID=AMA
RUN pip install "opentrons==7.5.0" "pylabrobot" numpy pandas
# Opentrons fetches nothing at simulate time once its shared data is installed; warm it so --network none works.
RUN python -c "from opentrons import simulate; print('opentrons ok')" && python -c "import pylabrobot; print('pylabrobot ok')"
COPY runlog.py mylog.py /t2w/
COPY simulate_all.py hamilton_ape.py /t2w/
RUN useradd -m sim
USER sim
WORKDIR /tmp
ENTRYPOINT ["python", "/t2w/simulate_all.py"]
