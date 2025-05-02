# Part code generator utilities

# Car manufacturers mapping
CAR_MANUFACTURERS = {
    'Acura': 'ACU',
    'Alfa Romeo': 'ALF',
    'Arola': 'ARO',
    'Aston Martin': 'AST',
    'Audi': 'AUD',
    'Autobianchi': 'AUT',
    'BMW': 'BMW',
    'Bricklin': 'BRI',
    'Cadillac': 'CAD',
    'Chevrolet': 'CHE',
    'Chrysler': 'CHR',
    'Dacia': 'DAC',
    'Daewoo': 'DAE',
    'DAF': 'DAF',
    'Daihatsu': 'DAI',
    'Datsun': 'DAT',
    'Dodge': 'DOD',
    'Fiat': 'FIA',
    'Ford': 'FOR',
    'GMC': 'GMC',
    'Honda': 'HON',
    'Hyundai': 'HYU',
    'Infiniti': 'INF',
    'Isuzu': 'ISU',
    'Iveco': 'IVE',
    'Jaguar': 'JAG',
    'Jeep': 'JEE',
    'Kia': 'KIA',
    'Lada': 'LAD',
    'Lancia': 'LAN',
    'Land Rover': 'LAND',
    'Lexus': 'LEX',
    'Mazda': 'MAZ',
    'Mercedes-Benz': 'MER',
    'Mini': 'MIN',
    'Mitsubishi': 'MIT',
    'Nissan': 'NIS',
    'Opel': 'OPE',
    'Peugeot': 'PEU',
    'Porsche': 'POR',
    'Renault': 'REN',
    'Rivian': 'RIV',
    'Seat': 'SEA',
    'Subaru': 'SUB',
    'Suzuki': 'SUZ',
    'Tata': 'TAT',
    'Toyota': 'TOY',
    'Volkswagen': 'VOLK',
    'Volvo': 'VOL'
}

# Quality levels mapping
QUALITY_LEVELS = {
    'ORIGINAL': 'W',
    'SECOND_LEVEL': 'X',
    'THIRD_LEVEL': 'Z'
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
    # Get manufacturer code - case insensitive lookup
    manufacturer_code = None
    for key, value in CAR_MANUFACTURERS.items():
        if key.upper() == manufacturer.upper():
            manufacturer_code = value
            break
    
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
    return [(key, key) for key in CAR_MANUFACTURERS.keys()]

def get_quality_level_options():
    """Return list of tuples for quality level choices"""
    return [
        ('ORIGINAL', 'Original'),
        ('SECOND_LEVEL', 'Second Level'),
        ('THIRD_LEVEL', 'Third Level')
    ] 
