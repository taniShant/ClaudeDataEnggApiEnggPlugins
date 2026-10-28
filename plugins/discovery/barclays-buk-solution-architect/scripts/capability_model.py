#!/usr/bin/env python3
"""
Capability model loading, validation and canonicalisation.

Responsibilities:
- Load capability model YAML files from knowledge/domains/*.yml
- Validate structure against schema
- Check identifier uniqueness and hierarchy integrity
- Compute deterministic SHA-256 fingerprint of the complete model
- Extract authoritative capability catalogue (id → {name, hierarchy, description})
"""

import sys
import os
import json
import hashlib
import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone

try:
    import jsonschema
except ImportError:
    jsonschema = None


def _load_schema(schema_name: str) -> Dict[str, Any]:
    """Load a JSON schema file."""
    schema_path = Path(__file__).parent / "schemas" / schema_name
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class CapabilityModelError(Exception):
    """Raised when capability model validation fails."""
    pass


class CapabilityModel:
    """
    Represents a loaded and validated BUK capability model.

    The model consists of one or more domain files loaded from knowledge/domains/*.yml.
    Each file contains one top-level domain with sub-domains and capabilities.
    """

    def __init__(self):
        self.domains: Dict[str, Dict[str, Any]] = {}  # domain_id -> domain_data
        self.schema = _load_schema("capability_model.schema.json")
        self.fingerprint: str = ""
        self.loaded_files: List[str] = []

    def load_from_directory(self, directory: Path) -> None:
        """
        Load all capability model YAML files from a directory.

        Files must be named *.yml or *.yaml and located directly in the directory.
        """
        if not directory.is_dir():
            raise CapabilityModelError(f"Directory not found: {directory}")

        yaml_files = list(directory.glob("*.yml")) + list(directory.glob("*.yaml"))
        if not yaml_files:
            raise CapabilityModelError(f"No YAML capability model files found in {directory}")

        for yaml_file in sorted(yaml_files):
            self.load_from_file(yaml_file)

        self._validate_cross_domain_integrity()
        self._compute_fingerprint()

    def load_from_file(self, file_path: Path) -> None:
        """Load and validate a single capability model file."""
        if not file_path.exists():
            raise CapabilityModelError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise CapabilityModelError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise CapabilityModelError(f"Failed to load {file_path}: {e}")

        if not isinstance(data, dict):
            raise CapabilityModelError(f"YAML in {file_path} must be a dictionary")

        # Validate against schema
        if jsonschema:
            try:
                jsonschema.validate(instance=data, schema=self.schema)
            except jsonschema.ValidationError as e:
                raise CapabilityModelError(
                    f"Schema validation failed in {file_path}:\n{e.message}"
                )

        domain = data.get("domain", {})
        domain_id = domain.get("id", "")

        if not domain_id:
            raise CapabilityModelError(f"Domain missing 'id' in {file_path}")

        if domain_id in self.domains:
            raise CapabilityModelError(
                f"Duplicate domain ID '{domain_id}' (seen in {file_path} and previously loaded file)"
            )

        self.domains[domain_id] = domain
        self.loaded_files.append(str(file_path))

    def _validate_cross_domain_integrity(self) -> None:
        """
        Validate model integrity across all loaded domains.

        Checks:
        - All capability IDs are unique across all domains
        - All sub-domain IDs are unique across all domains
        - Hierarchy is internally consistent (capability in correct sub-domain)
        """
        capability_ids: Dict[str, str] = {}  # capability_id -> domain_id
        subdomain_ids: Dict[str, str] = {}   # subdomain_id -> domain_id

        for domain_id, domain in self.domains.items():
            sub_domains = domain.get("sub_domains", [])

            for sub_domain in sub_domains:
                sub_id = sub_domain.get("id", "")

                if not sub_id:
                    raise CapabilityModelError(
                        f"Sub-domain missing 'id' in domain {domain_id}"
                    )

                if sub_id in subdomain_ids:
                    raise CapabilityModelError(
                        f"Duplicate sub-domain ID '{sub_id}' in domains {domain_id} and {subdomain_ids[sub_id]}"
                    )

                subdomain_ids[sub_id] = domain_id

                capabilities = sub_domain.get("capabilities", [])
                for capability in capabilities:
                    cap_id = capability.get("id", "")

                    if not cap_id:
                        raise CapabilityModelError(
                            f"Capability missing 'id' in sub-domain {sub_id}"
                        )

                    if cap_id in capability_ids:
                        raise CapabilityModelError(
                            f"Duplicate capability ID '{cap_id}' in domains {domain_id} and {capability_ids[cap_id]}"
                        )

                    capability_ids[cap_id] = domain_id

    def _compute_fingerprint(self) -> None:
        """
        Compute a deterministic SHA-256 fingerprint of the model.

        Fingerprint is stable for the same model content across multiple loads.
        """
        # Canonicalize the domains into a deterministic JSON representation
        canonical_data = json.dumps(
            self.domains,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=True
        )

        self.fingerprint = hashlib.sha256(canonical_data.encode('utf-8')).hexdigest()

    def get_fingerprint(self) -> str:
        """Return the model fingerprint with 'sha256:' prefix."""
        if not self.fingerprint:
            self._compute_fingerprint()
        return f"sha256:{self.fingerprint}"

    def get_capability_catalogue(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract authoritative capability catalogue.

        Returns a dict mapping capability_id -> {name, domain_id, subdomain_id, description, hierarchy}
        """
        catalogue: Dict[str, Dict[str, Any]] = {}

        for domain_id, domain in self.domains.items():
            domain_name = domain.get("name", "")

            for sub_domain in domain.get("sub_domains", []):
                sub_id = sub_domain.get("id", "")
                sub_name = sub_domain.get("name", "")

                for capability in sub_domain.get("capabilities", []):
                    cap_id = capability.get("id", "")
                    cap_name = capability.get("name", "")
                    cap_desc = capability.get("description", "")

                    catalogue[cap_id] = {
                        "id": cap_id,
                        "name": cap_name,
                        "description": cap_desc,
                        "domain_id": domain_id,
                        "domain_name": domain_name,
                        "subdomain_id": sub_id,
                        "subdomain_name": sub_name,
                        "hierarchy": f"{domain_name} > {sub_name} > {cap_name}"
                    }

        return catalogue

    def validate_capability_reference(self, capability_id: str) -> Tuple[bool, str]:
        """
        Validate that a capability ID exists in the model.

        Returns (is_valid, error_message).
        """
        catalogue = self.get_capability_catalogue()
        if capability_id not in catalogue:
            available = sorted(catalogue.keys())
            return False, f"Unknown capability ID '{capability_id}'. Valid IDs: {available}"
        return True, ""

    def get_capability_info(self, capability_id: str) -> Dict[str, Any]:
        """Get full info for a capability ID (must be pre-validated)."""
        catalogue = self.get_capability_catalogue()
        return catalogue.get(capability_id, {})
