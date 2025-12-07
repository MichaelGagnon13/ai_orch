"""
Bridge minimal pour contrôler FreeCAD via Python API.
Crée des objets 3D de base comme des boîtes.
"""

import logging
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FreeCadObject:
    """Représente un objet FreeCAD créé."""

    name: str
    object_type: str
    properties: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class FreeCadBridge:
    """Bridge minimal pour FreeCAD."""

    def __init__(self, freecad_path: Optional[str] = None):
        """
        Initialise le bridge FreeCAD.

        Args:
            freecad_path: Chemin vers l'installation FreeCAD (optionnel)
        """
        self.freecad_path = freecad_path
        self.FreeCAD = None
        self.doc = None
        self.is_connected = False

    def connect(self) -> bool:
        """
        Se connecte à FreeCAD en important les modules nécessaires.

        Returns:
            True si la connexion réussit, False sinon
        """
        try:
            # Tentative d'importation directe
            try:
                import FreeCAD
                import Part

                self.FreeCAD = FreeCAD
                self.Part = Part
                logger.info("FreeCAD importé avec succès (installation système)")

            except ImportError:
                # Tentative avec chemin personnalisé
                if self.freecad_path:
                    freecad_lib_path = Path(self.freecad_path) / "lib"
                    if freecad_lib_path.exists():
                        sys.path.insert(0, str(freecad_lib_path))
                        import FreeCAD
                        import Part

                        self.FreeCAD = FreeCAD
                        self.Part = Part
                        logger.info(f"FreeCAD importé depuis {self.freecad_path}")
                    else:
                        raise ImportError(f"Chemin FreeCAD invalide: {self.freecad_path}")
                else:
                    raise ImportError("FreeCAD non trouvé et aucun chemin fourni")

            # Création d'un nouveau document
            self.doc = self.FreeCAD.newDocument("TempDoc")
            self.is_connected = True

            logger.info("Connexion FreeCAD établie avec succès")
            return True

        except Exception as e:
            logger.error(f"Échec de connexion à FreeCAD: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        """Ferme la connexion FreeCAD."""
        try:
            if self.doc and self.FreeCAD:
                self.FreeCAD.closeDocument(self.doc.Name)
                logger.info("Document FreeCAD fermé")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture: {e}")

    def create_box(
        self,
        name: str = "Box",
        length: float = 10.0,
        width: float = 10.0,
        height: float = 10.0,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
    ) -> FreeCadObject:
        """
        Crée une boîte dans FreeCAD.

        Args:
            name: Nom de la boîte
            length: Longueur (X)
            width: Largeur (Y)
            height: Hauteur (Z)
            x, y, z: Position

        Returns:
            FreeCadObject avec les détails de la boîte créée
        """
        if not self.is_connected:
            return FreeCadObject(
                name=name,
                object_type="Box",
                properties={},
                success=False,
                error_message="Non connecté à FreeCAD",
            )

        try:
            # Création de la boîte
            box = self.doc.addObject("Part::Box", name)
            box.Length = length
            box.Width = width
            box.Height = height
            box.Placement.Base = self.FreeCAD.Vector(x, y, z)

            # Recalcul du document
            self.doc.recompute()

            properties = {
                "length": length,
                "width": width,
                "height": height,
                "position": {"x": x, "y": y, "z": z},
                "volume": length * width * height,
            }

            logger.info(f"Boîte '{name}' créée avec succès: {properties}")

            return FreeCadObject(name=name, object_type="Box", properties=properties, success=True)

        except Exception as e:
            error_msg = f"Erreur lors de la création de la boîte: {e}"
            logger.error(error_msg)
            return FreeCadObject(
                name=name, object_type="Box", properties={}, success=False, error_message=error_msg
            )

    def list_objects(self) -> List[str]:
        """
        Liste tous les objets dans le document actuel.

        Returns:
            Liste des noms d'objets
        """
        if not self.is_connected or not self.doc:
            return []

        try:
            return [obj.Name for obj in self.doc.Objects]
        except Exception as e:
            logger.error(f"Erreur lors du listage des objets: {e}")
            return []

    def export_step(self, filepath: str, object_names: Optional[List[str]] = None) -> bool:
        """
        Exporte les objets au format STEP.

        Args:
            filepath: Chemin du fichier de sortie
            object_names: Liste des objets à exporter (tous si None)

        Returns:
            True si l'export réussit
        """
        if not self.is_connected or not self.doc:
            logger.error("Non connecté à FreeCAD")
            return False

        try:
            # Sélection des objets à exporter
            if object_names is None:
                objects_to_export = self.doc.Objects
            else:
                objects_to_export = [
                    self.doc.getObject(name)
                    for name in object_names
                    if self.doc.getObject(name) is not None
                ]

            if not objects_to_export:
                logger.warning("Aucun objet à exporter")
                return False

            # Export STEP
            import Part

            Part.export(objects_to_export, filepath)

            logger.info(f"Export STEP réussi: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'export STEP: {e}")
            return False


def main():
    """Fonction de test principale."""
    print("=== Test FreeCAD Bridge Minimal ===")

    # Création du bridge
    bridge = FreeCadBridge()

    # Connexion
    if not bridge.connect():
        print("❌ Échec de connexion à FreeCAD")
        return

    print("✅ Connexion FreeCAD réussie")

    try:
        # Création d'une boîte
        result = bridge.create_box(
            name="TestBox", length=20.0, width=15.0, height=10.0, x=5.0, y=5.0, z=0.0
        )

        if result.success:
            print(f"✅ Boîte créée: {result.name}")
            print(f"   Propriétés: {result.properties}")
        else:
            print(f"❌ Échec création boîte: {result.error_message}")

        # Liste des objets
        objects = bridge.list_objects()
        print(f"📦 Objets dans le document: {objects}")

        # Export STEP (optionnel)
        if objects:
            temp_file = tempfile.mktemp(suffix=".step")
            if bridge.export_step(temp_file):
                print(f"💾 Export STEP réussi: {temp_file}")
                # Nettoyage
                Path(temp_file).unlink(missing_ok=True)

    finally:
        # Déconnexion
        bridge.disconnect()
        print("🔌 Déconnexion FreeCAD")


if __name__ == "__main__":
    main()
