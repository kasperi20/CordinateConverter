import math
import json
import string
import sys
import xml.etree.ElementTree as ET

from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QGridLayout, QLabel, \
    QLineEdit, QFileDialog, QMessageBox


class Areas:
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

class Point:
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)


def parse_xml(xml_file, color: bool):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    if not color:
        latlng_list = []

        for Border in root.findall("Border"):
            border_list = []
            for Point in Border.findall("Point"):
                for Position in Point.findall("Position"):
                    latitude = Position.find("Latitude").text
                    longitude = Position.find("Longitude").text
                    latlng = (latitude, longitude)

                    border_list.append(latlng)

            latlng_list.append(border_list)
        return latlng_list
    else:
        color_list = []

        for Border in root.findall("Border"):
            color = Border.find("Color").text
            color_w_alpha = f"{color}B3".upper()
            color_list.append(color_w_alpha)

        return color_list


# get distance / bearing between 2 points must be in degree,minute format & N/E are positive and S/W negative
def get_distance_azimuth(BullseyeN: float, BullseyeE: float, pointN: float, pointE: float, mag_var: float, negative: bool)-> tuple[float, float]:
    earth_radius = 6371

    bullseye_n = BullseyeN * math.pi/180
    bullseye_e = BullseyeE * math.pi/180

    point_n = pointN * math.pi/180
    point_e = pointE * math.pi/180

    delta_n = point_n - bullseye_n
    delta_e = point_e - bullseye_e

    #get distance in NM
    sin2_dn = math.pow( math.sin(delta_n / 2), 2)
    sin2_de = math.pow( math.sin(delta_e / 2), 2)

    a = sin2_dn + ( math.cos(bullseye_n) * math.cos(point_n) * sin2_de)

    a_sqrt = math.sqrt(a)
    a_sqrt1 = math.sqrt(1 - a)

    distance = 2 * earth_radius * ( math.atan2( a_sqrt, a_sqrt1 ) )

    nautical_mile = round(distance / 1.852 , 2)

    #get Bearing
    azimuth_rad = math.atan2( math.sin(delta_e) * math.cos(point_n), math.cos(bullseye_n) * math.sin(point_n) - (math.sin(bullseye_n) * math.cos(point_n) * math.cos(delta_e)) )

    if negative:
        bearing_unrounded = (azimuth_rad * 180 / math.pi + 360 ) % 360 + mag_var
    else:
        bearing_unrounded = (azimuth_rad * 180 / math.pi + 360) % 360 + mag_var

    bearing = round ( bearing_unrounded, 2)

    bearing_distance = bearing, nautical_mile
    return bearing_distance

# Loop through the list of points and return converted list
def handle_areas(point_list: list, bullseye_latlng: tuple, mag_var: float, negative: bool, color: list):
    areas = len(point_list)
    area_list = []

    for area in range(areas):
        points = []
        for i in point_list[area]:
            result = get_distance_azimuth(bullseye_latlng[0], bullseye_latlng[1], float(i[0]), float(i[1]), mag_var, negative)

            pname = f"Point {i}"
            p1 = Point()
            p1.name = pname
            p1.azimuth = result[0]
            p1.distance = result[1]

            points.append(p1)

        area_color = color[area]
        a1 = Areas()
        a1.name = f"Area {area}"
        a1.points = points
        a1.fill = area_color

        area_list.append(a1)
    return area_list


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cordinate")

        layout = QGridLayout()

        bullseye_info = QLabel("Input Bullseye Lat Long in format Degrees Minutes & S/W as negative numbers")
        font = bullseye_info.font()
        font.setPointSize(12)
        bullseye_info.setFont(font)

        bullseye_lat_label = QLabel("Bullseye latitude:")
        bullseye_lat_label.setFont(font)
        bullseye_lat_box = QLineEdit()
        bullseye_lat_box.setFont(font)
        bullseye_lat_box.setPlaceholderText("0.00000")
        self.bullseye_lat_box = bullseye_lat_box

        bullseye_lng_label = QLabel("Bullseye longitude:")
        bullseye_lng_label.setFont(font)
        bullseye_lng_box = QLineEdit()
        bullseye_lng_box.setFont(font)
        bullseye_lng_box.setPlaceholderText("0.00000")
        self.bullseye_lng_box = bullseye_lng_box

        file_info = QLabel("XML file Path")
        file_info.setFont(font)

        browse_button = QPushButton("Browse")
        browse_button.setFont(font)
        browse_button.clicked.connect(self.browse_clicked)
        file_box = QLineEdit()
        file_box.setFont(font)
        self.file_box = file_box

        mag_var_info = QLabel("Magnetic variation:")
        mag_var_info.setFont(font)
        mag_var_box = QLineEdit()
        mag_var_box.setFont(font)
        mag_var_box.setText("0.0")
        self.mag_var_box = mag_var_box

        button = QPushButton("Run")
        button.setFont(font)
        button.clicked.connect(self.run_clicked)

        layout.addWidget(bullseye_info, 0, 0, 1, 4)
        layout.addWidget(bullseye_lat_label, 1,0)
        layout.addWidget(bullseye_lat_box, 1,1,1,1)
        layout.addWidget(bullseye_lng_label, 2,0)
        layout.addWidget(bullseye_lng_box, 2,1,1,1)
        layout.addWidget(file_info, 3, 0, 1, 2)
        layout.addWidget(file_box, 4, 0, 1, 2)
        layout.addWidget(browse_button, 4, 3)
        layout.addWidget(mag_var_info, 5, 0)
        layout.addWidget(mag_var_box, 5, 1)
        layout.addWidget(button, 6, 0, 1, 4)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def browse_clicked(self, s):
        browse_dialog = QFileDialog(self)
        file_path = browse_dialog.getOpenFileName(self, 'Open file', ".", "XML files (*.xml)")[0]
        print(file_path)
        self.file_box.setText(file_path)

    def run_clicked(self):
        file = self.file_box.text()
        bullseye_lat = self.bullseye_lat_box.text()
        bullseye_lng = self.bullseye_lng_box.text()
        mag_var = float(self.mag_var_box.text())

        if file == "":
            QMessageBox.warning(self, "Warning", "No XML file selected")
            return
        if bullseye_lat == "":
            QMessageBox.warning(self, "Warning", "Bullseye latitude cannot be blank")
            return
        if bullseye_lng == "":
            QMessageBox.warning(self, "Warning", "Bullseye longitude cannot be blank")
            return

        if mag_var < 0:
            run(file, bullseye_lat, bullseye_lng, mag_var, True)
        else:
            run(file, bullseye_lat, bullseye_lng, mag_var, False)


def run(file: string, bullseye_lat: string, bullseye_lng: string, mag_var: float, negative: bool):
    list_of_points = parse_xml(file, False)
    color_list = parse_xml(file, True)

    bullseye_latlng = (float(bullseye_lat), float(bullseye_lng))

    list_of_areas = handle_areas(list_of_points, bullseye_latlng, mag_var, negative, color_list)

    area = Areas()
    area.areas = list_of_areas

    finished_file = Areas()
    finished_file.areas = area

    with open("result.json", "w") as outfile:
        outfile.write(finished_file.toJSON())

if __name__ == '__main__':

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    app.exec()