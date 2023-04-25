import json


def parse_geojson_off_beach(filename):
    content = None
    coords = []
    coords_center = []
    with open(filename) as file:
        content = json.load(file)
        for i in range(4):
            coords.append(content.get("features")[i].get("geometry").get("coordinates"))

    for j in range(len(coords)):
        for k in range(len(coords[j])):
            coords_center.append(coords[j][k][4])
    return coords_center
