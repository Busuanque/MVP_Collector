def get_recommendations(uv_index, skin_type):
    """Get personalized sun protection recommendations."""
    
    # UV level categories
    uv_level = "baixo"
    if uv_index >= 8:
        uv_level = "muito alto"
    elif uv_index >= 6:
        uv_level = "alto"
    elif uv_index >= 3:
        uv_level = "moderado"
    
    # Base recommendations
    recommendations = []
    
    # UV-based recommendations
    if uv_index >= 6:
        recommendations.append("🕶️ Use óculos de sol com proteção UV")
        recommendations.append("👒 Use chapéu ou boné")
        recommendations.append("🏠 Evite exposição entre 10h-16h")
    
    # Skin type specific recommendations
    skin_recommendations = {
        "Tipo I": [
            "🧴 Use protetor solar FPS 50+",
            "⏰ Limite exposição a 10-15 minutos",
            "👕 Use roupas com proteção UV"
        ],
        "Tipo II": [
            "🧴 Use protetor solar FPS 30+",
            "⏰ Limite exposição a 15-20 minutos",
            "👕 Use camiseta em exposição prolongada"
        ],
        "Tipo III": [
            "🧴 Use protetor solar FPS 25+",
            "⏰ Pode se expor até 25-30 minutos",
            "💧 Hidrate a pele após exposição"
        ],
        "Tipo IV": [
            "🧴 Use protetor solar FPS 20+",
            "⏰ Pode se expor até 40 minutos",
            "💧 Mantenha a pele hidratada"
        ],
        "Tipo V": [
            "🧴 Use protetor solar FPS 15+",
            "⏰ Tolerância maior ao sol",
            "💧 Hidrate bem a pele"
        ],
        "Tipo VI": [
            "🧴 Use protetor solar FPS 15+",
            "⏰ Alta tolerância ao sol",
            "💧 Mantenha hidratação"
        ]
    }
    
    # Add skin-specific recommendations
    if skin_type in skin_recommendations:
        recommendations.extend(skin_recommendations[skin_type])
    
    # Add general advice
    recommendations.append("💧 Beba bastante água")
    recommendations.append("🍅 Consuma alimentos ricos em antioxidantes")
    
    return recommendations
