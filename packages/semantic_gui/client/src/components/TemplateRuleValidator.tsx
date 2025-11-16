import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle, Info, X } from 'lucide-react';
import type { Node, Edge } from 'reactflow';

interface ValidationResult {
  id: string;
  type: 'error' | 'warning' | 'info';
  message: string;
  nodeId?: string;
  edgeId?: string;
  ruleId: string;
}

interface TemplateRuleValidatorProps {
  nodes: Node[];
  edges: Edge[];
  template: any;
  onValidationComplete?: (results: ValidationResult[]) => void;
}

export function TemplateRuleValidator({
  nodes,
  edges,
  template,
  onValidationComplete,
}: TemplateRuleValidatorProps) {
  const [validationResults, setValidationResults] = useState<
    ValidationResult[]
  >([]);
  const [isValidating, setIsValidating] = useState(false);

  useEffect(() => {
    validateArchitecture();
  }, [nodes, edges, template]);

  const validateArchitecture = async () => {
    if (!template || !nodes.length) return;

    setIsValidating(true);
    const results: ValidationResult[] = [];

    try {
      // Validate against template rules
      if (template.validationRules) {
        template.validationRules.forEach((rule: any) => {
          const ruleResults = validateRule(rule, nodes, edges);
          results.push(...ruleResults);
        });
      }

      // Check for architectural patterns
      const patternResults = validateArchitecturalPatterns(nodes, edges);
      results.push(...patternResults);

      setValidationResults(results);
      onValidationComplete?.(results);
    } catch (error) {
      console.error('Validation error:', error);
    } finally {
      setIsValidating(false);
    }
  };

  const validateRule = (
    rule: any,
    nodes: Node[],
    edges: Edge[]
  ): ValidationResult[] => {
    const results: ValidationResult[] = [];

    switch (rule.type) {
      case 'required':
        // Check for required connections
        if (rule.sourceType && rule.targetType) {
          const sourceNodes = nodes.filter(
            (n) => n.data.type === rule.sourceType
          );
          const hasRequiredConnections = sourceNodes.every((sourceNode) => {
            return edges.some(
              (edge) =>
                edge.source === sourceNode.id &&
                nodes.find((n) => n.id === edge.target)?.data.type ===
                  rule.targetType
            );
          });

          if (!hasRequiredConnections) {
            results.push({
              id: `${rule.id || Date.now()}_required`,
              type: 'error',
              message: `Required: ${rule.sourceType} must connect to ${rule.targetType}`,
              ruleId: rule.id || 'unknown',
            });
          }
        }
        break;

      case 'prohibited':
        // Check for prohibited connections
        if (rule.sourceType && rule.targetType) {
          const prohibitedConnections = edges.filter((edge) => {
            const sourceNode = nodes.find((n) => n.id === edge.source);
            const targetNode = nodes.find((n) => n.id === edge.target);
            return (
              sourceNode?.data.type === rule.sourceType &&
              targetNode?.data.type === rule.targetType
            );
          });

          prohibitedConnections.forEach((edge) => {
            results.push({
              id: `${edge.id}_prohibited`,
              type: 'error',
              message: `Prohibited: ${rule.sourceType} cannot connect to ${rule.targetType}`,
              edgeId: edge.id,
              ruleId: rule.id || 'unknown',
            });
          });
        }
        break;

      case 'naming':
        // Check naming conventions
        nodes.forEach((node) => {
          if (rule.nodeType && node.data.type === rule.nodeType) {
            const pattern = new RegExp(rule.pattern);
            if (!pattern.test(node.data.name)) {
              results.push({
                id: `${node.id}_naming`,
                type: 'warning',
                message: `Naming: ${node.data.type} should match pattern ${rule.pattern}`,
                nodeId: node.id,
                ruleId: rule.id || 'unknown',
              });
            }
          }
        });
        break;
    }

    return results;
  };

  const validateArchitecturalPatterns = (
    nodes: Node[],
    edges: Edge[]
  ): ValidationResult[] => {
    const results: ValidationResult[] = [];

    // Hexagonal Architecture validation
    if (template.name?.includes('hexagonal')) {
      // Controllers should not directly connect to repositories
      const invalidConnections = edges.filter((edge) => {
        const sourceNode = nodes.find((n) => n.id === edge.source);
        const targetNode = nodes.find((n) => n.id === edge.target);
        return (
          sourceNode?.data.type === 'controller' &&
          targetNode?.data.type === 'repository'
        );
      });

      invalidConnections.forEach((edge) => {
        results.push({
          id: `${edge.id}_hexagonal`,
          type: 'error',
          message:
            'Hexagonal Architecture: Controllers should not directly access repositories',
          edgeId: edge.id,
          ruleId: 'hexagonal_pattern',
        });
      });

      // Check for missing service layer
      const controllers = nodes.filter((n) => n.data.type === 'controller');
      const services = nodes.filter((n) => n.data.type === 'service');

      if (controllers.length > 0 && services.length === 0) {
        results.push({
          id: 'missing_service_layer',
          type: 'warning',
          message:
            'Consider adding service layer for better separation of concerns',
          ruleId: 'hexagonal_pattern',
        });
      }
    }

    return results;
  };

  const getIconForType = (type: ValidationResult['type']) => {
    switch (type) {
      case 'error':
        return <X className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
  };

  const errorCount = validationResults.filter((r) => r.type === 'error').length;
  const warningCount = validationResults.filter(
    (r) => r.type === 'warning'
  ).length;

  return (
    <Card className="border-2 border-primary bg-card">
      <CardHeader>
        <CardTitle className="text-primary terminal-font font-black flex items-center justify-between">
          RULE_VALIDATION
          <div className="flex space-x-2">
            {errorCount > 0 && (
              <Badge variant="destructive" className="terminal-font">
                {errorCount} ERRORS
              </Badge>
            )}
            {warningCount > 0 && (
              <Badge variant="secondary" className="terminal-font">
                {warningCount} WARNINGS
              </Badge>
            )}
            {validationResults.length === 0 && (
              <Badge variant="default" className="terminal-font bg-green-600">
                VALID
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isValidating && (
          <div className="text-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2"></div>
            <span className="text-primary terminal-font text-sm">
              VALIDATING...
            </span>
          </div>
        )}

        {!isValidating && validationResults.length === 0 && (
          <div className="text-center py-4">
            <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
            <span className="text-green-400 terminal-font">
              ALL_RULES_PASSED
            </span>
          </div>
        )}

        {!isValidating && validationResults.length > 0 && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {validationResults.map((result) => (
              <div
                key={result.id}
                className={`flex items-start space-x-2 p-2 rounded border ${
                  result.type === 'error'
                    ? 'border-red-500 bg-red-900/20'
                    : result.type === 'warning'
                      ? 'border-yellow-500 bg-yellow-900/20'
                      : 'border-blue-500 bg-blue-900/20'
                }`}
              >
                {getIconForType(result.type)}
                <div className="flex-1">
                  <div className="text-sm terminal-font">{result.message}</div>
                  {(result.nodeId || result.edgeId) && (
                    <div className="text-xs text-primary/60 terminal-font mt-1">
                      {result.nodeId && `Node: ${result.nodeId}`}
                      {result.edgeId && `Edge: ${result.edgeId}`}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-between items-center mt-4 pt-2 border-t border-primary/30">
          <span className="text-xs text-primary/60 terminal-font">
            Template: {template?.name || 'Unknown'}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={validateArchitecture}
            disabled={isValidating}
            className="terminal-font text-xs"
          >
            REVALIDATE
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
