from flask import Flask, request, send_file, make_response
from flask_cors import CORS
import ezdxf
import simplekml
from pyproj import Transformer
import os

app = Flask(__name__)
CORS(app, resources={r"/convert": {"origins": "*", "methods": ["POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

# Função para converter DXF para KML (mantida igual)
def dxf_to_kml(dxf_filename, kml_filename):
    print("Iniciando a leitura do arquivo DXF...")
    doc = ezdxf.readfile(dxf_filename)
    msp = doc.modelspace()
    kml = simplekml.Kml()

    transformer = Transformer.from_crs("EPSG:32724", "EPSG:4326", always_xy=True)

    print("Processando as entidades do DXF...")
    for entity in msp.query("LINE LWPOLYLINE POLYLINE CIRCLE ARC POINT"):
        if entity.dxftype() == "LINE":
            x1, y1 = entity.dxf.start.x, entity.dxf.start.y
            x2, y2 = entity.dxf.end.x, entity.dxf.end.y
            lon1, lat1 = transformer.transform(x1, y1)
            lon2, lat2 = transformer.transform(x2, y2)
            kml.newlinestring(coords=[(lon1, lat1), (lon2, lat2)])
        elif entity.dxftype() in ["LWPOLYLINE", "POLYLINE"]:
            coords = []
            for p in entity.get_points():
                lon, lat = transformer.transform(p[0], p[1])
                coords.append((lon, lat))
            kml.newlinestring(coords=coords)
        elif entity.dxftype() == "CIRCLE":
            x, y = entity.dxf.center.x, entity.dxf.center.y
            lon, lat = transformer.transform(x, y)
            kml.newpoint(coords=[(lon, lat)])
        elif entity.dxftype() == "POINT":
            x, y = entity.dxf.location.x, entity.dxf.location.y
            lon, lat = transformer.transform(x, y)
            kml.newpoint(coords=[(lon, lat)])

    print("Salvando o arquivo KML...")
    kml.save(kml_filename)
    print(f"Arquivo KML salvo em: {kml_filename}")

# Handler para requisições OPTIONS (CORS pré-flight)
def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "POST")
    return response

# Rota principal modificada
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
    
    # Headers adicionais para garantir compatibilidade
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
    
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
