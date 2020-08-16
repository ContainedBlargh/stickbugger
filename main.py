from json import load
from math import sqrt
from sys import argv
# Colors
from typing import List, Tuple

import numpy as np
from midi2audio import FluidSynth
from midiutil import MIDIFile
from tqdm import tqdm
from vispy import io
from vispy.color import Color
from vispy.scene import SceneCanvas
from vispy.scene.visuals import Image, Line
from subprocess import Popen
from shlex import split as sh_split
import os
import glob

bug_color = "#fffed1"
wall_color = "#8f847c"
bg_color = "#7e7577"

# Line widths
bug_width = 10 / 1920
wall_width = 60 / 1920


def load_reference() -> dict:
    with open("reference.json", "r") as fp:
        return load(fp)


def load_sticks(sticks_path: str) -> dict:
    with open(sticks_path, "r") as fp:
        return load(fp)


def measure_stick(stick: dict) -> float:
    x1 = float(stick["start_x"])
    y1 = float(stick["start_y"])
    x2 = float(stick["end_x"])
    y2 = float(stick["end_y"])
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def to_numpy_arr(stick: dict, width: float, height: float) -> np.ndarray:
    x1 = float(stick["start_x"])
    y1 = float(stick["start_y"])
    x2 = float(stick["end_x"])
    y2 = float(stick["end_y"])
    arr = np.array([[x1 * width, y1 * height], [x2 * width, y2 * height]])
    return arr


def to_vispy_line(
        coords: np.ndarray,
        ln_color: str = None,
        ln_width: int = None
) -> Line:
    global bug_color
    global bug_width
    if ln_color is None:
        ln_color = bug_color
    if ln_width is None:
        ln_width = bug_width
    return Line(
        pos=coords,
        color=Color(ln_color),
        width=ln_width,
        connect="strip",
        method="agg",
        antialias=True
    )


