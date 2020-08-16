from json import dump
from math import sqrt
from sys import argv

import cv2
import numpy as np


def line_length(line: np.ndarray):
    x1, y1, x2, y2 = line[0]
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def line_to_dict(line: np.ndarray, width: float, height: float):
    line = line[0]
    return {
        "start_x": line[0] / width,
        "start_y": line[1] / height,
        "end_x": line[2] / width,
        "end_y": line[3] / height
    }


def main(args):
    if len(args) != 2:
        print("Usage of this program:\npython find_paths.py <.png file path> <.json output pat>")
        return

    file_path = args[0]
    output_path = args[1]

    img = cv2.imread(file_path)
    height, width = img.shape[:-1]
    gray_scale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    kernel_size = 5
    blur_gray = cv2.GaussianBlur(gray_scale, (kernel_size, kernel_size), 0)

    low_threshold = 50
    high_threshold = 150
    edges = cv2.Canny(blur_gray, low_threshold, high_threshold)

    rho = 1
    theta = np.pi / 180
    threshold = 15
    min_line_length = 20
    max_line_gap = 5
    lines = list(cv2.HoughLinesP(edges, rho, theta, threshold, np.array([]), min_line_length, max_line_gap))
    lines.sort(key=line_length, reverse=True)
    lines = lines[:min(16, len(lines))]
    wall_line = lines.pop(0)
    json = {
        "wall_line": line_to_dict(wall_line, width, height),
        "stick_lines": [line_to_dict(line, width, height) for line in lines]
    }
    with open(output_path, "w") as fp:
        dump(json, fp)


if __name__ == '__main__':
    main(argv[1:])
