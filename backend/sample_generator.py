"""
Generate realistic sample engineering datasheets (PDF) and telemetry/calibration datasets (CSV & JSON)
for immediate student testing in the RAG Engineering Assistant.
"""
import csv
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_bme280_datasheet_pdf(target_path: Path) -> None:
    """Create a multi-page technical datasheet PDF for the Bosch BME280 sensor."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(target_path), pagesize=A4)
    width, height = A4

    # --- PAGE 1: General Description & Electrical Specifications ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 55, "BOSCH BME280 - Capteur Environnemental Numérique (Pression, Humidité, Température)")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 72, "Référence Document : BST-BME280-DS002-15 | Révision Technique : 1.24 | Usage : Projets Systèmes Embarqués")
    c.line(50, height - 80, width - 50, height - 80)

    y = height - 105
    p1_lines = [
        ("Helvetica-Bold", 12, "1. Description Générale et Domaines d'Application"),
        ("Helvetica", 10, "Le BME280 est un capteur environnemental intégré conçu spécifiquement pour les applications mobiles et"),
        ("Helvetica", 10, "les systèmes embarqués à faible consommation énergétique (IoT, stations météo autonomes, drones, domotique)."),
        ("Helvetica", 10, "Il combine des capteurs de haute linéarité et haute précision pour la pression atmosphérique, l'humidité"),
        ("Helvetica", 10, "relative et la température ambiante dans un boîtier métallique LGA à 8 broches compact (2.5 x 2.5 x 0.93 mm)."),
        ("Helvetica", 10, ""),
        ("Helvetica-Bold", 12, "2. Caractéristiques Électriques et Alimentation (Electrical Specifications)"),
        ("Helvetica", 10, "- Tension d'alimentation principale (VDD) : 1.71 V à 3.6 V (nominal typique : 3.3 V)."),
        ("Helvetica", 10, "- Tension d'interface logique (VDDIO) : 1.2 V à 3.6 V (compatible logique 1.8 V et 3.3 V)."),
        ("Helvetica", 10, "- ATTENTION CRITIQUE : Le BME280 n'est PAS tolérant au 5.0 V direct sur ses broches VDD, VDDIO, SDA ou SCL."),
        ("Helvetica", 10, "  Toute connexion directe à un microcontrôleur 5V (ex: Arduino Uno sans convertisseur de niveau logique)"),
        ("Helvetica", 10, "  au-delà de la limite absolue de 4.25 V détruit définitivement l'étage d'entrée CMOS."),
        ("Helvetica", 10, "- Courant consommé en mode Sommeil (Sleep mode) : 0.1 µA typique (0.3 µA maximum à 85 °C)."),
        ("Helvetica", 10, "- Courant consommé en mesure d'humidité + température (1 Hz, Forced Mode) : 2.8 µA typique."),
        ("Helvetica", 10, "- Courant consommé en mesure complète Pression + Humidité + Température (1 Hz) : 3.6 µA typique."),
        ("Helvetica", 10, "- Courant de crête pendant la conversion ADC : 714 µA (pression), 340 µA (humidité), 350 µA (température)."),
        ("Helvetica", 10, ""),
        ("Helvetica-Bold", 12, "3. Performances Métrologiques des Capteurs"),
        ("Helvetica", 10, "- Plage de mesure Température : -40 °C à +85 °C (précision : ±0.5 °C à 25 °C, résolution : 0.01 °C)."),
        ("Helvetica", 10, "- Plage de mesure Humidité Relative : 0 % à 100 % RH (précision : ±3 % RH entre 20 % et 80 % RH)."),
        ("Helvetica", 10, "  Hystérésis humidité : ±1 % RH. Temps de réponse (tau 63%) : 1 seconde."),
        ("Helvetica", 10, "- Plage de mesure Pression Barométrique : 300 hPa à 1100 hPa (précision absolue : ±1.0 hPa entre 0 et 65 °C,"),
        ("Helvetica", 10, "  sensibilité relative : ±0.12 hPa, équivalent à ±1 mètre d'altitude)."),
        ("Helvetica", 10, "- Bruit RMS en pression (filtre IIR coefficient 16, oversampling x16) : 0.2 Pa (soit 1.7 cm d'altitude)."),
        ("Helvetica", 10, ""),
        ("Helvetica-Bold", 12, "4. Limites Absolues (Absolute Maximum Ratings)"),
        ("Helvetica", 10, "- Tension maximale sur VDD et VDDIO : -0.3 V à +4.25 V."),
        ("Helvetica", 10, "- Température de stockage : -45 °C à +85 °C."),
        ("Helvetica", 10, "- Résistance aux pics de pression : jusqu'à 20 000 hPa (20 bar) sans endommagement mécanique."),
        ("Helvetica", 10, "- Protection ESD (Modèle Corps Humain HBM) : ±2 kV."),
    ]

    for font, size, text in p1_lines:
        c.setFont(font, size)
        c.drawString(50, y, text)
        y -= 17

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 35, "Page 1 / 3 - Datasheet Technique BME280 - Document de référence pour projets étudiants")
    c.showPage()

    # --- PAGE 2: Pinout, I2C / SPI Bus & Wiring Guide ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 55, "BOSCH BME280 - Brochage (Pinout), Interfaces I2C / SPI et Schéma de Câblage")
    c.line(50, height - 65, width - 50, height - 65)

    y = height - 95
    p2_lines = [
        ("Helvetica-Bold", 12, "5. Description du Brochage (Pinout Boîtier LGA-8 et Module Breakout)"),
        ("Helvetica", 10, "- Broche 1 (GND) : Masse commune du circuit analogique et numérique."),
        ("Helvetica", 10, "- Broche 2 (CSB) : Chip Select actif à l'état bas pour le mode SPI. Doit être relié à VDDIO pour forcer le mode I2C."),
        ("Helvetica", 10, "  Attention : Si CSB passe à l'état bas (GND) après la mise sous tension, l'interface I2C est désactivée définitivement"),
        ("Helvetica", 10, "  jusqu'au prochain cycle d'alimentation (Power-On Reset) et le composant bascule en mode SPI."),
        ("Helvetica", 10, "- Broche 3 (SDI) : Entrée/Sortie de données I2C (SDA) ou entrée données SPI (MOSI / SDI)."),
        ("Helvetica", 10, "- Broche 4 (SCK) : Horloge série I2C (SCL) ou horloge SPI (SCK). Fréquence max I2C : 3.4 MHz ; SPI : 10 MHz."),
        ("Helvetica", 10, "- Broche 5 (SDO) : Sélection de l'adresse I2C (LSB de l'adresse) ou sortie de données SPI 4 fils (MISO / SDO)."),
        ("Helvetica", 10, "- Broche 6 (VDDIO) : Alimentation des entrées/sorties numériques (1.2 V à 3.6 V)."),
        ("Helvetica", 10, "- Broche 7 (GND) : Masse de référence analogique."),
        ("Helvetica", 10, "- Broche 8 (VDD) : Alimentation principale du cœur analogique (1.71 V à 3.6 V)."),
        ("Helvetica", 10, ""),
        ("Helvetica-Bold", 12, "6. Adressage et Configuration du Bus I2C"),
        ("Helvetica", 10, "L'adresse esclave I2C sur 7 bits dépend de l'état électrique de la broche SDO (Broche 5) :"),
        ("Helvetica", 10, "- Si SDO est connecté à GND (masse) : Adresse I2C = 0x76 (1110110b). C'est la configuration par défaut sur de nombreux modules."),
        ("Helvetica", 10, "- Si SDO est connecté à VDDIO (3.3V) : Adresse I2C = 0x77 (1110111b)."),
        ("Helvetica", 10, "- IMPORTANT : Ne jamais laisser la broche SDO flottante (non connectée), sinon l'adresse I2C devient instable."),
        ("Helvetica", 10, "- Résistances de tirage (Pull-up) : En mode I2C, des résistances pull-up de 4.7 kOhm (typique entre 2.2 kOhm et 10 kOhm)"),
        ("Helvetica", 10, "  sont obligatoires entre SDA et VDDIO ainsi qu'entre SCL et VDDIO."),
        ("Helvetica", 10, "- Capacité de découplage : Placer deux condensateurs céramiques de 100 nF au plus près des broches VDD et VDDIO."),
        ("Helvetica", 10, ""),
        ("Helvetica-Bold", 12, "7. Guide de Câblage avec Microcontrôleurs (ESP32, STM32, Arduino)"),
        ("Helvetica", 10, "- Câblage ESP32 (Logique 3.3V native - Connexion directe) :"),
        ("Helvetica", 10, "  BME280 VDD & VDDIO -> ESP32 3V3 | BME280 GND -> ESP32 GND | BME280 SDI (SDA) -> GPIO 21 | BME280 SCK (SCL) -> GPIO 22."),
        ("Helvetica", 10, "- Câblage STM32 Nucleo (I2C1 en 3.3V) :"),
        ("Helvetica", 10, "  BME280 VDD & VDDIO -> 3V3 | GND -> GND | SDA -> PB9 (D14) | SCL -> PB8 (D15)."),
        ("Helvetica", 10, "- Câblage Arduino Uno / Nano (Logique 5V) :"),
        ("Helvetica", 10, "  Utiliser impérativement un translatateur de niveau logique bidirectionnel (Level Shifter MOSFET BSS138 5V <-> 3.3V)"),
        ("Helvetica", 10, "  sur les lignes SDA (A4) et SCL (A5), et alimenter VDD/VDDIO via un régulateur 3.3V stable."),
    ]

    for font, size, text in p2_lines:
        c.setFont(font, size)
        c.drawString(50, y, text)
        y -= 17

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 35, "Page 2 / 3 - Datasheet Technique BME280 - Document de référence pour projets étudiants")
    c.showPage()

    # --- PAGE 3: Register Map, Modes, Oversampling & Troubleshooting ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 55, "BOSCH BME280 - Registres Internes, Modes de Fonctionnement et Dépannage")
    c.line(50, height - 65, width - 50, height - 65)

    y = height - 95
    p3_lines = [
        ("Helvetica-Bold", 12, "8. Cartographie des Registres Principaux (Register Map)"),
        ("Helvetica", 10, "- Registre 0xD0 (chip_id) : Identifiant matériel en lecture seule. Doit retourner 0x60 pour un véritable BME280."),
        ("Helvetica", 10, "  Note de diagnostic : Si la lecture de 0xD0 retourne 0x58, le composant est un BMP280 (sans capteur d'humidité)."),
        ("Helvetica", 10, "- Registre 0xE0 (reset) : Écrire la valeur 0xB6 déclenche une réinitialisation logicielle complète (Soft Reset en 2 ms)."),
        ("Helvetica", 10, "- Registre 0xF2 (ctrl_hum) : Bits [2:0] osrs_h configurent le suréchantillonnage (oversampling) de l'humidité."),
        ("Helvetica", 10, "  RÈGLE CRITIQUE : Toute modification du registre 0xF2 (ctrl_hum) ne prend effet qu'APRÈS une opération d'écriture"),
        ("Helvetica", 10, "  dans le registre 0xF4 (ctrl_meas). Toujours écrire dans 0xF2 avant d'écrire dans 0xF4."),
        ("Helvetica", 10, "- Registre 0xF3 (status) : Bit 3 (measuring = 1 pendant conversion ADC), Bit 0 (im_update = 1 pendant copie NVM)."),
        ("Helvetica", 10, "- Registre 0xF4 (ctrl_meas) : Bits [7:5] osrs_t (température), Bits [4:2] osrs_p (pression), Bits [1:0] mode."),
        ("Helvetica", 10, "  Modes (bits [1:0]) : 00 = Sleep Mode (repos), 01 ou 10 = Forced Mode (mesure unique puis retour Sleep), 11 = Normal Mode."),
        ("Helvetica", 10, "- Registre 0xF5 (config) : Bits [7:5] t_sb (durée d'attente t_standby en Normal Mode), Bits [4:2] filter (coefficient IIR)."),
        ("Helvetica", 10, "- Registres 0xF7 à 0xFE : Données brutes de mesure (0xF7..0xF9 = Pression 20 bits, 0xFA..0xFC = Température 20 bits,"),
        ("Helvetica", 10, "  0xFD..0xFE = Humidité 16 bits). Utiliser une lecture groupée (burst read de 8 octets de 0xF7 à 0xFE) pour garantir"),
        ("Helvetica", 10, "  la cohérence temporelle des octets MSB/LSB."),
        ("Helvetica", 10, "- Registres de calibration usine : 0x88 à 0xA1 et 0xE1 à 0xF0 (coefficients dig_T1..T3, dig_P1..P9, dig_H1..H6)."),
        ("Helvetica", 10, ""),
        ("Helvetica-Bold", 12, "9. Profils de Configuration Recommandés selon le Projet Étudiant"),
        ("Helvetica", 10, "- Station Météo Basse Consommation : Mode Forced (1 éch/min), Oversampling P x1, T x1, H x1, Filtre IIR Off (consommation ~0.16 µA)."),
        ("Helvetica", 10, "- Navigation Drone / Altimètre Précis : Mode Normal (t_standby = 0.5 ms), Oversampling P x16, T x2, H x1, Filtre IIR coeff 16."),
        ("Helvetica", 10, "- Régulation Intérieure / CVC (HVAC) : Mode Normal (t_standby = 1000 ms), Oversampling P x2, T x1, H x1, Filtre IIR coeff 4."),
        ("Helvetica", 10, ""),
        ("Helvetica-Bold", 12, "10. Guide de Dépannage Matériel et Logiciel (Troubleshooting)"),
        ("Helvetica", 10, "- Symptôme 1 : Le capteur ne répond pas sur le bus I2C (NACK) -> Vérifier que CSB est bien tiré à VDDIO (3.3V),"),
        ("Helvetica", 10, "  tester les deux adresses 0x76 et 0x77, et vérifier la présence des résistances pull-up de 4.7 kOhm."),
        ("Helvetica", 10, "- Symptôme 2 : L'humidité reste bloquée à 0 % ou 0x8000 -> Soit le registre 0xF2 (ctrl_hum) a été écrit APRÈS 0xF4,"),
        ("Helvetica", 10, "  soit le composant est en réalité un BMP280 (vérifier 0xD0 : 0x60 = BME280, 0x58 = BMP280)."),
        ("Helvetica", 10, "- Symptôme 3 : La température mesurée est supérieure de +2 °C à +3 °C à la température réelle -> Auto-échauffement"),
        ("Helvetica", 10, "  causé par le régulateur LDO ou le microcontrôleur voisin sur le PCB. Éloigner le capteur et utiliser le Forced Mode."),
    ]

    for font, size, text in p3_lines:
        c.setFont(font, size)
        c.drawString(50, y, text)
        y -= 16

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 35, "Page 3 / 3 - Datasheet Technique BME280 - Document de référence pour projets étudiants")
    c.showPage()
    c.save()


def generate_bme280_dataset_csv(target_path: Path) -> None:
    """Create a realistic engineering validation & calibration dataset CSV for BME280."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "essai_id": "EXP-01",
            "mode_fonctionnement": "Sleep_Mode",
            "tension_vdd_v": 3.30,
            "oversampling_config": "aucun (0x00)",
            "filtre_iir_coeff": 0,
            "frequence_echantillonnage_hz": 0.0,
            "courant_moyen_ua": 0.11,
            "temp_reference_c": 25.00,
            "temp_bme280_c": None,
            "erreur_temp_c": None,
            "humidite_ref_rh": 50.0,
            "humidite_bme280_rh": None,
            "pression_bme280_hpa": None,
            "bruit_rms_pression_pa": None,
            "diagnostic_banc": "Repos nominal conforme datasheet (< 0.3 uA)"
        },
        {
            "essai_id": "EXP-02",
            "mode_fonctionnement": "Forced_Meteo",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x1 T:x1 H:x1",
            "filtre_iir_coeff": 0,
            "frequence_echantillonnage_hz": 0.0167,
            "courant_moyen_ua": 0.18,
            "temp_reference_c": 22.40,
            "temp_bme280_c": 22.48,
            "erreur_temp_c": 0.08,
            "humidite_ref_rh": 48.0,
            "humidite_bme280_rh": 48.6,
            "pression_bme280_hpa": 1013.25,
            "bruit_rms_pression_pa": 1.35,
            "diagnostic_banc": "Optimal pour station météo sur batterie LiFePO4 (1 mesure/minute)"
        },
        {
            "essai_id": "EXP-03",
            "mode_fonctionnement": "Forced_Standard_1Hz",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x1 T:x1 H:x1",
            "filtre_iir_coeff": 0,
            "frequence_echantillonnage_hz": 1.0,
            "courant_moyen_ua": 3.62,
            "temp_reference_c": 25.00,
            "temp_bme280_c": 25.12,
            "erreur_temp_c": 0.12,
            "humidite_ref_rh": 55.0,
            "humidite_bme280_rh": 55.8,
            "pression_bme280_hpa": 1012.90,
            "bruit_rms_pression_pa": 1.30,
            "diagnostic_banc": "Consommation conforme au nominal 3.6 uA à 1 Hz"
        },
        {
            "essai_id": "EXP-04",
            "mode_fonctionnement": "Normal_HVAC_Intérieur",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x2 T:x1 H:x1",
            "filtre_iir_coeff": 4,
            "frequence_echantillonnage_hz": 1.0,
            "courant_moyen_ua": 4.95,
            "temp_reference_c": 21.00,
            "temp_bme280_c": 21.15,
            "erreur_temp_c": 0.15,
            "humidite_ref_rh": 45.0,
            "humidite_bme280_rh": 44.3,
            "pression_bme280_hpa": 1014.10,
            "bruit_rms_pression_pa": 0.55,
            "diagnostic_banc": "Filtrage IIR coeff 4 efficace contre les courants d'air de ventilation"
        },
        {
            "essai_id": "EXP-05",
            "mode_fonctionnement": "Normal_Drone_Altimetre",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x16 T:x2 H:x1",
            "filtre_iir_coeff": 16,
            "frequence_echantillonnage_hz": 25.0,
            "courant_moyen_ua": 635.0,
            "temp_reference_c": 25.00,
            "temp_bme280_c": 25.45,
            "erreur_temp_c": 0.45,
            "humidite_ref_rh": 50.0,
            "humidite_bme280_rh": 49.1,
            "pression_bme280_hpa": 1008.40,
            "bruit_rms_pression_pa": 0.21,
            "diagnostic_banc": "Précision altimétrique ±1.7 cm (bruit RMS 0.21 Pa), idéal maintien altitude drone"
        },
        {
            "essai_id": "EXP-06",
            "mode_fonctionnement": "Normal_Continu_Max",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x16 T:x16 H:x16",
            "filtre_iir_coeff": 16,
            "frequence_echantillonnage_hz": 15.0,
            "courant_moyen_ua": 710.0,
            "temp_reference_c": 25.00,
            "temp_bme280_c": 27.35,
            "erreur_temp_c": 2.35,
            "humidite_ref_rh": 50.0,
            "humidite_bme280_rh": 43.2,
            "pression_bme280_hpa": 1013.05,
            "bruit_rms_pression_pa": 0.19,
            "diagnostic_banc": "ANOMALIE AUTO-ÉCHAUFFEMENT (+2.35 °C) et baisse artificielle d'humidité (-6.8 % RH) dus aux conversions continues"
        },
        {
            "essai_id": "EXP-07",
            "mode_fonctionnement": "Forced_Basse_Tension",
            "tension_vdd_v": 1.80,
            "oversampling_config": "P:x1 T:x1 H:x1",
            "filtre_iir_coeff": 0,
            "frequence_echantillonnage_hz": 1.0,
            "courant_moyen_ua": 3.45,
            "temp_reference_c": 20.00,
            "temp_bme280_c": 20.04,
            "erreur_temp_c": 0.04,
            "humidite_ref_rh": 60.0,
            "humidite_bme280_rh": 60.5,
            "pression_bme280_hpa": 1015.00,
            "bruit_rms_pression_pa": 1.28,
            "diagnostic_banc": "Fonctionnement nominal sous alimentation 1.8V (limite basse VDD = 1.71V)"
        },
        {
            "essai_id": "EXP-08",
            "mode_fonctionnement": "Chambre_Froide_-20C",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x4 T:x2 H:x2",
            "filtre_iir_coeff": 4,
            "frequence_echantillonnage_hz": 1.0,
            "courant_moyen_ua": 9.80,
            "temp_reference_c": -20.00,
            "temp_bme280_c": -20.65,
            "erreur_temp_c": -0.65,
            "humidite_ref_rh": 35.0,
            "humidite_bme280_rh": 36.4,
            "pression_bme280_hpa": 1020.10,
            "bruit_rms_pression_pa": 0.48,
            "diagnostic_banc": "Conforme à l'enveloppe thermique basse (-40 °C à +85 °C)"
        },
        {
            "essai_id": "EXP-09",
            "mode_fonctionnement": "Etuve_Chaude_+75C",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x4 T:x2 H:x2",
            "filtre_iir_coeff": 4,
            "frequence_echantillonnage_hz": 1.0,
            "courant_moyen_ua": 11.40,
            "temp_reference_c": 75.00,
            "temp_bme280_c": 75.55,
            "erreur_temp_c": 0.55,
            "humidite_ref_rh": 25.0,
            "humidite_bme280_rh": 25.9,
            "pression_bme280_hpa": 995.60,
            "bruit_rms_pression_pa": 0.52,
            "diagnostic_banc": "Dérive thermique maîtrisée (+0.55 °C à 75 °C)"
        },
        {
            "essai_id": "EXP-10",
            "mode_fonctionnement": "Erreur_Ordre_Registres",
            "tension_vdd_v": 3.30,
            "oversampling_config": "P:x1 T:x1 H:x1 (0xF2 écrit après 0xF4)",
            "filtre_iir_coeff": 0,
            "frequence_echantillonnage_hz": 1.0,
            "courant_moyen_ua": 2.90,
            "temp_reference_c": 24.00,
            "temp_bme280_c": 24.10,
            "erreur_temp_c": 0.10,
            "humidite_ref_rh": 52.0,
            "humidite_bme280_rh": 0.0,
            "pression_bme280_hpa": 1013.40,
            "bruit_rms_pression_pa": 1.31,
            "diagnostic_banc": "ERREUR LOGICIELLE : Registre ctrl_hum (0xF2) écrit après ctrl_meas (0xF4), mesure d'humidité ignorée (0.0 % RH)"
        }
    ]

    fieldnames = list(rows[0].keys())
    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_components_compatibility_json(target_path: Path) -> None:
    """Create a secondary dataset (JSON) comparing sensor parameters and MCU bus compatibility."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "composant_ref": "BOSCH-BME280",
            "categorie": "Capteur environnemental P/T/RH",
            "tension_alimentation_v": "1.71 - 3.6 V (VDD), 1.2 - 3.6 V (VDDIO)",
            "tolerance_5v": "Non (Destruction > 4.25 V)",
            "bus_supportes": "I2C (0x76, 0x77 jusqu'à 3.4 MHz), SPI (3 et 4 fils jusqu'à 10 MHz)",
            "identifiant_registre_0xD0": "0x60",
            "consommation_1hz_ua": 3.6,
            "recommandation_projet": "Idéal pour station météo IoT ESP32/STM32 et altimètre drone"
        },
        {
            "composant_ref": "BOSCH-BMP280",
            "categorie": "Capteur barométrique P/T (Sans humidité)",
            "tension_alimentation_v": "1.71 - 3.6 V (VDD), 1.2 - 3.6 V (VDDIO)",
            "tolerance_5v": "Non (Destruction > 4.25 V)",
            "bus_supportes": "I2C (0x76, 0x77), SPI (jusqu'à 10 MHz)",
            "identifiant_registre_0xD0": "0x58",
            "consommation_1hz_ua": 2.7,
            "recommandation_projet": "Souvent confondu avec le BME280 sur les modules étudiants. Vérifier 0xD0 == 0x58."
        },
        {
            "composant_ref": "SENSIRION-SHT31-D",
            "categorie": "Capteur humidité et température haute précision",
            "tension_alimentation_v": "2.15 - 5.5 V",
            "tolerance_5v": "Oui (Compatible nativement Arduino 5V et ESP32 3.3V)",
            "bus_supportes": "I2C uniquement (Adresses 0x44 par défaut, 0x45 si ADR = VDD)",
            "identifiant_registre_0xD0": "N/A (Commande I2C 16 bits 0xF32D pour Status)",
            "consommation_1hz_ua": 17.0,
            "recommandation_projet": "Alternative directe compatible 5V si le projet n'exige pas la pression atmosphérique"
        },
        {
            "composant_ref": "TEXAS-INSTRUMENTS-INA219",
            "categorie": "Moniteur de courant et puissance High-Side I2C",
            "tension_alimentation_v": "3.0 - 5.5 V (Tension de bus mesurée : 0 à 26 V)",
            "tolerance_5v": "Oui (Alimentation logique 3.3V ou 5V)",
            "bus_supportes": "I2C (16 adresses configurables de 0x40 à 0x4F via A0/A1)",
            "identifiant_registre_0xD0": "Registre Config 0x00 = 0x399F au reset",
            "consommation_1hz_ua": 700.0,
            "recommandation_projet": "Recommandé pour mesurer la consommation énergétique réelle du système étudiant"
        }
    ]
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_sample_files(samples_dir: Path) -> dict[str, Path]:
    """Ensure all sample datasheets and datasets exist on disk."""
    samples_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = samples_dir / "BME280_Datasheet_Technique_FR.pdf"
    csv_path = samples_dir / "BME280_Dataset_Essais_Calibration.csv"
    json_path = samples_dir / "Comparatif_Composants_Capteurs_I2C.json"

    if not pdf_path.exists():
        generate_bme280_datasheet_pdf(pdf_path)
    if not csv_path.exists():
        generate_bme280_dataset_csv(csv_path)
    if not json_path.exists():
        generate_components_compatibility_json(json_path)

    return {
        "datasheet_pdf": pdf_path,
        "dataset_csv": csv_path,
        "dataset_json": json_path,
    }


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent / "data" / "samples"
    paths = ensure_sample_files(base)
    for k, p in paths.items():
        print(f"Generated {k}: {p} ({p.stat().st_size} bytes)")
