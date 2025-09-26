def get_recommendations(uv_index, skin_type):
    """Rule-based recommendations for UV protection based on skin type and UV level."""
    recs = []
    if uv_index < 3:
        base_spf = "SPF 15+"
    elif uv_index < 6:
        base_spf = "SPF 30+"
    elif uv_index < 8:
        base_spf = "SPF 50+"
    else:
        base_spf = "SPF 50+ e proteção extra"
    
    if skin_type in ["I", "II"]:
        recs.extend([f"Aplique {base_spf} a cada 2 horas.", "Use chapéu e óculos de sol.", "Evite sol das 10h-16h."])
    elif skin_type in ["III", "IV"]:
        recs.extend([f"Aplique {base_spf} a cada 2-3 horas.", "Use roupas de proteção UV.", "Hidrate a pele."])
    else:  # V-VI
        recs.extend([f"Aplique {base_spf} se exposto.", "Monitore hiperpigmentação.", "Use antioxidantes."])
    
    recs.append(f"UV atual: {uv_index} - {'Baixo' if uv_index < 3 else 'Médio' if uv_index < 6 else 'Alto'} risco.")
    return recs