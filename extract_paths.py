from json import dump
from sys import argv
from typing import List, Tuple
from xml.etree.ElementTree import parse as parse_xml, Element


def parse_paths(paths: List[Element], width: float, height: float) -> Tuple[dict, List[dict]]:
    def path_width(path: Element) -> float:
        style: str = path.attrib["style"]

        style_attributes = [tuple(attrib.split(":")) for attrib in style.split(";")]
        style_attributes = dict(style_attributes)
        return float(style_attributes["stroke-width"]
                     .replace("px", "")
                     .replace("m", "")
                     .replace("e", "")
                     .replace("pt", "")
                     .replace("c", ""))

    # noinspection PyTypeChecker
    def path_coords(path: Element) -> List[List[float]]:
        d: str = path.attrib["d"]
        coords_string = d.lower()[2:]
        coords_pairs = []
        prev = ""
        relative = d[0] == "m"
        for char in coords_string:
            if char is ' ' and prev[-1].isalpha():
                prev += ','
                continue
            elif char is ' ':
                coords_pairs.append(prev + char)
                prev = ""
            else:
                prev += char
        coords_pairs.append(prev)
        coords_pairs = [pair.split(',') for pair in coords_pairs]
        coords = []
        for pair in coords_pairs:
            coords.append([0.0, 0.0])
            current = coords[-1]
            i = 0
            for coord in pair:
                if coord[0].isdigit() or coord[0] == '-':
                    if relative and len(coords) > 1:
                        current[i] = float(coord) + coords[-2][i]
                    else:
                        current[i] = float(coord)
                elif coord.strip().lower() == "h":
                    current[i + 1] = coords[-2][1]
                    i -= 1
                elif coord.strip().lower() == "v":
                    current[i] = coords[-2][0]
                else:
                    raise ValueError(f"Unknown symbol '{coord.strip()}' in path coords.")
                i += 1
        for coord in coords:
            coord[0] /= width
            coord[1] /= height
        return coords

    def coords_to_dict(coords: List[List[float]]) -> dict:
        return {
            "start_x": coords[0][0],
            "start_y": coords[0][1],
            "end_x": coords[-1][0],
            "end_y": coords[-1][1]
        }

    widths = [path_width(path) for path in paths]
    min_width = min(widths)
    max_width = max(widths)

    if min_width == max_width:
        raise ValueError("Cannot discern between wall and bug, ensure that wall line is thicker than the others.")

    wall_line_idx = widths.index(max_width)
    wall_line = paths.pop(wall_line_idx)
    wall_coords = path_coords(wall_line)
    wall_dict = coords_to_dict(wall_coords)

    sticks_dict = [coords_to_dict(path_coords(path)) for path in paths]

    return wall_dict, sticks_dict


def save_json(output_path: str, wall_line: dict, stick_lines: List[dict]):
    with open(output_path, "w") as fp:
        dump(
            {
                "wall_line": wall_line,
                "stick_lines": stick_lines
            }, fp)
    pass


def main(args: List[str]):
    if len(args) != 2:
        print("Usage of this program:\npython extract_paths <.svg file path> <.json output path>")
        return

    svg_path = args[0]
    output_path = args[1]

    etree = parse_xml(svg_path)
    root: Element = etree.getroot()
    paths: List[Element] = [child for child in root if child.tag.endswith("}path")]
    width = float(root.attrib["width"])
    height = float(root.attrib["height"])
    wall_line, stick_lines = parse_paths(paths, width, height)
    save_json(output_path, wall_line, stick_lines)

    pass


if __name__ == '__main__':
    main(argv[1:])