def split_stick(stick: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    delta = stick[1, :] - stick[0, :]
    halfway = stick[0, :] + delta * 0.5
    return np.array([[stick[0, 0], stick[0, 1]],
                     [halfway[0], halfway[1]]]), \
           np.array([[halfway[0], halfway[1]],
                     [stick[1, 0], stick[1, 1]]])


def create_sequence(origin: np.ndarray, destination: np.ndarray, steps: int = 120) -> List[np.ndarray]:
    sequence = [origin]
    distance = destination - origin
    m = distance * (1 / steps)
    for i in range(steps):
        sequence.append(sequence[-1] + m)
    return sequence


def main(args: List[str]):
    global bug_width
    global wall_width
    if len(args) != 3:
        print("Usage of this program:\npython main.py <image file path> <sticks json path> <output .webm path>")
        return

    if not os.path.exists("./frames"):
        os.mkdir("./frames")

    old_frames = glob.glob("./frames/*")
    for f in old_frames:
        os.remove(f)

    img_path: str = args[0]
    sticks_path = args[1]
    output_path = args[2]

    image = io.read_png(img_path)
    height, width = image.shape[:-1]
    bug_width = max(bug_width * width, 4)
    wall_width = max(wall_width * width, 6)

    vp_image = Image(data=image, method='auto')
    canvas = SceneCanvas(keys='interactive', size=(width, height), bgcolor=Color(bg_color))
    view = canvas.central_widget.add_view()
    view.add(vp_image)

    midi = MIDIFile(1)
    track = 0
    channel = 0
    time = 0
    duration = 0.25
    tempo = 60
    volume = 100
    midi.addTempo(track, time, tempo)
    m_idx = 50

    frame = 0
    for i in tqdm(range(30*2)):
        img = canvas.render()
        io.write_png(f"frames/frame{frame}.png", img)
        frame += 1

    time += duration * 4

    source_data = load_sticks(sticks_path)
    src_msticks = [(measure_stick(stick), to_numpy_arr(stick, width, height)) for stick in source_data["stick_lines"]]
    src_msticks.sort(key=lambda p: p[0], reverse=True)
    src_wall = to_numpy_arr(source_data["wall_line"], width, height)

    n = len(src_msticks)

    reference_data = load_reference()
    ref_msticks = [(measure_stick(stick), to_numpy_arr(stick, width, height)) for stick in
                   reference_data["stick_lines"]]
    ref_msticks.sort(key=lambda p: p[0], reverse=True)
    ref_wall = to_numpy_arr(reference_data["wall_line"], width, height)
    m = len(ref_msticks)

    print("Balancing sticks...")

    if n < m:
        i = 0
        while n < m:
            largest = src_msticks.pop(i)[1]
            (a, b) = split_stick(largest)
            src_msticks.append((-1, a))
            src_msticks.append((-1, b))
            n += 1
            i += 1
    elif n > m:
        i = 0
        while n > m:
            largest = ref_msticks.pop(i)[1]
            (a, b) = split_stick(largest)
            ref_msticks.append((-1, a))
            ref_msticks.append((-1, b))
            m += 1
            i += 1

    src_sticks = list(zip(*src_msticks))[1]
    ref_sticks = list(zip(*ref_msticks))[1]

    pairs = list(zip(src_sticks, ref_sticks))
    sticks = [to_vispy_line(stick) for stick in src_sticks]

    print("Rendering initial sticks and playing the Xylophone...")

    for i, stick in enumerate(sticks):
        for _ in range(15):
            img = canvas.render()
            io.write_png(f"frames/frame{frame}.png", img)
            frame += 1
        view.add(stick)
        for _ in range(15):
            img = canvas.render()
            io.write_png(f"frames/frame{frame}.png", img)
            frame += 1
        midi.addNote(track, channel, m_idx, time, duration, volume)
        time += duration * 2
        m_idx += 1

    midi.addNote(track, channel, m_idx + 1, time + 0.5, duration, volume)
    midi.addNote(track, channel, 0, time + duration, duration, volume)

    with open("build-up.mid", "wb") as output_file:
        midi.writeFile(output_file)

    for i in range(4):
        img = canvas.render()
        io.write_png(f"frames/frame{frame}.png", img)
        frame += 1

    wall = to_vispy_line(src_wall, ln_color=wall_color, ln_width=wall_width)
    view.add(wall)

    for i in tqdm(range(60)):
        img = canvas.render()
        io.write_png(f"frames/frame{frame}.png", img)
        frame += 1

    midi.addNote(track, channel, m_idx + 1, time + 1, duration, volume)

    moving_sticks = [create_sequence(src, ref) for (src, ref) in pairs]
    moving_wall = create_sequence(src_wall, ref_wall)

    vp_image.visible = False


    for t in tqdm(range(120)):
        for s, stick in enumerate(sticks):
            stick.set_data(moving_sticks[s][t])
        wall.set_data(moving_wall[t])

        img = canvas.render()
        io.write_png(f"frames/frame{frame}.png", img)
        frame += 1

    print("\nCombining files, this is the last step...")
    pbar = tqdm(total=5)
    print("\nComposing music...")
    fs = Popen(sh_split("fluidsynth -F \"build-up.wav\" ./soundfonts/Xylophone.sf2 ./build-up.mid"))
    fs.wait()
    pbar.update()
    print("\nMerging sound files...")
    merger_cmd = "ffmpeg -hide_banner -loglevel panic -y -i build-up.wav -i transform_noise.wav -filter_complex '[0:0][1:0]concat=n=2:v=0:a=1[out]' -map '[out]' build-up-transform.wav"
    merger = Popen(sh_split(merger_cmd))
    merger.wait()
    pbar.update()
    print("\nMerging frames...")
    render_cmd = f"ffmpeg -hide_banner -loglevel panic -framerate 60 -y -i ./frames/frame%d.png -i build-up-transform.wav -c:v libvpx-vp9 -pix_fmt yuva420p -vf scale=1920:1080 out.webm"
    render = Popen(sh_split(render_cmd))
    render.wait()
    pbar.update()
    print("\nMerging video files... (this takes ages)")
    merger2_cmd = f"ffmpeg -y -hide_banner -loglevel panic -c:v libvpx-vp9 -i out.webm -c:v libvpx-vp9 -i stick_bug_dancing.webm -filter_complex '[0:0][0:1][1:0][1:1]concat=n=2:v=1:a=1[outv][outa]' -map '[outv]' -map '[outa]' {output_path}"
    merger2 = Popen(sh_split(merger2_cmd))
    merger2.wait()
    pbar.update()

    old_frames = glob.glob("./frames/*")
    for f in old_frames:
        os.remove(f)
    pbar.update()
    print("\nAll done!")
    pass


if __name__ == '__main__':
    main(argv[1:])
