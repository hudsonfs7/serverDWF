from flask import Flask, request, send_file
import ezdxf
from simplekml import Kml
import os

app = Flask(__name__)

# Função para converter DXF para KML
def dxf_to_kml(dxf_filename, kml_filename):
    doc = ezdxf.readfile(dxf_filename)
    kml = Kml()

    for entity in doc.modelspace():
        if entity.dxftype() == 'LINE':
            kml.newlinestring(name="Line", coords=[(entity.dxf.start.x, entity.dxf.start.y), (entity.dxf.end.x, entity.dxf.end.y)])
        elif entity.dxftype() == 'LWPOLYLINE':
            coords = [(point[0], point[1]) for point in entity.get_points()]
            kml.newlinestring(name="Polyline", coords=coords)

    kml.save(kml_filename)

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
