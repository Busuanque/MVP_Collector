# src/recommendations.py

# Modulo original com imagens
def get_recommendations(uv_index, skin_type):

    # UV level categories
    recommendations = []

    risco = (
        "Alto risco" if uv_index >= 8 else
        "Risco moderado" if uv_index >= 6 else
        "Baixo risco"
    )
    recommendations.append(f"Risco: {risco}")

    if uv_index >= 6:
        recommendations += [
            "Use óculos de sol com proteção UV",
            "Use chapéu ou boné",
            "Evite exposição entre 10h-16h"
        ]

    skin_map = {
        "Tipo I - Pele Muito Clara": [
            "Use protetor solar FPS 50+",
            "Limite exposição a 10-15 minutos",
            "Use roupas com proteção UV"
        ],
        "Tipo II -  Pele Clara": [
            "Use protetor solar FPS 30+",
            "Limite exposição a 15-20 minutos",
            "Use camiseta em exposição prolongada"
        ],
        "Tipo III - Pele Morena Clara": [
            "Use protetor solar FPS 25+",
            "Pode se expor até 25-30 minutos",
            "Hidrate a pele após exposição"
        ],
        "Tipo IV - Pele Morena": [
            "Use protetor solar FPS 20+",
            "Pode se expor até 40 minutos",
            "Mantenha a pele hidratada"
        ],
        "Tipo V - Pele Morena Escura": [
            "Use protetor solar FPS 15+",
            "Tolerância maior ao sol",
            "Hidrate bem a pele"
        ],
        "Tipo VI - Pele Muito Escura": [
            "Use protetor solar FPS 15+",
            "Alta tolerância ao sol",
            "Mantenha hidratação"
        ]
    }
    #recommendations += skin_map.get(skin_type, [])
    recommendations += next((v for k, v in skin_map.items() if skin_type in k),[])

    recommendations.append(f"Beba bastante água")
    recommendations.append(f"Coma alimentos ricos em antioxidantes")
    return recommendations

def format_analysis_html(uv_index, skin_type, recommendations):
    #Gera bloco HTML estruturado para exibir:
    #- Índice UV
    #- Tipo de Pele
    #- Lista de Recomendações
    html = f"<p><strong>Índice UV:</strong> {uv_index:}</p>"
    html += f"<p><strong>Tipo de Pele:</strong> {skin_type}</p>"
    html += "<p><strong>Recomendações:</strong></p><ul>"
    for rec in recommendations:
        html += f"<li>{rec}</li>"
    html += "</ul>"
    return html
    
