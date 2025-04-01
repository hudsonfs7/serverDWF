from flask import Flask, request, send_file
import ezdxf
import simplekml
from pyproj import Transformer
import os

app = Flask(__name__)

# Função para converter DXF para KML
def dxf_to_kml(dxf_filename, kml_filename):
    print("Iniciando a leitura do arquivo DXF...")
    doc = ezdxf.readfile(dxf_filename)
    msp = doc.modelspace()
    kml = simplekml.Kml()

    # Converter de UTM Zona 24S (EPSG:32724) para WGS84 (EPSG:4326)
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

# Rota para fazer o upload do arquivo DXF e gerar o KML
@app.route('/convert', methods=['POST'])
def convert():
    # Verifica se o arquivo foi enviado
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    
    # Verifica se o arquivo tem nome
    if file.filename == '':
        return 'No selected file', 400

    # Salva o arquivo DXF temporariamente
    dxf_filename = 'temp.dxf'
    file.save(dxf_filename)
    
    # Nome do arquivo KML de saída
    kml_filename = 'output.kml'
    
    # Converte o DXF para KML
    dxf_to_kml(dxf_filename, kml_filename)
    
    # Apaga o arquivo DXF temporário
    os.remove(dxf_filename)
    
    # Envia o arquivo KML gerado como resposta
    return send_file(kml_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

