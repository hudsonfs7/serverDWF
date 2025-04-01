from flask import Flask, request, send_file, make_response
from flask_cors import CORS
import ezdxf
import simplekml
from pyproj import Transformer
import os

app = Flask(__name__)
CORS(app, resources={r"/convert": {"origins": "*", "methods": ["POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

# ================================================
# NOVAS FUNÇÕES PARA TRADUZIR CORES E ESPESSURAS
# ================================================

def get_effective_color(entity, doc):
    """Obtém a cor efetiva considerando ByLayer/ByBlock"""
    if entity.dxf.color == 256:  # ByLayer
        layer = doc.layers.get(entity.dxf.layer)
        return layer.dxf.color
    return entity.dxf.color

def aci_to_kml(aci):
    """Converte índice de cor ACI (AutoCAD) para formato KML (aabbggrr)"""
    # Mapeamento básico de cores ACI (personalize conforme necessidade)
    aci_rgb = {
        1: (255, 0, 0),     # Vermelho
        2: (255, 255, 0),   # Amarelo
        3: (0, 255, 0),     # Verde
        4: (0, 0, 255),     # Azul
        5: (255, 0, 255),   # Magenta
        6: (0, 255, 255),   # Ciano
        7: (255, 255, 255), # Branco
    }
    r, g, b = aci_rgb.get(aci, (255, 255, 255))  # Default branco
    return simplekml.Color.rgb(r, g, b)  # Formato KML: aabbggrr

def lineweight_to_width(lineweight):
    """Converte espessura do DXF (0.01mm) para pixels no KML"""
    return max(1, int(lineweight * 0.04))  # Ajuste o fator conforme necessário

# ================================================
# FUNÇÃO DE CONVERSÃO PRINCIPAL MODIFICADA
# ================================================

def dxf_to_kml(dxf_filename, kml_filename):
    print("Iniciando a leitura do arquivo DXF...")
    doc = ezdxf.readfile(dxf_filename)
    msp = doc.modelspace()
    kml = simplekml.Kml()

    transformer = Transformer.from_crs("EPSG:32724", "EPSG:4326", always_xy=True)

    print("Processando as entidades do DXF com estilos...")
    for entity in msp.query("LINE LWPOLYLINE POLYLINE CIRCLE ARC POINT"):
        # Obter cor e espessura
        color_aci = get_effective_color(entity, doc)
        kml_color = aci_to_kml(color_aci)
        linewidth = lineweight_to_width(entity.dxf.lineweight)

        # Processar geometria
        if entity.dxftype() == "LINE":
            start = transformer.transform(entity.dxf.start.x, entity.dxf.start.y)
            end = transformer.transform(entity.dxf.end.x, entity.dxf.end.y)
            line = kml.newlinestring(coords=[start, end])
            line.style.linestyle.color = kml_color
            line.style.linestyle.width = linewidth

        elif entity.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
            coords = [transformer.transform(p[0], p[1]) for p in entity.get_points()]
            polyline = kml.newlinestring(coords=coords)
            polyline.style.linestyle.color = kml_color
            polyline.style.linestyle.width = linewidth

        elif entity.dxftype() == "CIRCLE":
            center = transformer.transform(entity.dxf.center.x, entity.dxf.center.y)
            point = kml.newpoint(coords=[center])
            point.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
            point.style.iconstyle.color = kml_color

        elif entity.dxftype() == "POINT":
            location = transformer.transform(entity.dxf.location.x, entity.dxf.location.y)
            point = kml.newpoint(coords=[location])
            point.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
            point.style.iconstyle.color = kml_color

    print("Salvando KML com estilos...")
    kml.save(kml_filename)

# ================================================
# RESTANTE DO CÓDIGO (MANTIDO IGUAL)
# ================================================

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "POST")
    return response

@app.route('/convert', methods=['POST', 'OPTIONS'])
def convert():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file', 400

    dxf_filename = 'temp.dxf'
    file.save(dxf_filename)
    
    kml_filename = 'output.kml'
    dxf_to_kml(dxf_filename, kml_filename)
    
    os.remove(dxf_filename)
    
    response = send_file(kml_filename, as_attachment=True)
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
