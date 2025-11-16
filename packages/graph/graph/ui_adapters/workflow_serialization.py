"""
Workflow serialization utilities for GraphRAG Ontology Application.

This module provides common serialization utilities for workflows across
different UI frameworks, enabling export and versioning capabilities.
"""

import logging
import json
import yaml
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib
import subprocess

# Configure logging
logger = logging.getLogger(__name__)


class WorkflowSerializer:
    """Workflow serialization utilities.

    This class provides common serialization utilities for workflows,
    enabling export to different formats and version control integration.
    """

    @staticmethod
    def to_yaml(workflow_data: Dict[str, Any], framework: str) -> str:
        """Convert workflow data to YAML format.

        Args:
            workflow_data: Workflow configuration data
            framework: Framework identifier (e.g., "flowise", "langflow")

        Returns:
            YAML representation of the workflow
        """
        try:
            # Create YAML-friendly structure
            yaml_dict = {
                "id": workflow_data.get("id", "unnamed"),
                "framework": framework,
                "version": workflow_data.get("metadata", {}).get("version_id", "unknown"),
                "generated_at": datetime.now().isoformat(),
                "steps": workflow_data.get("steps", []),
                "metadata": workflow_data.get("metadata", {})
            }

            return yaml.dump(yaml_dict, sort_keys=False, default_flow_style=False)

        except Exception as e:
            logger.error(f"Failed to convert workflow to YAML: {str(e)}", exc_info=True)

            # Fallback to manual YAML generation
            yaml_lines = [
                f"# {framework.capitalize()} workflow export",
                f"# Generated: {datetime.now().isoformat()}",
                "",
                f"id: {workflow_data.get('id', 'unnamed')}",
                f"framework: {framework}",
                f"version: {workflow_data.get('metadata', {}).get('version_id', 'unknown')}",
                f"generated_at: {datetime.now().isoformat()}",
                "steps:"
            ]

            # Add steps
            for step in workflow_data.get("steps", []):
                yaml_lines.append("  - type: " + step.get("type", "unknown"))

                for key, value in step.items():
                    if key != "type":
                        if isinstance(value, str):
                            yaml_lines.append(f"    {key}: {value}")
                        else:
                            yaml_lines.append(f"    {key}: {json.dumps(value)}")

            # Add metadata
            yaml_lines.append("metadata:")
            for key, value in workflow_data.get("metadata", {}).items():
                if isinstance(value, str):
                    yaml_lines.append(f"  {key}: {value}")
                else:
                    yaml_lines.append(f"  {key}: {json.dumps(value)}")

            return "\n".join(yaml_lines)

    @staticmethod
    def from_yaml(yaml_content: str) -> Dict[str, Any]:
        """Convert YAML to workflow data.

        Args:
            yaml_content: YAML representation of the workflow

        Returns:
            Workflow configuration data

        Raises:
            ValueError: When YAML parsing fails
        """
        try:
            # Parse YAML content
            workflow_data = yaml.safe_load(yaml_content)

            # Validate required fields
            if not isinstance(workflow_data, dict):
                raise ValueError("Invalid YAML format: root must be a dictionary")

            if "steps" not in workflow_data:
                raise ValueError("Invalid workflow format: 'steps' field is required")

            # Extract framework-specific fields
            framework = workflow_data.pop("framework", "unknown")
            version = workflow_data.pop("version", "unknown")
            generated_at = workflow_data.pop("generated_at", datetime.now().isoformat())

            # Ensure metadata exists
            if "metadata" not in workflow_data:
                workflow_data["metadata"] = {}

            # Add framework and version information to metadata
            workflow_data["metadata"]["framework"] = framework
            workflow_data["metadata"]["version_id"] = version
            workflow_data["metadata"]["imported_at"] = datetime.now().isoformat()
            workflow_data["metadata"]["exported_at"] = generated_at

            return workflow_data

        except Exception as e:
            logger.error(f"Failed to parse workflow YAML: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to parse workflow YAML: {str(e)}")

    @staticmethod
    def generate_version_id(workflow_data: Dict[str, Any]) -> str:
        """Generate version identifier for workflow.

        Creates a deterministic version ID based on workflow content,
        enabling identification of identical workflow versions.

        Args:
            workflow_data: Workflow configuration data

        Returns:
            Version identifier string
        """
        # Create a copy without metadata for consistent hashing
        workflow_copy = workflow_data.copy()
        workflow_copy.pop("metadata", None)

        # Generate hash from workflow content
        content_str = json.dumps(workflow_copy, sort_keys=True)
        hash_obj = hashlib.sha256(content_str.encode())
        version_hash = hash_obj.hexdigest()[:8]

        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        return f"{timestamp}-{version_hash}"

    @staticmethod
    def create_git_tag(
        *,
        repo_path: str,
        tag_name: str,
        message: str,
        annotated: bool = True
    ) -> bool:
        """Create Git tag for workflow version.

        Args:
            repo_path: Path to Git repository
            tag_name: Tag name (typically version ID)
            message: Tag message
            annotated: Whether to create an annotated tag

        Returns:
            True if tag creation was successful, False otherwise
        """
        try:
            # Check if Git is available
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.warning("Git not available. Version tagging skipped.")
                return False

            # Create tag command
            if annotated:
                cmd = ["git", "tag", "-a", tag_name, "-m", message]
            else:
                cmd = ["git", "tag", tag_name]

            # Execute tag command
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.warning(f"Failed to create Git tag: {result.stderr}")
                return False

            logger.info(f"Created Git tag: {tag_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create Git tag: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def rollback_to_tag(
        *,
        repo_path: str,
        tag_name: str,
        workflow_path: str
    ) -> bool:
        """Roll back workflow to a specific tagged version.

        Args:
            repo_path: Path to Git repository
            tag_name: Tag name to roll back to
            workflow_path: Path to workflow file or directory

        Returns:
            True if rollback was successful, False otherwise
        """
        try:
            # Check if Git is available
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.warning("Git not available. Rollback skipped.")
                return False

            # Check if tag exists
            result = subprocess.run(
                ["git", "tag", "-l", tag_name],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0 or not result.stdout.strip():
                logger.warning(f"Tag not found: {tag_name}")
                return False

            # Checkout file from tag
            result = subprocess.run(
                ["git", "checkout", tag_name, "--", workflow_path],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.warning(f"Failed to roll back to tag: {result.stderr}")
                return False

            logger.info(f"Rolled back {workflow_path} to tag: {tag_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to roll back to tag: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def list_tags(
        *,
        repo_path: str,
        pattern: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """List Git tags for workflow versions.

        Args:
            repo_path: Path to Git repository
            pattern: Optional pattern to filter tags

        Returns:
            List of dictionaries with tag information
        """
        try:
            # Check if Git is available
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.warning("Git not available. Tag listing skipped.")
                return []

            # Build command
            cmd = ["git", "tag", "-l"]
            if pattern:
                cmd.append(pattern)

            # Execute command
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.warning(f"Failed to list Git tags: {result.stderr}")
                return []

            # Parse tags
            tags = []
            for tag in result.stdout.strip().split("\n"):
                if tag:
                    # Get tag details
                    tag_info = subprocess.run(
                        ["git", "show", tag, "--format=%ai %s", "-s"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=False
                    )

                    if tag_info.returncode == 0 and tag_info.stdout.strip():
                        parts = tag_info.stdout.strip().split(" ", 3)
                        if len(parts) >= 4:
                            date, time, tz, message = parts
                            tags.append({
                                "name": tag,
                                "date": f"{date} {time} {tz}",
                                "message": message
                            })
                        else:
                            tags.append({
                                "name": tag,
                                "date": "",
                                "message": tag_info.stdout.strip()
                            })
                    else:
                        tags.append({
                            "name": tag,
                            "date": "",
                            "message": ""
                        })

            return tags

        except Exception as e:
            logger.error(f"Failed to list Git tags: {str(e)}", exc_info=True)
            return []
