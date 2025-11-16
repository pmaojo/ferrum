"""
AI-Powered Code Review Service

Provides intelligent code review capabilities using LLM analysis
combined with architectural pattern detection and best practices.
"""

import logging
import json
import ast
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from application.ports.base import LLMPort
from application.ports.knowledge_graph_port import KnowledgeGraphPort
from ..agents.advanced_ai_agent import CodeReviewSuggestion
from .architectural_pattern_service import ArchitecturalPatternService

logger = logging.getLogger(__name__)


@dataclass
class CodeFile:
    """Represents a code file for review"""
    file_path: str
    content: str
    language: str
    module_name: Optional[str] = None
    component_type: Optional[str] = None


@dataclass
class ReviewContext:
    """Context for code review"""
    project_type: str  # "kthulu", "general"
    architecture_style: str  # "hexagonal", "layered", "microservices"
    review_focus: List[str]  # ["architecture", "patterns", "quality", "security"]
    tenant_id: str = "default"


@dataclass
class CodeReviewReport:
    """Complete code review report"""
    file_path: str
    overall_score: float  # 0-100
    suggestions: List[CodeReviewSuggestion]
    architectural_issues: List[Dict[str, Any]]
    pattern_violations: List[Dict[str, Any]]
    quality_metrics: Dict[str, Any]
    summary: str
    recommendations: List[str]


