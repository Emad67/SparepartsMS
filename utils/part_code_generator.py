# Part code generator utilities

# Car manufacturers mapping
CAR_MANUFACTURERS = {
    'TOYOTA': 'TO',
    'NISSAN': 'NI',
    'HONDA': 'HO',
    'MITSUBISHI': 'MI',
    'MAZDA': 'MA',
    'SUBARU': 'SU',
    'ISUZU': 'IS',
    'SUZUKI': 'SZ',
    'DAIHATSU': 'DA',
    'HINO': 'HI',
    'BMW': 'BW',
}

# Quality levels mapping
QUALITY_LEVELS = {
    'ORIGINAL': 'O',
    'SECOND_LEVEL': 'S',
    'THIRD_LEVEL': 'T'
}

def generate_part_code(manufacturer, quality_level, part_number):
    """
    Generate a part code based on the specified format:
    - First two letters of manufacturer
    - Quality level code (O/S/G/A)
    - Part number
    
    Args:
        manufacturer (str): The car manufacturer name
        quality_level (str): The quality level (OEM/OES/GEN/AFT)
        part_number (str): The part number
        
    Returns:
        str: The generated part code
    """
    # Get manufacturer code
    manufacturer_code = CAR_MANUFACTURERS.get(manufacturer.upper(), '')
    if not manufacturer_code:
        raise ValueError(f"Invalid manufacturer: {manufacturer}")
    
    # Get quality level code
    quality_code = QUALITY_LEVELS.get(quality_level.upper(), '')
    if not quality_code:
        raise ValueError(f"Invalid quality level: {quality_level}")
    
    # Combine all components
    return f"{manufacturer_code}{quality_code}{part_number}"

def get_manufacturer_options():
    """Return list of tuples for manufacturer choices"""
    return [(key, key.title()) for key in CAR_MANUFACTURERS.keys()]

def get_quality_level_options():
    """Return list of tuples for quality level choices"""
    return [
        ('ORIGINAL', 'Original'),
        ('SECOND_LEVEL', 'Second Level'),
        ('THIRD_LEVEL', 'Third Level')
    ] 