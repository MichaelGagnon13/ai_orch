#!/usr/bin/env python3
"""
SystemIntegrator - Agent d'intégration système
"""

import json
import logging
import os
import subprocess
from typing import Any, Dict

import psutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemIntegrator:
    """Agent d'intégration et monitoring système"""

    SAFE_COMMANDS = ["ls", "pwd", "whoami", "date", "uname", "df", "free"]

    def read_file(self, path: str) -> Dict[str, Any]:
        """Lit un fichier"""
        try:
            with open(path, "r") as f:
                content = f.read()
            logger.info(f"✅ Fichier lu: {path}")
            return {"success": True, "content": content, "path": path}
        except Exception as e:
            logger.error(f"❌ Erreur lecture {path}: {e}")
            return {"success": False, "error": str(e), "path": path}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Écrit dans un fichier"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            logger.info(f"✅ Fichier écrit: {path}")
            return {"success": True, "path": path, "bytes": len(content)}
        except Exception as e:
            logger.error(f"❌ Erreur écriture {path}: {e}")
            return {"success": False, "error": str(e), "path": path}

    def exec_command(self, cmd: str) -> Dict[str, Any]:
        """Exécute une commande sécurisée"""
        cmd_base = cmd.split()[0] if cmd else ""

        if cmd_base not in self.SAFE_COMMANDS:
            return {
                "success": False,
                "error": f"Commande non autorisée: {cmd_base}",
                "allowed": self.SAFE_COMMANDS,
            }

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            logger.info(f"✅ Commande exécutée: {cmd}")
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout 10s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_system_info(self) -> Dict[str, Any]:
        """Récupère infos système"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "success": True,
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": disk.percent,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_processes(self, limit: int = 10) -> Dict[str, Any]:
        """Liste les processus"""
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Tri par CPU
            processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
            return {"success": True, "processes": processes[:limit]}
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Test
    integrator = SystemIntegrator()
    print(json.dumps(integrator.get_system_info(), indent=2))
