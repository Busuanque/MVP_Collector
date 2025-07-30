def get_recommendations(fitzpatrick_type, uv_index):
    """Return skin cancer prevention recommendations in Portuguese based on Fitzpatrick type and UV index."""
    # Map Fitzpatrick types to descriptions in Portuguese
    skin_type_map = {
        "Type I-II (Light)": "Tipo I-II (Pele clara)",
        "Type III-IV (Medium to olive)": "Tipo III-IV (Pele média a oliva)",
        "Type V-VI (Dark)": "Tipo V-VI (Pele escura)"
    }
    skin_type = skin_type_map.get(fitzpatrick_type, fitzpatrick_type)

    # UV index risk levels
    if uv_index < 3:
        risk_level = "baixo"
        base_recommendation = "Risco UV baixo: A exposição ao sol é geralmente segura, mas use protetor solar (FPS 15+) para proteção adicional."
    elif 3 <= uv_index < 6:
        risk_level = "moderado"
        base_recommendation = "Risco UV moderado: Use protetor solar (FPS 30+), chapéu e óculos de sol. Evite o sol entre as 10h e as 16h."
    elif 6 <= uv_index < 8:
        risk_level = "alto"
        base_recommendation = "Risco UV alto: Use protetor solar (FPS 50+), chapéu, óculos de sol e roupa protetora. Evite o sol entre as 10h e as 16h."
    else:
        risk_level = "muito alto"
        base_recommendation = "Risco UV muito alto: Evite a exposição ao sol, especialmente entre as 10h e as 16h. Use protetor solar (FPS 50+), chapéu, óculos de sol e roupa de manga longa."

    # Skin type-specific advice
    if "Tipo I-II" in skin_type:
        skin_advice = "A sua pele clara queima facilmente. Use sempre protetor solar e limite a exposição ao sol."
    elif "Tipo III-IV" in skin_type:
        skin_advice = "A sua pele média bronzeia, mas pode queimar. Use protetor solar e evite exposição prolongada ao sol."
    else:  # Tipo V-VI
        skin_advice = "A sua pele escura tem maior proteção natural, mas ainda requer protetor solar para reduzir riscos."

    return f"{base_recommendation}\n{skin_advice}"