"""
Workflow versioning for Langflow integration.

This module provides workflow export and version control integration
for Langflow workflows, enabling workflow management and versioning.

Requirements:
- 3.2: Add version control integration for workflow management
- 3.4: Serialize to YAML compatible with both frameworks
- 4.4: Enable workflow export as code functionality
- 4.4: Integrate version in Git tags and activate rollback
"""

import hashlib
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import uuid

# Configure logging
logger = logging.getLogger(__name__)


class WorkflowVersionManager:
    """Workflow version manager for Langflow integration.

    This class provides workflow versioning capabilities for Langflow,
    including export as code, version control integration, and workflow
    history tracking.

    Requirements addressed:
    - 3.2: Add version control integration for workflow management
    - 4.4: Enable workflow export as code functionality
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        git_enabled: bool = True,
        max_versions: int = 10,
    ):
        """Initialize workflow version manager.

        Args:
            storage_dir: Directory for workflow storage
            git_enabled: Whether to use Git for version control
            max_versions: Maximum number of versions to keep per workflow
        """
        self.storage_dir = storage_dir or os.path.expanduser("~/.langflow/workflows")
        self.git_enabled = git_enabled
        self.max_versions = max_versions

        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)

        # Initialize Git repository if enabled
        if self.git_enabled:
            self._initialize_git_repository()

    def _initialize_git_repository(self) -> None:
        """Initialize Git repository for workflow versioning.

        Creates a Git repository in the storage directory if it doesn't
        already exist, enabling version control for workflows.
        """
        try:
            # Check if Git is available
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True, check=False
            )

            if result.returncode != 0:
                logger.warning("Git not available. Version control disabled.")
                self.git_enabled = False
                return

            # Check if repository already exists
            git_dir = os.path.join(self.storage_dir, ".git")
            if os.path.exists(git_dir):
                logger.info(f"Git repository already exists at {self.storage_dir}")
                return

            # Initialize repository
            result = subprocess.run(
                ["git", "init"],
                cwd=self.storage_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"Initialized Git repository at {self.storage_dir}")

                # Configure Git user if not already configured
                self._configure_git_user()

                # Create initial commit
                with open(os.path.join(self.storage_dir, "README.md"), "w") as f:
                    f.write(
                        "# Langflow Workflows\n\nThis repository contains versioned Langflow workflows.\n"
                    )

                subprocess.run(
                    ["git", "add", "README.md"],
                    cwd=self.storage_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"],
                    cwd=self.storage_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

            else:
                logger.warning(f"Failed to initialize Git repository: {result.stderr}")
                self.git_enabled = False

        except Exception as e:
            logger.error(
                f"Failed to initialize Git repository: {str(e)}", exc_info=True
            )
            self.git_enabled = False

    def _configure_git_user(self) -> None:
        """Configure Git user for commits.

        Sets up a default Git user configuration if none exists,
        enabling commits without user interaction.
        """
        try:
            # Check if user is configured
            result = subprocess.run(
                ["git", "config", "user.name"],
                cwd=self.storage_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0 or not result.stdout.strip():
                # Configure default user
                subprocess.run(
                    ["git", "config", "user.name", "Langflow Workflow Manager"],
                    cwd=self.storage_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                subprocess.run(
                    ["git", "config", "user.email", "langflow@example.com"],
                    cwd=self.storage_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                logger.info("Configured default Git user for workflow versioning")

        except Exception as e:
            logger.error(f"Failed to configure Git user: {str(e)}", exc_info=True)

    def save_workflow(
        self,
        *,
        workflow_id: str,
        workflow_data: Dict[str, Any],
        commit_message: Optional[str] = None,
        author: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save workflow with version control.

        Args:
            workflow_id: Unique identifier for the workflow
            workflow_data: Workflow configuration data
            commit_message: Optional commit message for version control
            author: Optional author name for commit

        Returns:
            Dictionary containing save result with version information

        Raises:
            ValueError: When workflow saving fails
        """
        try:
            # Create workflow directory if it doesn't exist
            workflow_dir = os.path.join(self.storage_dir, workflow_id)
            os.makedirs(workflow_dir, exist_ok=True)

            # Generate version identifier
            version_id = self._generate_version_id(workflow_data)
            timestamp = datetime.now().isoformat()

            # Add version metadata
            workflow_data["metadata"] = workflow_data.get("metadata", {})
            workflow_data["metadata"]["version_id"] = version_id
            workflow_data["metadata"]["saved_at"] = timestamp

            if author:
                workflow_data["metadata"]["author"] = author

            # Save workflow JSON
            json_path = os.path.join(workflow_dir, "workflow.json")
            with open(json_path, "w") as f:
                json.dump(workflow_data, f, indent=2)

            # Save workflow code exports
            self._export_workflow_code(workflow_dir, workflow_data)

            # Commit changes if Git is enabled
            if self.git_enabled:
                self._commit_workflow_changes(
                    workflow_id=workflow_id,
                    version_id=version_id,
                    commit_message=commit_message or f"Update workflow {workflow_id}",
                )

            # Update version history
            history = self._update_version_history(
                workflow_id, version_id, workflow_data
            )

            logger.info(f"Saved workflow {workflow_id} with version {version_id}")

            return {
                "workflow_id": workflow_id,
                "version_id": version_id,
                "saved_at": timestamp,
                "history": history,
            }

        except Exception as e:
            logger.error(f"Failed to save workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Workflow saving failed: {str(e)}")

    def _generate_version_id(self, workflow_data: Dict[str, Any]) -> str:
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

    def _export_workflow_code(
        self, workflow_dir: str, workflow_data: Dict[str, Any]
    ) -> None:
        """Export workflow as code in multiple formats.

        Args:
            workflow_dir: Directory to save exports
            workflow_data: Workflow configuration data
        """
        try:
            # Create exports directory
            exports_dir = os.path.join(workflow_dir, "exports")
            os.makedirs(exports_dir, exist_ok=True)

            # Export as Python
            python_code = self._generate_python_code(workflow_data)
            with open(os.path.join(exports_dir, "workflow.py"), "w") as f:
                f.write(python_code)

            # Export as Jupyter notebook
            notebook_code = self._generate_notebook_code(workflow_data)
            with open(os.path.join(exports_dir, "workflow.ipynb"), "w") as f:
                f.write(notebook_code)

            # Export as YAML
            yaml_code = self._generate_yaml_code(workflow_data)
            with open(os.path.join(exports_dir, "workflow.yaml"), "w") as f:
                f.write(yaml_code)

        except Exception as e:
            logger.error(f"Failed to export workflow code: {str(e)}", exc_info=True)

    def _generate_python_code(self, workflow_data: Dict[str, Any]) -> str:
        """Generate Python code from workflow configuration.

        Args:
            workflow_data: Workflow configuration data

        Returns:
            Generated Python code as string
        """
        workflow_id = workflow_data.get("id", "unnamed")
        steps = workflow_data.get("steps", [])

        code_lines = [
            "# Generated by GraphRAG Ontology Application",
            "# Langflow workflow export",
            f"# Workflow ID: {workflow_id}",
            f"# Version: {workflow_data.get('metadata', {}).get('version_id', 'unknown')}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            "from langflow import load_flow_from_json",
            "from langflow.graph import Graph",
            "import json",
            "",
            "# Workflow definition",
            "workflow_definition = {",
            f'    "id": "{workflow_id}",',
            '    "steps": [',
        ]

        # Add steps
        for i, step in enumerate(steps):
            step_json = json.dumps(step, indent=4).replace("\n", "\n        ")
            code_lines.append(
                f"        {step_json}{'' if i == len(steps) - 1 else ','}"
            )

        code_lines.extend(
            [
                "    ]",
                "}",
                "",
                "# Load and execute workflow",
                "def execute_workflow(input_data):",
                "    # Convert workflow definition to Langflow format",
                "    langflow_json = {",
                '        "nodes": [],',
                '        "edges": []',
                "    }",
                "    ",
                "    # Convert workflow steps to Langflow nodes and edges",
                '    for i, step in enumerate(workflow_definition["steps"]):',
                "        # Create node for step",
                '        node_id = f"node_{i}"',
                '        node_type = step.get("type", "unknown")',
                "        ",
                "        # Add node to graph",
                '        langflow_json["nodes"].append({',
                '            "id": node_id,',
                '            "type": node_type,',
                '            "data": step',
                "        })",
                "        ",
                "        # Connect nodes with edges",
                "        if i > 0:",
                '            langflow_json["edges"].append({',
                '                "source": f"node_{i-1}",',
                '                "target": node_id',
                "            })",
                "    ",
                "    # Load and execute flow",
                "    graph = Graph.from_payload(langflow_json)",
                "    result = graph.build(input_data)",
                "    return result",
                "",
                "# Example usage",
                'if __name__ == "__main__":',
                '    input_data = {"query": "What is GraphRAG?"}',
                "    result = execute_workflow(input_data)",
                "    import logging",
                "    logging.getLogger(__name__).info(result)",
            ]
        )

        return "\n".join(code_lines)

    def _generate_notebook_code(self, workflow_data: Dict[str, Any]) -> str:
        """Generate Jupyter notebook from workflow configuration.

        Args:
            workflow_data: Workflow configuration data

        Returns:
            Generated notebook JSON as string
        """
        workflow_id = workflow_data.get("id", "unnamed")
        steps = workflow_data.get("steps", [])

        cells = []

        # Add header cell
        cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"# Langflow Workflow: {workflow_id}\n",
                    "\n",
                    f"Version: {workflow_data.get('metadata', {}).get('version_id', 'unknown')}\n",
                    "\n",
                    f"Generated: {datetime.now().isoformat()}\n",
                ],
            }
        )

        # Add imports cell
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Import required libraries\n",
                    "from langflow import load_flow_from_json\n",
                    "from langflow.graph import Graph\n",
                    "import json\n",
                ],
                "outputs": [],
            }
        )

        # Add workflow definition cell
        workflow_cell_source = [
            "# Workflow definition\n",
            "workflow_definition = {\n",
            f'    "id": "{workflow_id}",\n',
            '    "steps": [\n',
        ]

        # Add steps
        for i, step in enumerate(steps):
            step_json = json.dumps(step, indent=4).replace("\n", "\n        ")
            workflow_cell_source.append(
                f"        {step_json}{'' if i == len(steps) - 1 else ','}\n"
            )

        workflow_cell_source.extend(["    ]\n", "}\n"])

        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": workflow_cell_source,
                "outputs": [],
            }
        )

        # Add conversion cell
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Convert workflow definition to Langflow format\n",
                    "langflow_json = {\n",
                    '    "nodes": [],\n',
                    '    "edges": []\n',
                    "}\n",
                    "\n",
                    "# Convert workflow steps to Langflow nodes and edges\n",
                    'for i, step in enumerate(workflow_definition["steps"]):\n',
                    "    # Create node for step\n",
                    '    node_id = f"node_{i}"\n',
                    '    node_type = step.get("type", "unknown")\n',
                    "    \n",
                    "    # Add node to graph\n",
                    '    langflow_json["nodes"].append({\n',
                    '        "id": node_id,\n',
                    '        "type": node_type,\n',
                    '        "data": step\n',
                    "    })\n",
                    "    \n",
                    "    # Connect nodes with edges\n",
                    "    if i > 0:\n",
                    '        langflow_json["edges"].append({\n',
                    '            "source": f"node_{i-1}",\n',
                    '            "target": node_id\n',
                    "        })\n",
                ],
                "outputs": [],
            }
        )

        # Add execution cell
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": [
                    "# Load and execute flow\n",
                    "graph = Graph.from_payload(langflow_json)\n",
                    "\n",
                    "# Define input data\n",
                    'input_data = {"query": "What is GraphRAG?"}\n',
                    "\n",
                    "# Execute workflow\n",
                    "result = graph.build(input_data)\n",
                    "import logging\n                logging.getLogger(__name__).info(result)\n",
                ],
                "outputs": [],
            }
        )

        # Create notebook JSON
        notebook = {
            "cells": cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.8.0",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        return json.dumps(notebook, indent=2)

    def _generate_yaml_code(self, workflow_data: Dict[str, Any]) -> str:
        """Generate YAML from workflow configuration.

        Args:
            workflow_data: Workflow configuration data

        Returns:
            Generated YAML as string
        """
        try:
            import yaml

            # Create YAML-friendly structure
            yaml_dict = {
                "id": workflow_data.get("id", "unnamed"),
                "version": workflow_data.get("metadata", {}).get(
                    "version_id", "unknown"
                ),
                "generated_at": datetime.now().isoformat(),
                "steps": workflow_data.get("steps", []),
            }

            return yaml.dump(yaml_dict, sort_keys=False, default_flow_style=False)

        except ImportError:
            # Fallback if PyYAML is not available
            yaml_lines = [
                "# Generated by GraphRAG Ontology Application",
                "# Langflow workflow export",
                "",
                f"id: {workflow_data.get('id', 'unnamed')}",
                f"version: {workflow_data.get('metadata', {}).get('version_id', 'unknown')}",
                f"generated_at: {datetime.now().isoformat()}",
                "steps:",
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

            return "\n".join(yaml_lines)

    def _commit_workflow_changes(
        self, *, workflow_id: str, version_id: str, commit_message: str
    ) -> bool:
        """Commit workflow changes to Git repository.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier
            commit_message: Commit message

        Returns:
            True if commit was successful, False otherwise
        """
        try:
            # Add workflow files to Git
            workflow_path = os.path.join(workflow_id)

            result = subprocess.run(
                ["git", "add", workflow_path],
                cwd=self.storage_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(f"Failed to add workflow files: {result.stderr}")
                return False

            # Create commit
            result = subprocess.run(
                ["git", "commit", "-m", f"{commit_message} [version: {version_id}]"],
                cwd=self.storage_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                # Check if there were no changes
                if (
                    "nothing to commit" in result.stdout
                    or "nothing to commit" in result.stderr
                ):
                    logger.info("No changes to commit")
                    return True

                logger.warning(f"Failed to commit workflow changes: {result.stderr}")
                return False

            logger.info(f"Committed workflow {workflow_id} version {version_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to commit workflow changes: {str(e)}", exc_info=True)
            return False

    def _update_version_history(
        self, workflow_id: str, version_id: str, workflow_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Update workflow version history.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier
            workflow_data: Workflow configuration data

        Returns:
            Updated version history list
        """
        try:
            # Load existing history
            history_path = os.path.join(self.storage_dir, workflow_id, "history.json")

            if os.path.exists(history_path):
                with open(history_path, "r") as f:
                    history = json.load(f)
            else:
                history = []

            # Add new version to history
            history.append(
                {
                    "version_id": version_id,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": workflow_data.get("metadata", {}),
                    "step_count": len(workflow_data.get("steps", [])),
                }
            )

            # Limit history size
            if len(history) > self.max_versions:
                history = history[-self.max_versions :]

            # Save updated history
            with open(history_path, "w") as f:
                json.dump(history, f, indent=2)

            return history

        except Exception as e:
            logger.error(f"Failed to update version history: {str(e)}", exc_info=True)
            return []

    def get_workflow_versions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get version history for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of version history entries

        Raises:
            ValueError: When workflow is not found
        """
        try:
            # Check if workflow exists
            workflow_dir = os.path.join(self.storage_dir, workflow_id)
            if not os.path.exists(workflow_dir):
                raise ValueError(f"Workflow not found: {workflow_id}")

            # Load history
            history_path = os.path.join(workflow_dir, "history.json")

            if os.path.exists(history_path):
                with open(history_path, "r") as f:
                    history = json.load(f)

                # Sort by timestamp (newest first)
                history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

                return history
            else:
                return []

        except Exception as e:
            logger.error(f"Failed to get workflow versions: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get workflow versions: {str(e)}")

    def get_workflow_version(self, workflow_id: str, version_id: str) -> Dict[str, Any]:
        """Get specific version of a workflow.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier

        Returns:
            Workflow configuration for the specified version

        Raises:
            ValueError: When workflow or version is not found
        """
        try:
            # Check if workflow exists
            workflow_dir = os.path.join(self.storage_dir, workflow_id)
            if not os.path.exists(workflow_dir):
                raise ValueError(f"Workflow not found: {workflow_id}")

            # If version is "latest", get the latest version
            if version_id == "latest":
                history = self.get_workflow_versions(workflow_id)
                if not history:
                    raise ValueError(f"No versions found for workflow: {workflow_id}")

                version_id = history[0]["version_id"]

            # Try to get version from Git if enabled
            if self.git_enabled:
                workflow_data = self._get_version_from_git(workflow_id, version_id)
                if workflow_data:
                    return workflow_data

            # Fall back to checking history
            history = self.get_workflow_versions(workflow_id)

            for entry in history:
                if entry["version_id"] == version_id:
                    # Load workflow JSON
                    json_path = os.path.join(workflow_dir, "workflow.json")

                    if os.path.exists(json_path):
                        with open(json_path, "r") as f:
                            workflow_data = json.load(f)

                        # Check if this is the requested version
                        if (
                            workflow_data.get("metadata", {}).get("version_id")
                            == version_id
                        ):
                            return workflow_data

            raise ValueError(f"Version not found: {version_id}")

        except Exception as e:
            logger.error(f"Failed to get workflow version: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to get workflow version: {str(e)}")

    def _get_version_from_git(
        self, workflow_id: str, version_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get workflow version from Git history.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier

        Returns:
            Workflow configuration for the specified version or None if not found
        """
        try:
            # Find commit with the specified version
            result = subprocess.run(
                ["git", "log", "--grep", f"\\[version: {version_id}\\]", "--format=%H"],
                cwd=self.storage_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return None

            commit_hash = result.stdout.strip().split("\n")[0]

            # Create temporary directory for checkout
            with tempfile.TemporaryDirectory():
                # Extract workflow file from commit
                workflow_path = os.path.join(workflow_id, "workflow.json")

                result = subprocess.run(
                    ["git", "show", f"{commit_hash}:{workflow_path}"],
                    cwd=self.storage_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode != 0:
                    return None

                # Parse workflow JSON
                try:
                    workflow_data = json.loads(result.stdout)
                    return workflow_data
                except json.JSONDecodeError:
                    return None

        except Exception as e:
            logger.error(f"Failed to get version from Git: {str(e)}", exc_info=True)
            return None

    def compare_workflow_versions(
        self, workflow_id: str, version_id1: str, version_id2: str
    ) -> Dict[str, Any]:
        """Compare two workflow versions.

        Args:
            workflow_id: Workflow identifier
            version_id1: First version identifier
            version_id2: Second version identifier

        Returns:
            Dictionary containing comparison results

        Raises:
            ValueError: When workflow or versions are not found
        """
        try:
            # Get workflow versions
            workflow1 = self.get_workflow_version(workflow_id, version_id1)
            workflow2 = self.get_workflow_version(workflow_id, version_id2)

            # Compare steps
            steps1 = workflow1.get("steps", [])
            steps2 = workflow2.get("steps", [])

            # Calculate differences
            added_steps = []
            removed_steps = []
            modified_steps = []

            # Create step maps for comparison
            step_map1 = {i: step for i, step in enumerate(steps1)}
            step_map2 = {i: step for i, step in enumerate(steps2)}

            # Find added and modified steps
            for i, step in step_map2.items():
                if i >= len(steps1):
                    added_steps.append({"index": i, "step": step})
                elif json.dumps(step, sort_keys=True) != json.dumps(
                    steps1[i], sort_keys=True
                ):
                    modified_steps.append(
                        {"index": i, "before": steps1[i], "after": step}
                    )

            # Find removed steps
            for i, step in step_map1.items():
                if i >= len(steps2):
                    removed_steps.append({"index": i, "step": step})

            # Create comparison result
            comparison = {
                "workflow_id": workflow_id,
                "version1": version_id1,
                "version2": version_id2,
                "step_count1": len(steps1),
                "step_count2": len(steps2),
                "added_steps": added_steps,
                "removed_steps": removed_steps,
                "modified_steps": modified_steps,
                "timestamp": datetime.now().isoformat(),
            }

            return comparison

        except Exception as e:
            logger.error(
                f"Failed to compare workflow versions: {str(e)}", exc_info=True
            )
            raise ValueError(f"Failed to compare workflow versions: {str(e)}")

    def revert_to_version(
        self, workflow_id: str, version_id: str, commit_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Revert workflow to a previous version.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier to revert to
            commit_message: Optional commit message

        Returns:
            Dictionary containing revert result

        Raises:
            ValueError: When workflow or version is not found
        """
        try:
            # Get workflow version
            workflow_data = self.get_workflow_version(workflow_id, version_id)

            # Save as new version
            result = self.save_workflow(
                workflow_id=workflow_id,
                workflow_data=workflow_data,
                commit_message=commit_message or f"Revert to version {version_id}",
                author="revert_operation",
            )

            logger.info(f"Reverted workflow {workflow_id} to version {version_id}")

            return {
                "workflow_id": workflow_id,
                "original_version": version_id,
                "new_version": result["version_id"],
                "timestamp": datetime.now().isoformat(),
                "status": "reverted",
            }

        except Exception as e:
            logger.error(f"Failed to revert workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to revert workflow: {str(e)}")

    def export_workflow(
        self,
        workflow_id: str,
        version_id: str = "latest",
        format: str = "python",
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export workflow as code.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier (default: "latest")
            format: Export format ("python", "notebook", or "yaml")
            output_dir: Optional output directory

        Returns:
            Dictionary containing export result

        Raises:
            ValueError: When workflow or version is not found
        """
        try:
            # Get workflow version
            workflow_data = self.get_workflow_version(workflow_id, version_id)

            # Determine output directory
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            else:
                output_dir = os.getcwd()

            # Generate code based on format
            if format == "python":
                code = self._generate_python_code(workflow_data)
                file_extension = "py"
            elif format == "notebook":
                code = self._generate_notebook_code(workflow_data)
                file_extension = "ipynb"
            elif format == "yaml":
                code = self._generate_yaml_code(workflow_data)
                file_extension = "yaml"
            else:
                raise ValueError(f"Unsupported export format: {format}")

            # Save to file
            output_path = os.path.join(output_dir, f"{workflow_id}.{file_extension}")
            with open(output_path, "w") as f:
                f.write(code)

            logger.info(f"Exported workflow {workflow_id} to {output_path}")

            return {
                "workflow_id": workflow_id,
                "version_id": version_id,
                "format": format,
                "output_path": output_path,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to export workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to export workflow: {str(e)}")

    def export_workflow_to_yaml(
        self,
        *,
        workflow_id: str,
        version_id: Optional[str] = None,
        include_history: bool = False,
    ) -> Dict[str, Any]:
        """Export workflow to YAML format compatible with both frameworks.

        Args:
            workflow_id: Workflow identifier
            version_id: Optional version identifier (latest if not provided)
            include_history: Whether to include version history

        Returns:
            Dictionary containing exported YAML content and metadata

        Raises:
            ValueError: When workflow export fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Get workflow data
            workflow_data = self.get_workflow_version(
                workflow_id=workflow_id, version_id=version_id or "latest"
            )

            if not workflow_data:
                raise ValueError(f"Workflow not found: {workflow_id}")

            # Add framework identifier
            workflow_data["metadata"] = workflow_data.get("metadata", {})
            workflow_data["metadata"]["framework"] = "langflow"

            # Add history if requested
            if include_history:
                history = self.get_workflow_versions(workflow_id)
                workflow_data["metadata"]["version_history"] = history

            # Convert to YAML
            yaml_content = WorkflowSerializer.to_yaml(workflow_data, "langflow")

            return {
                "workflow_id": workflow_id,
                "version_id": workflow_data.get("metadata", {}).get("version_id"),
                "content": yaml_content,
                "format": "yaml",
            }

        except Exception as e:
            logger.error(f"Failed to export workflow to YAML: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to export workflow to YAML: {str(e)}")

    def import_workflow_from_yaml(
        self,
        *,
        yaml_content: str,
        workflow_id: Optional[str] = None,
        override_existing: bool = False,
    ) -> Dict[str, Any]:
        """Import workflow from YAML format.

        Args:
            yaml_content: YAML content to import
            workflow_id: Optional workflow identifier (generated if not provided)
            override_existing: Whether to override existing workflow

        Returns:
            Dictionary containing import result

        Raises:
            ValueError: When workflow import fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Parse YAML content
            workflow_data = WorkflowSerializer.from_yaml(yaml_content)

            # Use provided workflow ID or extract from YAML
            imported_id = (
                workflow_id or workflow_data.get("id") or f"wf_{uuid.uuid4().hex[:8]}"
            )

            # Check if workflow exists
            workflow_dir = os.path.join(self.storage_dir, imported_id)
            if os.path.exists(workflow_dir) and not override_existing:
                raise ValueError(
                    f"Workflow already exists: {imported_id}. Use override_existing=True to replace it."
                )

            # Save workflow
            result = self.save_workflow(
                workflow_id=imported_id,
                workflow_data=workflow_data,
                commit_message=(
                    "Import workflow from YAML [version: "
                    f"{workflow_data.get('metadata', {}).get('version_id', 'unknown')}]"
                ),
            )

            return {
                "workflow_id": imported_id,
                "version_id": result["version_id"],
                "saved_at": result["saved_at"],
                "status": "imported",
            }

        except Exception as e:
            logger.error(
                f"Failed to import workflow from YAML: {str(e)}", exc_info=True
            )
            raise ValueError(f"Failed to import workflow from YAML: {str(e)}")

    def create_git_tag(
        self,
        *,
        workflow_id: str,
        version_id: Optional[str] = None,
        tag_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create Git tag for workflow version.

        Args:
            workflow_id: Workflow identifier
            version_id: Optional version identifier (latest if not provided)
            tag_message: Optional tag message

        Returns:
            Dictionary containing tag creation result

        Raises:
            ValueError: When tag creation fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Check if Git is enabled
            if not self.git_enabled:
                raise ValueError("Git is not enabled for this workflow manager")

            # Get workflow version
            workflow_data = self.get_workflow_version(
                workflow_id=workflow_id, version_id=version_id or "latest"
            )

            if not workflow_data:
                raise ValueError(f"Workflow not found: {workflow_id}")

            # Get version ID
            version_id = workflow_data.get("metadata", {}).get("version_id")
            if not version_id:
                raise ValueError("Workflow version does not have a version ID")

            # Create tag name
            tag_name = f"langflow-{workflow_id}-{version_id}"

            # Create tag message
            message = (
                tag_message or f"Langflow workflow {workflow_id} version {version_id}"
            )

            # Create tag
            tag_created = WorkflowSerializer.create_git_tag(
                repo_path=self.storage_dir,
                tag_name=tag_name,
                message=message,
                annotated=True,
            )

            if not tag_created:
                raise ValueError(f"Failed to create Git tag: {tag_name}")

            return {
                "workflow_id": workflow_id,
                "version_id": version_id,
                "tag_name": tag_name,
                "created_at": datetime.now().isoformat(),
                "message": message,
            }

        except Exception as e:
            logger.error(f"Failed to create Git tag: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to create Git tag: {str(e)}")

    def rollback_to_version(
        self, *, workflow_id: str, version_id: str
    ) -> Dict[str, Any]:
        """Roll back workflow to a specific version.

        Args:
            workflow_id: Workflow identifier
            version_id: Version identifier to roll back to

        Returns:
            Dictionary containing rollback result

        Raises:
            ValueError: When rollback fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Check if Git is enabled
            if not self.git_enabled:
                # Fall back to loading version from history
                workflow_data = self.get_workflow_version(
                    workflow_id=workflow_id, version_id=version_id
                )

                if not workflow_data:
                    raise ValueError(f"Version not found: {version_id}")

                # Save as current version
                result = self.save_workflow(
                    workflow_id=workflow_id,
                    workflow_data=workflow_data,
                    commit_message=f"Roll back to version {version_id}",
                )

                return {
                    "workflow_id": workflow_id,
                    "version_id": version_id,
                    "rollback_time": datetime.now().isoformat(),
                    "method": "history",
                    "status": "success",
                }

            # Try to roll back using Git tag
            tag_name = f"langflow-{workflow_id}-{version_id}"

            # Check if tag exists
            tags = WorkflowSerializer.list_tags(
                repo_path=self.storage_dir, pattern=tag_name
            )

            if not tags:
                # Try to find commit with version
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--grep",
                        f"\\[version: {version_id}\\]",
                        "--format=%H",
                    ],
                    cwd=self.storage_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode != 0 or not result.stdout.strip():
                    raise ValueError(f"Version not found in Git history: {version_id}")

                commit_hash = result.stdout.strip().split("\n")[0]

                # Roll back using commit hash
                workflow_path = os.path.join(workflow_id)

                result = subprocess.run(
                    ["git", "checkout", commit_hash, "--", workflow_path],
                    cwd=self.storage_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode != 0:
                    raise ValueError(f"Failed to roll back to commit: {result.stderr}")
            else:
                # Roll back using tag
                workflow_path = os.path.join(workflow_id)

                rollback_success = WorkflowSerializer.rollback_to_tag(
                    repo_path=self.storage_dir,
                    tag_name=tag_name,
                    workflow_path=workflow_path,
                )

                if not rollback_success:
                    raise ValueError(f"Failed to roll back to tag: {tag_name}")

            return {
                "workflow_id": workflow_id,
                "version_id": version_id,
                "rollback_time": datetime.now().isoformat(),
                "method": "git",
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Failed to roll back workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to roll back workflow: {str(e)}")

    def list_git_tags(
        self, *, workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List Git tags for workflow versions.

        Args:
            workflow_id: Optional workflow identifier to filter tags

        Returns:
            List of dictionaries with tag information

        Raises:
            ValueError: When listing tags fails
        """
        try:
            # Import serialization utilities
            from ui_adapters.workflow_serialization import WorkflowSerializer

            # Check if Git is enabled
            if not self.git_enabled:
                raise ValueError("Git is not enabled for this workflow manager")

            # Build pattern
            pattern = None
            if workflow_id:
                pattern = f"langflow-{workflow_id}-*"

            # List tags
            tags = WorkflowSerializer.list_tags(
                repo_path=self.storage_dir, pattern=pattern
            )

            # Parse workflow and version information from tag names
            for tag in tags:
                tag_name = tag["name"]
                if tag_name.startswith("langflow-"):
                    parts = tag_name.split("-", 2)
                    if len(parts) >= 3:
                        tag["workflow_id"] = parts[1]
                        tag["version_id"] = parts[2]

            return tags

        except Exception as e:
            logger.error(f"Failed to list Git tags: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to list Git tags: {str(e)}")