class AICodeReviewService:
    """Service for AI-powered code review"""
    
    def __init__(
        self,
        llm: LLMPort,
        knowledge_graph: Optional[KnowledgeGraphPort] = None,
        tenant_id: str = "default"
    ):
        """Initialize the AI code review service"""
        self.llm = llm
        self.knowledge_graph = knowledge_graph
        self.tenant_id = tenant_id
        
        # Initialize pattern service if knowledge graph is available
        self.pattern_service = None
        if knowledge_graph:
            self.pattern_service = ArchitecturalPatternService(knowledge_graph, llm)
        
        logger.info(f"AICodeReviewService initialized for tenant {tenant_id}")
    
    def review_file(
        self,
        file_path: str,
        content: str,
        context: ReviewContext
    ) -> CodeReviewReport:
        """
        Review a single code file
        
        Args:
            file_path: Path to the file being reviewed
            content: File content
            context: Review context and preferences
            
        Returns:
            Complete code review report
        """
        try:
            # Create code file object
            code_file = CodeFile(
                file_path=file_path,
                content=content,
                language=self._detect_language(file_path),
                module_name=self._extract_module_name(file_path),
                component_type=self._detect_component_type(file_path, content)
            )
            
            # Perform different types of analysis
            suggestions = self._analyze_code_quality(code_file, context)
            architectural_issues = self._analyze_architecture(code_file, context)
            pattern_violations = self._analyze_patterns(code_file, context)
            quality_metrics = self._calculate_quality_metrics(code_file)
            
            # Generate overall score
            overall_score = self._calculate_overall_score(
                suggestions, architectural_issues, pattern_violations, quality_metrics
            )
            
            # Generate summary and recommendations
            summary = self._generate_summary(code_file, overall_score, suggestions)
            recommendations = self._generate_recommendations(
                suggestions, architectural_issues, pattern_violations
            )
            
            return CodeReviewReport(
                file_path=file_path,
                overall_score=overall_score,
                suggestions=suggestions,
                architectural_issues=architectural_issues,
                pattern_violations=pattern_violations,
                quality_metrics=quality_metrics,
                summary=summary,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.exception(f"Error reviewing file {file_path}: {str(e)}")
            return self._create_error_report(file_path, str(e))
    
    def review_multiple_files(
        self,
        files: List[Tuple[str, str]],  # (file_path, content) pairs
        context: ReviewContext
    ) -> List[CodeReviewReport]:
        """
        Review multiple files
        
        Args:
            files: List of (file_path, content) tuples
            context: Review context
            
        Returns:
            List of code review reports
        """
        reports = []
        
        for file_path, content in files:
            report = self.review_file(file_path, content, context)
            reports.append(report)
        
        return reports
    
    def get_review_summary(
        self,
        reports: List[CodeReviewReport]
    ) -> Dict[str, Any]:
        """
        Generate summary across multiple file reviews
        
        Args:
            reports: List of code review reports
            
        Returns:
            Overall review summary
        """
        if not reports:
            return {"error": "No reports provided"}
        
        # Calculate aggregate metrics
        total_files = len(reports)
        avg_score = sum(report.overall_score for report in reports) / total_files
        total_suggestions = sum(len(report.suggestions) for report in reports)
        
        # Categorize issues by severity
        high_priority_issues = []
        medium_priority_issues = []
        low_priority_issues = []
        
        for report in reports:
            for suggestion in report.suggestions:
                if suggestion.architectural_impact == "high":
                    high_priority_issues.append({
                        "file": report.file_path,
                        "title": suggestion.title,
                        "type": suggestion.suggestion_type
                    })
                elif suggestion.architectural_impact == "medium":
                    medium_priority_issues.append({
                        "file": report.file_path,
                        "title": suggestion.title,
                        "type": suggestion.suggestion_type
                    })
                else:
                    low_priority_issues.append({
                        "file": report.file_path,
                        "title": suggestion.title,
                        "type": suggestion.suggestion_type
                    })
        
        # Generate overall recommendations
        overall_recommendations = self._generate_overall_recommendations(reports)
        
        return {
            "summary": {
                "total_files": total_files,
                "average_score": round(avg_score, 1),
                "total_suggestions": total_suggestions,
                "high_priority_issues": len(high_priority_issues),
                "medium_priority_issues": len(medium_priority_issues),
                "low_priority_issues": len(low_priority_issues)
            },
            "priority_issues": {
                "high": high_priority_issues[:10],  # Top 10 high priority
                "medium": medium_priority_issues[:10],
                "low": low_priority_issues[:10]
            },
            "recommendations": overall_recommendations,
            "files_by_score": [
                {
                    "file": report.file_path,
                    "score": report.overall_score,
                    "suggestion_count": len(report.suggestions)
                }
                for report in sorted(reports, key=lambda r: r.overall_score)
            ]
        }
    
    def _analyze_code_quality(
        self,
        code_file: CodeFile,
        context: ReviewContext
    ) -> List[CodeReviewSuggestion]:
        """Analyze code quality using LLM"""
        
        # Create analysis prompt based on language and context
        if code_file.language == "go":
            prompt = self._create_go_analysis_prompt(code_file, context)
        elif code_file.language == "python":
            prompt = self._create_python_analysis_prompt(code_file, context)
        else:
            prompt = self._create_generic_analysis_prompt(code_file, context)
        
        try:
            llm_response = self.llm.generate(prompt, self.tenant_id)
            suggestions_data = json.loads(llm_response)
            
            suggestions = []
            for suggestion_data in suggestions_data:
                suggestion = CodeReviewSuggestion(
                    file_path=code_file.file_path,
                    line_number=suggestion_data.get("line_number"),
                    suggestion_type=suggestion_data.get("suggestion_type", "improvement"),
                    title=suggestion_data.get("title", ""),
                    description=suggestion_data.get("description", ""),
                    code_snippet=suggestion_data.get("code_snippet"),
                    suggested_fix=suggestion_data.get("suggested_fix"),
                    confidence=suggestion_data.get("confidence", 0.5),
                    architectural_impact=suggestion_data.get("architectural_impact", "medium")
                )
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error in LLM code analysis: {str(e)}")
            return [self._create_fallback_suggestion(code_file, str(e))]
    
    def _create_go_analysis_prompt(
        self,
        code_file: CodeFile,
        context: ReviewContext
    ) -> str:
        """Create analysis prompt for Go code"""
        
        focus_areas = ", ".join(context.review_focus)
        
        return f"""
        Review this Go code for quality, architecture, and best practices:
        
        File: {code_file.file_path}
        Module: {code_file.module_name or 'unknown'}
        Component Type: {code_file.component_type or 'unknown'}
        Architecture Style: {context.architecture_style}
        Review Focus: {focus_areas}
        
        Code:
        ```go
        {code_file.content}
        ```
        
        Analyze for:
        1. Hexagonal architecture compliance (if applicable)
        2. Dependency inversion principle
        3. SOLID principles
        4. Go best practices and idioms
        5. Error handling
        6. Interface design
        7. Testability
        8. Performance considerations
        
        Return JSON array of suggestions:
        [{{
            "line_number": 15,
            "suggestion_type": "architecture|pattern|quality|performance|security",
            "title": "Brief title",
            "description": "Detailed explanation",
            "code_snippet": "problematic code (if applicable)",
            "suggested_fix": "suggested improvement",
            "confidence": 0.0-1.0,
            "architectural_impact": "low|medium|high"
        }}]
        
        Focus on actionable, specific improvements. Limit to 10 most important suggestions.
        """
    
    def _create_python_analysis_prompt(
        self,
        code_file: CodeFile,
        context: ReviewContext
    ) -> str:
        """Create analysis prompt for Python code"""
        
        focus_areas = ", ".join(context.review_focus)
        
        return f"""
        Review this Python code for quality, architecture, and best practices:
        
        File: {code_file.file_path}
        Module: {code_file.module_name or 'unknown'}
        Architecture Style: {context.architecture_style}
        Review Focus: {focus_areas}
        
        Code:
        ```python
        {code_file.content}
        ```
        
        Analyze for:
        1. Clean architecture principles
        2. SOLID principles
        3. Python best practices (PEP 8, PEP 20)
        4. Type hints and documentation
        5. Error handling
        6. Security issues
        7. Performance considerations
        8. Testability
        
        Return JSON array of suggestions with same format as Go analysis.
        Limit to 10 most important suggestions.
        """
    
    def _create_generic_analysis_prompt(
        self,
        code_file: CodeFile,
        context: ReviewContext
    ) -> str:
        """Create generic analysis prompt for other languages"""
        
        return f"""
        Review this {code_file.language} code for quality and best practices:
        
        File: {code_file.file_path}
        
        Code:
        ```{code_file.language}
        {code_file.content}
        ```
        
        Focus on:
        1. Code quality and readability
        2. Best practices for {code_file.language}
        3. Potential bugs or issues
        4. Performance considerations
        5. Security concerns
        
        Return JSON array of suggestions with same format.
        Limit to 10 most important suggestions.
        """
    
    def _analyze_architecture(
        self,
        code_file: CodeFile,
        context: ReviewContext
    ) -> List[Dict[str, Any]]:
        """Analyze architectural compliance"""
        
        issues = []
        
        # Check for common architectural violations
        if context.architecture_style == "hexagonal":
            issues.extend(self._check_hexagonal_violations(code_file))
        
        # Check dependency direction
        if "architecture" in context.review_focus:
            issues.extend(self._check_dependency_violations(code_file))
        
        return issues
    
    def _check_hexagonal_violations(self, code_file: CodeFile) -> List[Dict[str, Any]]:
        """Check for hexagonal architecture violations"""
        
        violations = []
        
        # Check if domain code imports infrastructure
        if code_file.component_type in ["usecase", "entity", "domain"]:
            # Look for infrastructure imports
            infra_patterns = [
                r'import.*database',
                r'import.*http',
                r'import.*grpc',
                r'import.*redis',
                r'import.*kafka'
            ]
            
            for i, line in enumerate(code_file.content.split('\n'), 1):
                for pattern in infra_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append({
                            "type": "hexagonal_violation",
                            "line_number": i,
                            "description": f"Domain code should not directly import infrastructure: {line.strip()}",
                            "severity": "high",
                            "suggestion": "Use dependency injection and interfaces instead"
                        })
        
        return violations
    
    def _check_dependency_violations(self, code_file: CodeFile) -> List[Dict[str, Any]]:
        """Check for dependency direction violations"""
        
        violations = []
        
        # This would be more sophisticated in a real implementation
        # For now, just check for obvious violations
        
        return violations
    
    def _analyze_patterns(
        self,
        code_file: CodeFile,
        context: ReviewContext
    ) -> List[Dict[str, Any]]:
        """Analyze design pattern usage"""
        
        pattern_issues = []
        
        # Check for common anti-patterns
        if code_file.language == "go":
            pattern_issues.extend(self._check_go_patterns(code_file))
        elif code_file.language == "python":
            pattern_issues.extend(self._check_python_patterns(code_file))
        
        return pattern_issues
    
    def _check_go_patterns(self, code_file: CodeFile) -> List[Dict[str, Any]]:
        """Check Go-specific patterns and anti-patterns"""
        
        issues = []
        lines = code_file.content.split('\n')
        
        # Check for proper error handling
        for i, line in enumerate(lines, 1):
            if 'err != nil' in line:
                # Check if error is properly handled
                next_lines = lines[i:i+3] if i < len(lines) - 3 else lines[i:]
                if not any('return' in next_line or 'log' in next_line.lower() 
                          for next_line in next_lines):
                    issues.append({
                        "type": "error_handling",
                        "line_number": i,
                        "description": "Error might not be properly handled",
                        "severity": "medium",
                        "suggestion": "Ensure errors are returned or logged appropriately"
                    })
        
        # Check for interface usage
        interface_count = code_file.content.count('interface{')
        if interface_count == 0 and code_file.component_type in ["port", "service"]:
            issues.append({
                "type": "interface_design",
                "line_number": None,
                "description": "Consider using interfaces for better testability and decoupling",
                "severity": "medium",
                "suggestion": "Define interfaces for external dependencies"
            })
        
        return issues
    
    def _check_python_patterns(self, code_file: CodeFile) -> List[Dict[str, Any]]:
        """Check Python-specific patterns and anti-patterns"""
        
        issues = []
        
        try:
            # Parse Python AST for more sophisticated analysis
            tree = ast.parse(code_file.content)
            
            # Check for proper exception handling
            for node in ast.walk(tree):
                if isinstance(node, ast.Try):
                    if not node.handlers:
                        issues.append({
                            "type": "exception_handling",
                            "line_number": node.lineno,
                            "description": "Try block without exception handlers",
                            "severity": "high",
                            "suggestion": "Add appropriate exception handlers"
                        })
        
        except SyntaxError:
            issues.append({
                "type": "syntax_error",
                "line_number": None,
                "description": "Python syntax error detected",
                "severity": "high",
                "suggestion": "Fix syntax errors before review"
            })
        
        return issues
    
    def _calculate_quality_metrics(self, code_file: CodeFile) -> Dict[str, Any]:
        """Calculate code quality metrics"""
        
        lines = code_file.content.split('\n')
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('//')])
        comment_lines = len([line for line in lines if line.strip().startswith('//')])
        
        # Basic metrics
        metrics = {
            "total_lines": total_lines,
            "code_lines": code_lines,
            "comment_lines": comment_lines,
            "comment_ratio": comment_lines / max(code_lines, 1),
            "avg_line_length": sum(len(line) for line in lines) / max(total_lines, 1)
        }
        
        # Language-specific metrics
        if code_file.language == "go":
            metrics.update(self._calculate_go_metrics(code_file))
        elif code_file.language == "python":
            metrics.update(self._calculate_python_metrics(code_file))
        
        return metrics
    
    def _calculate_go_metrics(self, code_file: CodeFile) -> Dict[str, Any]:
        """Calculate Go-specific metrics"""
        
        content = code_file.content
        
        return {
            "function_count": content.count('func '),
            "struct_count": content.count('type ') + content.count('struct{'),
            "interface_count": content.count('interface{'),
            "error_checks": content.count('err != nil'),
            "goroutine_usage": content.count('go '),
            "channel_usage": content.count('chan ') + content.count('<-')
        }
    
    def _calculate_python_metrics(self, code_file: CodeFile) -> Dict[str, Any]:
        """Calculate Python-specific metrics"""
        
        try:
            tree = ast.parse(code_file.content)
            
            function_count = len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)])
            class_count = len([node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)])
            import_count = len([node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))])
            
            return {
                "function_count": function_count,
                "class_count": class_count,
                "import_count": import_count,
                "complexity_estimate": function_count + class_count * 2
            }
        
        except SyntaxError:
            return {"parse_error": True}
    
    def _calculate_overall_score(
        self,
        suggestions: List[CodeReviewSuggestion],
        architectural_issues: List[Dict[str, Any]],
        pattern_violations: List[Dict[str, Any]],
        quality_metrics: Dict[str, Any]
    ) -> float:
        """Calculate overall code quality score (0-100)"""
        
        base_score = 80.0  # Start with good score
        
        # Deduct points for suggestions
        for suggestion in suggestions:
            impact_penalty = {
                "high": 10,
                "medium": 5,
                "low": 2
            }.get(suggestion.architectural_impact, 5)
            
            confidence_factor = suggestion.confidence
            base_score -= impact_penalty * confidence_factor
        
        # Deduct points for architectural issues
        for issue in architectural_issues:
            severity_penalty = {
                "high": 15,
                "medium": 8,
                "low": 3
            }.get(issue.get("severity", "medium"), 8)
            
            base_score -= severity_penalty
        
        # Deduct points for pattern violations
        for violation in pattern_violations:
            severity_penalty = {
                "high": 12,
                "medium": 6,
                "low": 2
            }.get(violation.get("severity", "medium"), 6)
            
            base_score -= severity_penalty
        
        # Adjust based on quality metrics
        comment_ratio = quality_metrics.get("comment_ratio", 0)
        if comment_ratio < 0.1:  # Less than 10% comments
            base_score -= 5
        elif comment_ratio > 0.3:  # Good commenting
            base_score += 5
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, base_score))
    
    def _generate_summary(
        self,
        code_file: CodeFile,
        overall_score: float,
        suggestions: List[CodeReviewSuggestion]
    ) -> str:
        """Generate review summary"""
        
        high_priority = len([s for s in suggestions if s.architectural_impact == "high"])
        medium_priority = len([s for s in suggestions if s.architectural_impact == "medium"])
        low_priority = len([s for s in suggestions if s.architectural_impact == "low"])
        
        if overall_score >= 80:
            quality_assessment = "excellent"
        elif overall_score >= 60:
            quality_assessment = "good"
        elif overall_score >= 40:
            quality_assessment = "fair"
        else:
            quality_assessment = "needs improvement"
        
        summary = f"Code quality assessment: {quality_assessment} (score: {overall_score:.1f}/100). "
        summary += f"Found {len(suggestions)} suggestions: {high_priority} high priority, "
        summary += f"{medium_priority} medium priority, {low_priority} low priority."
        
        if high_priority > 0:
            summary += " Focus on addressing high priority architectural issues first."
        elif medium_priority > 0:
            summary += " Consider addressing medium priority improvements."
        else:
            summary += " Code follows good practices with minor improvements suggested."
        
        return summary
    
    def _generate_recommendations(
        self,
        suggestions: List[CodeReviewSuggestion],
        architectural_issues: List[Dict[str, Any]],
        pattern_violations: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate overall recommendations"""
        
        recommendations = []
        
        # High priority architectural issues
        high_arch_issues = [issue for issue in architectural_issues if issue.get("severity") == "high"]
        if high_arch_issues:
            recommendations.append("Address architectural violations to improve system design")
        
        # Pattern-related recommendations
        if pattern_violations:
            recommendations.append("Review design patterns and consider refactoring anti-patterns")
        
        # Suggestion-based recommendations
        suggestion_types = [s.suggestion_type for s in suggestions]
        if "architecture" in suggestion_types:
            recommendations.append("Focus on architectural improvements for better maintainability")
        if "performance" in suggestion_types:
            recommendations.append("Consider performance optimizations")
        if "security" in suggestion_types:
            recommendations.append("Address security concerns")
        
        # Generic recommendations
        if len(suggestions) > 10:
            recommendations.append("Consider breaking down complex components into smaller, focused units")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _generate_overall_recommendations(
        self,
        reports: List[CodeReviewReport]
    ) -> List[str]:
        """Generate recommendations across multiple files"""
        
        recommendations = []
        
        # Analyze patterns across files
        all_suggestions = [s for report in reports for s in report.suggestions]
        high_impact_count = len([s for s in all_suggestions if s.architectural_impact == "high"])
        
        if high_impact_count > 5:
            recommendations.append("Multiple high-impact architectural issues detected - consider architectural review")
        
        # Check for common issues
        common_types = {}
        for suggestion in all_suggestions:
            common_types[suggestion.suggestion_type] = common_types.get(suggestion.suggestion_type, 0) + 1
        
        most_common = max(common_types.items(), key=lambda x: x[1]) if common_types else None
        if most_common and most_common[1] > 3:
            recommendations.append(f"Common issue type '{most_common[0]}' appears across multiple files")
        
        # Score-based recommendations
        avg_score = sum(report.overall_score for report in reports) / len(reports)
        if avg_score < 60:
            recommendations.append("Overall code quality needs improvement - consider refactoring")
        elif avg_score > 85:
            recommendations.append("Excellent code quality - maintain current standards")
        
        return recommendations
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        
        extension = Path(file_path).suffix.lower()
        
        language_map = {
            '.go': 'go',
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php'
        }
        
        return language_map.get(extension, 'unknown')
    
    def _extract_module_name(self, file_path: str) -> Optional[str]:
        """Extract module name from file path"""
        
        path_parts = Path(file_path).parts
        
        # Look for common module indicators
        if 'internal' in path_parts:
            internal_index = path_parts.index('internal')
            if internal_index + 1 < len(path_parts):
                return path_parts[internal_index + 1]
        
        if 'src' in path_parts:
            src_index = path_parts.index('src')
            if src_index + 1 < len(path_parts):
                return path_parts[src_index + 1]
        
        # Fallback to parent directory
        return Path(file_path).parent.name if Path(file_path).parent.name != '.' else None
    
    def _detect_component_type(self, file_path: str, content: str) -> Optional[str]:
        """Detect component type from file path and content"""
        
        file_name = Path(file_path).name.lower()
        content_lower = content.lower()
        
        # Check file name patterns
        if 'usecase' in file_name or 'use_case' in file_name:
            return 'usecase'
        elif 'adapter' in file_name:
            return 'adapter'
        elif 'port' in file_name or 'interface' in file_name:
            return 'port'
        elif 'entity' in file_name or 'model' in file_name:
            return 'entity'
        elif 'service' in file_name:
            return 'service'
        elif 'repository' in file_name:
            return 'repository'
        
        # Check content patterns
        if 'interface' in content_lower and 'port' in content_lower:
            return 'port'
        elif 'struct' in content_lower and ('usecase' in content_lower or 'use_case' in content_lower):
            return 'usecase'
        
        return None
    
    def _create_fallback_suggestion(
        self,
        code_file: CodeFile,
        error_message: str
    ) -> CodeReviewSuggestion:
        """Create fallback suggestion when analysis fails"""
        
        return CodeReviewSuggestion(
            file_path=code_file.file_path,
            line_number=None,
            suggestion_type="error",
            title="Analysis failed",
            description=f"Automated analysis failed: {error_message}",
            code_snippet=None,
            suggested_fix="Manual review recommended",
            confidence=0.1,
            architectural_impact="low"
        )
    
    def _create_error_report(self, file_path: str, error_message: str) -> CodeReviewReport:
        """Create error report when review fails"""
        
        return CodeReviewReport(
            file_path=file_path,
            overall_score=0.0,
            suggestions=[],
            architectural_issues=[],
            pattern_violations=[],
            quality_metrics={},
            summary=f"Review failed: {error_message}",
            recommendations=["Manual review required due to analysis failure"]
        )


def create_ai_code_review_service(
    llm: LLMPort,
    knowledge_graph: Optional[KnowledgeGraphPort] = None,
    tenant_id: str = "default"
) -> AICodeReviewService:
    """Factory function to create an AICodeReviewService"""
    return AICodeReviewService(
        llm=llm,
        knowledge_graph=knowledge_graph,
        tenant_id=tenant_id
    )